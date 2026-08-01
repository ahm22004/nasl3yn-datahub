"""
DataHub Skills — Cinematic operations exposed as DataHub Skills.
Skills are reusable units that agents can invoke via the MCP Server.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field

from nasl3yn_datahub.api.client import DataHubClient, VideoAsset, PipelineRun, DataHubEntity

logger = logging.getLogger(__name__)


# ===== Base Skill Classes =====

class SkillInput(BaseModel):
    """Base input for all skills."""
    pass


class SkillOutput(BaseModel):
    """Base output for all skills."""
    success: bool
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)


class DataHubSkill(ABC):
    """Base class for DataHub Skills."""
    
    name: str = ""
    description: str = ""
    input_model: Type[SkillInput] = SkillInput
    output_model: Type[SkillOutput] = SkillOutput
    
    def __init__(self, client: DataHubClient):
        self.client = client
    
    @abstractmethod
    async def execute(self, input: SkillInput) -> SkillOutput:
        """Execute the skill with the given input."""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the skill's JSON schema for MCP registration."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
            "output_schema": self.output_model.model_json_schema(),
        }


# ===== Video Asset Skill =====

class VideoAssetCreateInput(SkillInput):
    name: str
    description: str = ""
    prompt: str
    model: str
    resolution: str
    duration_seconds: float
    codec: str
    seed: Optional[int] = None
    generation_time_ms: Optional[int] = None
    cost_usd: Optional[float] = None
    tags: List[str] = []


class VideoAssetOutput(SkillOutput):
    urn: Optional[str] = None
    asset: Optional[Dict[str, Any]] = None


class VideoAssetSkill(DataHubSkill):
    """Skill for creating and managing cinematic video assets."""
    
    name = "create_video_asset"
    description = "Register a new cinematic video asset in DataHub with full metadata"
    input_model = VideoAssetCreateInput
    output_model = VideoAssetOutput
    
    async def execute(self, input: VideoAssetCreateInput) -> VideoAssetOutput:
        safe_name = input.name.lower().replace(" ", "_").replace("-", "_")
        urn = f"urn:li:dataset:(urn:li:dataPlatform:nasl3yn,{safe_name},PROD)"
        
        asset = VideoAsset(
            urn=urn,
            name=input.name,
            description=input.description,
            prompt=input.prompt,
            model=input.model,
            resolution=input.resolution,
            duration_seconds=input.duration_seconds,
            codec=input.codec,
            seed=input.seed,
            generation_time_ms=input.generation_time_ms,
            cost_usd=input.cost_usd,
            tags=input.tags,
        )
        
        await self.client.create_entity(asset.to_entity())
        
        return VideoAssetOutput(
            success=True,
            message=f"Created video asset: {urn}",
            urn=urn,
            asset=asset.model_dump(),
        )


class VideoAssetGetInput(SkillInput):
    urn: str


class VideoAssetGetOutput(SkillOutput):
    asset: Optional[Dict[str, Any]] = None


class VideoAssetGetSkill(DataHubSkill):
    """Skill for retrieving a video asset by URN."""
    
    name = "get_video_asset"
    description = "Retrieve a cinematic video asset by its URN"
    input_model = VideoAssetGetInput
    output_model = VideoAssetGetOutput
    
    async def execute(self, input: VideoAssetGetInput) -> VideoAssetGetOutput:
        entity = await self.client.get_entity(input.urn)
        if not entity:
            return VideoAssetGetOutput(
                success=False,
                message=f"Asset not found: {input.urn}",
            )
        
        asset = VideoAsset.from_entity(entity)
        return VideoAssetGetOutput(
            success=True,
            message=f"Retrieved asset: {input.urn}",
            asset=asset.model_dump(),
        )


# ===== Lineage Skill =====

class LineageTraceInput(SkillInput):
    urn: str
    direction: str = "BOTH"
    degree: int = 2


class LineageTraceOutput(SkillOutput):
    lineage: Dict[str, Any] = Field(default_factory=dict)


class LineageSkill(DataHubSkill):
    """Skill for tracing lineage of cinematic assets."""
    
    name = "trace_lineage"
    description = "Trace upstream/downstream lineage for a cinematic asset"
    input_model = LineageTraceInput
    output_model = LineageTraceOutput
    
    async def execute(self, input: LineageTraceInput) -> LineageTraceOutput:
        result = await self.client.get_lineage(
            urn=input.urn,
            direction=input.direction,
            degree=input.degree,
        )
        return LineageTraceOutput(
            success=True,
            message=f"Traced lineage for {input.urn}",
            lineage=result,
        )


class LineageAddInput(SkillInput):
    upstream_urn: str
    downstream_urn: str


class LineageAddOutput(SkillOutput):
    pass


class LineageAddSkill(DataHubSkill):
    """Skill for adding lineage edges between assets."""
    
    name = "add_lineage_edge"
    description = "Create a lineage relationship between two cinematic assets"
    input_model = LineageAddInput
    output_model = LineageAddOutput
    
    async def execute(self, input: LineageAddInput) -> LineageAddOutput:
        success = await self.client.add_lineage_edge(input.upstream_urn, input.downstream_urn)
        if success:
            return LineageAddOutput(
                success=True,
                message=f"Lineage edge created: {input.upstream_urn} -> {input.downstream_urn}",
            )
        return LineageAddOutput(
            success=False,
            message="Failed to create lineage edge",
        )


# ===== Pipeline Skill =====

class PipelineRegisterInput(SkillInput):
    name: str
    description: str = ""
    pipeline_type: str
    dag_yaml: str
    input_assets: List[str] = []
    output_assets: List[str] = []


class PipelineRegisterOutput(SkillOutput):
    urn: Optional[str] = None


class PipelineSkill(DataHubSkill):
    """Skill for registering video generation pipelines."""
    
    name = "register_pipeline"
    description = "Register a video generation pipeline run in DataHub"
    input_model = PipelineRegisterInput
    output_model = PipelineRegisterOutput
    
    async def execute(self, input: PipelineRegisterInput) -> PipelineRegisterOutput:
        safe_name = input.name.lower().replace(" ", "_").replace("-", "_")
        urn = f"urn:li:dataProcess:(urn:li:dataPlatform:nasl3yn,{safe_name},PROD)"
        
        pipeline = PipelineRun(
            urn=urn,
            name=input.name,
            description=input.description,
            pipeline_type=input.pipeline_type,
            dag_yaml=input.dag_yaml,
            status="pending",
            input_assets=input.input_assets,
            output_assets=input.output_assets,
        )
        
        await self.client.create_entity(pipeline.to_entity())
        
        # Add lineage edges from input assets to pipeline
        for asset_urn in input.input_assets:
            await self.client.add_lineage_edge(asset_urn, urn)
        
        # Add lineage edges from pipeline to output assets
        for asset_urn in input.output_assets:
            await self.client.add_lineage_edge(urn, asset_urn)
        
        return PipelineRegisterOutput(
            success=True,
            message=f"Registered pipeline: {urn}",
            urn=urn,
        )


class PipelineStatusInput(SkillInput):
    urn: str
    status: str
    error: str = ""


class PipelineStatusOutput(SkillOutput):
    pass


class PipelineStatusSkill(DataHubSkill):
    """Skill for updating pipeline status."""
    
    name = "update_pipeline_status"
    description = "Update the status of a pipeline run (pending, running, completed, failed)"
    input_model = PipelineStatusInput
    output_model = PipelineStatusOutput
    
    async def execute(self, input: PipelineStatusInput) -> PipelineStatusOutput:
        entity = await self.client.get_entity(input.urn)
        if not entity:
            return PipelineStatusOutput(
                success=False,
                message=f"Pipeline not found: {input.urn}",
            )
        
        entity.properties["customProperties"]["status"] = input.status
        if input.error:
            entity.properties["customProperties"]["error"] = input.error
        
        await self.client.create_entity(entity)
        
        return PipelineStatusOutput(
            success=True,
            message=f"Pipeline {input.urn} status updated to: {input.status}",
        )


# ===== Metadata Skill =====

class MetadataValidateInput(SkillInput):
    urn: str
    schema_version: str = "1.0"


class MetadataValidateOutput(SkillOutput):
    valid: bool
    missing_fields: List[str] = Field(default_factory=list)
    extra_fields: List[str] = Field(default_factory=list)


REQUIRED_CINEMATIC_FIELDS = [
    "prompt", "model", "resolution", "duration_seconds", "codec"
]


class MetadataSkill(DataHubSkill):
    """Skill for validating cinematic metadata schemas."""
    
    name = "validate_metadata"
    description = "Validate that a video asset has all required cinematic metadata fields"
    input_model = MetadataValidateInput
    output_model = MetadataValidateOutput
    
    async def execute(self, input: MetadataValidateInput) -> MetadataValidateOutput:
        entity = await self.client.get_entity(input.urn)
        if not entity:
            return MetadataValidateOutput(
                success=False,
                message=f"Asset not found: {input.urn}",
                valid=False,
                missing_fields=REQUIRED_CINEMATIC_FIELDS,
            )
        
        cp = entity.properties.get("customProperties", {})
        missing = [f for f in REQUIRED_CINEMATIC_FIELDS if f not in cp]
        extra = [f for f in cp.keys() if f not in REQUIRED_CINEMATIC_FIELDS]
        
        return MetadataValidateOutput(
            success=True,
            message=f"Metadata validation for {input.urn}",
            valid=len(missing) == 0,
            missing_fields=missing,
            extra_fields=extra,
        )


# ===== Skill Registry =====

SKILL_REGISTRY: Dict[str, Type[DataHubSkill]] = {
    "create_video_asset": VideoAssetSkill,
    "get_video_asset": VideoAssetGetSkill,
    "trace_lineage": LineageSkill,
    "add_lineage_edge": LineageAddSkill,
    "register_pipeline": PipelineSkill,
    "update_pipeline_status": PipelineStatusSkill,
    "validate_metadata": MetadataSkill,
}


def get_skill(name: str, client: DataHubClient) -> DataHubSkill:
    """Get a skill instance by name."""
    skill_class = SKILL_REGISTRY.get(name)
    if not skill_class:
        raise ValueError(f"Unknown skill: {name}")
    return skill_class(client)


def list_skills() -> List[Dict[str, Any]]:
    """List all available skills with their schemas."""
    return [
        {"name": name, "description": cls.description}
        for name, cls in SKILL_REGISTRY.items()
    ]


async def execute_skill(name: str, client: DataHubClient, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a skill by name with the given input."""
    skill = get_skill(name, client)
    input_model = skill.input_model(**input_data)
    output = await skill.execute(input_model)
    return output.model_dump()