"""
Orchestrator Agent — Autonomous video pipeline orchestration using DataHub context.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

import typer
from rich.console import Console
from rich.table import Table

from nasl3yn_datahub.api.client import DataHubClient, DataHubConfig, VideoAsset, PipelineRun
from nasl3yn_datahub.skills.registry import (
    get_skill,
    list_skills,
    SKILL_REGISTRY,
    VideoAssetCreateInput,
    PipelineRegisterInput,
    PipelineStatusInput,
    LineageTraceInput,
    LineageAddInput,
)

logger = logging.getLogger(__name__)

console = Console()
main = typer.Typer()


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    """A single step in a video generation workflow."""
    name: str
    skill: str
    input: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class VideoWorkflow:
    """A complete video generation workflow."""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_assets: List[str] = field(default_factory=list)


class AgentConfig(BaseSettings):
    name: str = "nasl3yn-cinematic-orchestrator"
    max_concurrent_workflows: int = 3
    default_model: str = "veo-2"
    poll_interval_seconds: int = 10
    platform_name: str = "nasl3yn"

    class Config:
        env_prefix = "AGENT_"
        case_sensitive = False


class CinematicOrchestrator:
    """
    Autonomous agent that orchestrates video generation pipelines
    using DataHub as the context backbone.
    """
    
    def __init__(self, config: AgentConfig, datahub_config: DataHubConfig):
        self.config = config
        self.datahub_config = datahub_config
        self._client: Optional[DataHubClient] = None
        self._workflows: Dict[str, VideoWorkflow] = {}
        self._running = False
    
    async def __aenter__(self) -> CinematicOrchestrator:
        self._client = DataHubClient(self.datahub_config)
        await self._client.__aenter__()
        return self
    
    async def __aexit__(self, *args):
        if self._client:
            await self._client.__aexit__(*args)
    
    @property
    def client(self) -> DataHubClient:
        if not self._client:
            raise RuntimeError("Orchestrator not initialized. Use async context manager.")
        return self._client
    
    # ===== Workflow Management =====
    
    def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
    ) -> VideoWorkflow:
        """Create a new video generation workflow."""
        workflow_id = str(uuid.uuid4())[:8]
        workflow = VideoWorkflow(
            id=workflow_id,
            name=name,
            description=description,
            steps=[
                WorkflowStep(
                    name=s["name"],
                    skill=s["skill"],
                    input=s["input"],
                    depends_on=s.get("depends_on", []),
                )
                for s in steps
            ],
        )
        self._workflows[workflow_id] = workflow
        logger.info(f"Created workflow {workflow_id}: {name}")
        return workflow
    
    async def execute_workflow(self, workflow_id: str) -> VideoWorkflow:
        """Execute a workflow by ID."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        if workflow.status != WorkflowStatus.PENDING:
            raise ValueError(f"Workflow {workflow_id} already started (status: {workflow.status})")
        
        workflow.status = WorkflowStatus.EXECUTING
        workflow.started_at = datetime.utcnow()
        
        # Execute steps in dependency order
        completed = set()
        
        while len(completed) < len(workflow.steps):
            # Find runnable steps
            runnable = [
                step for step in workflow.steps
                if step.status == WorkflowStatus.PENDING
                and all(dep in completed for dep in step.depends_on)
            ]
            
            if not runnable:
                # Check for circular dependency or all remaining failed
                remaining = [s for s in workflow.steps if s.status == WorkflowStatus.PENDING]
                if not remaining:
                    break
                # No runnable steps but some remain = circular dependency or failed deps
                for step in remaining:
                    step.status = WorkflowStatus.FAILED
                    step.error = "Dependency resolution failed (circular or failed dependencies)"
                break
            
            # Execute runnable steps in parallel (up to max_concurrent)
            semaphore = asyncio.Semaphore(self.config.max_concurrent_workflows)
            
            async def run_step(step: WorkflowStep):
                async with semaphore:
                    step.status = WorkflowStatus.EXECUTING
                    logger.info(f"Executing step {step.name} (skill: {step.skill})")
                    try:
                        result = await execute_skill(step.skill, self.client, step.input)
                        step.result = result
                        if result.get("success"):
                            step.status = WorkflowStatus.COMPLETED
                            logger.info(f"Step {step.name} completed")
                        else:
                            step.status = WorkflowStatus.FAILED
                            step.error = result.get("message", "Unknown error")
                            logger.error(f"Step {step.name} failed: {step.error}")
                    except Exception as e:
                        step.status = WorkflowStatus.FAILED
                        step.error = str(e)
                        logger.exception(f"Step {step.name} exception: {e}")
            
            await asyncio.gather(*[run_step(s) for s in runnable])
            
            # Update completed set
            for step in runnable:
                if step.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
                    completed.add(step.name)
        
        # Determine final workflow status
        failed_steps = [s for s in workflow.steps if s.status == WorkflowStatus.FAILED]
        if failed_steps:
            workflow.status = WorkflowStatus.FAILED
        else:
            workflow.status = WorkflowStatus.COMPLETED
            # Collect output assets from results
            for step in workflow.steps:
                if step.result and step.result.get("urn"):
                    workflow.output_assets.append(step.result["urn"])
        
        workflow.completed_at = datetime.utcnow()
        logger.info(f"Workflow {workflow_id} finished: {workflow.status}")
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[VideoWorkflow]:
        """Get workflow by ID."""
        return self._workflows.get(workflow_id)
    
    def list_workflows(self) -> List[VideoWorkflow]:
        """List all workflows."""
        return list(self._workflows.values())
    
    # ===== Pre-built Workflow Templates =====
    
    def create_single_scene_workflow(
        self,
        scene_name: str,
        prompt: str,
        model: str = None,
        resolution: str = "3840x2160",
        duration_seconds: float = 8.0,
        codec: str = "hevc",
    ) -> VideoWorkflow:
        """Create a workflow for generating a single cinematic scene."""
        model = model or self.config.default_model
        asset_name = f"{scene_name}_render"
        safe_name = asset_name.lower().replace(" ", "_")
        asset_urn = f"urn:li:dataset:(urn:li:dataPlatform:{self.config.platform_name},{safe_name},PROD)"
        pipeline_urn = f"urn:li:dataProcess:(urn:li:dataPlatform:{self.config.platform_name},{safe_name}_pipeline,PROD)"
        
        steps = [
            {
                "name": "create_video_asset",
                "skill": "create_video_asset",
                "input": {
                    "name": asset_name,
                    "description": f"Rendered scene: {scene_name}",
                    "prompt": prompt,
                    "model": model,
                    "resolution": resolution,
                    "duration_seconds": duration_seconds,
                    "codec": codec,
                },
                "depends_on": [],
            },
            {
                "name": "register_pipeline",
                "skill": "register_pipeline",
                "input": {
                    "name": f"{scene_name} Pipeline",
                    "description": f"Generation pipeline for {scene_name}",
                    "pipeline_type": "custom",
                    "dag_yaml": f"# Pipeline for {scene_name}\nsteps:\n  - generate: {model}\n  - render: {resolution}\n  - encode: {codec}",
                    "input_assets": [],
                    "output_assets": [asset_urn],
                },
                "depends_on": ["create_video_asset"],
            },
            {
                "name": "validate_metadata",
                "skill": "validate_metadata",
                "input": {
                    "urn": asset_urn,
                    "schema_version": "1.0",
                },
                "depends_on": ["create_video_asset"],
            },
        ]
        
        return self.create_workflow(
            name=f"{scene_name} Generation",
            description=f"Generate single cinematic scene: {scene_name}",
            steps=steps,
        )
    
    def create_multi_scene_workflow(
        self,
        project_name: str,
        scenes: List[Dict[str, Any]],
        model: str = None,
    ) -> VideoWorkflow:
        """Create a workflow for generating multiple scenes with shared context."""
        model = model or self.config.default_model
        steps = []
        asset_urns = []
        
        for i, scene in enumerate(scenes):
            scene_name = scene.get("name", f"scene_{i+1}")
            asset_name = f"{project_name}_{scene_name}_render"
            safe_name = asset_name.lower().replace(" ", "_")
            asset_urn = f"urn:li:dataset:(urn:li:dataPlatform:{self.config.platform_name},{safe_name},PROD)"
            asset_urns.append(asset_urn)
            
            steps.append({
                "name": f"create_asset_{scene_name}",
                "skill": "create_video_asset",
                "input": {
                    "name": asset_name,
                    "description": f"Scene {i+1}: {scene_name}",
                    "prompt": scene.get("prompt", ""),
                    "model": scene.get("model", model),
                    "resolution": scene.get("resolution", "3840x2160"),
                    "duration_seconds": scene.get("duration_seconds", 8.0),
                    "codec": scene.get("codec", "hevc"),
                },
                "depends_on": [],
            })
        
        # Register pipeline that encompasses all scenes
        steps.append({
            "name": "register_pipeline",
            "skill": "register_pipeline",
            "input": {
                "name": f"{project_name} Multi-Scene Pipeline",
                "description": f"Generation pipeline for {len(scenes)} scenes",
                "pipeline_type": "custom",
                "dag_yaml": "# Multi-scene pipeline for {project_name}\nscenes:\n" + "\n".join(
                    f"  - {s.get('name', 'scene_{i+1}')}: {s.get('prompt', '')[:50]}"
                    for i, s in enumerate(scenes)
                ),
                "input_assets": [],
                "output_assets": asset_urns,
            },
            "depends_on": [f"create_asset_{s.get('name', f'scene_{i+1}')}" for i, s in enumerate(scenes)],
        })
        
        # Validate all assets
        for i, scene in enumerate(scenes):
            scene_name = scene.get("name", f"scene_{i+1}")
            asset_name = f"{project_name}_{scene_name}_render"
            safe_name = asset_name.lower().replace(" ", "_")
            asset_urn = f"urn:li:dataset:(urn:li:dataPlatform:{self.config.platform_name},{safe_name},PROD)"
            steps.append({
                "name": f"validate_{scene_name}",
                "skill": "validate_metadata",
                "input": {"urn": asset_urn, "schema_version": "1.0"},
                "depends_on": [f"create_asset_{scene_name}"],
            })
        
        return self.create_workflow(
            name=f"{project_name} Multi-Scene Generation",
            description=f"Generate {len(scenes)} cinematic scenes for {project_name}",
            steps=steps,
        )
    
    def create_lineage_workflow(
        self,
        prompt_urn: str,
        asset_urns: List[str],
    ) -> VideoWorkflow:
        """Create a workflow to establish lineage from prompt to rendered assets."""
        steps = []
        for i, asset_urn in enumerate(asset_urns):
            steps.append({
                "name": f"add_lineage_{i}",
                "skill": "add_lineage_edge",
                "input": {
                    "upstream_urn": prompt_urn,
                    "downstream_urn": asset_urn,
                },
                "depends_on": [],
            })
        
        return self.create_workflow(
            name="Establish Prompt-to-Asset Lineage",
            description="Link prompt entity to all generated video assets",
            steps=steps,
        )


# ===== CLI Entry Point =====

def _run_async(coro):
    """Helper to run async function from sync CLI."""
    import asyncio
    return asyncio.run(coro)


@main.callback()
def callback():
    """Nasl3yn DataHub Cinematic Orchestrator CLI."""
    pass


@main.command()
def single_scene(
    name: str = typer.Argument(..., help="Scene name"),
    prompt: str = typer.Argument(..., help="Generation prompt"),
    model: str = typer.Option("veo-2", help="Video generation model"),
    resolution: str = typer.Option("3840x2160", help="Output resolution"),
    duration: float = typer.Option(8.0, help="Duration in seconds"),
    codec: str = typer.Option("hevc", help="Video codec"),
):
    """Create and execute a single-scene generation workflow."""
    _run_async(_single_scene_async(name, prompt, model, resolution, duration, codec))


async def _single_scene_async(
    name: str,
    prompt: str,
    model: str,
    resolution: str,
    duration: float,
    codec: str,
):
    """Async implementation of single_scene command."""
    agent_config = AgentConfig()
    datahub_config = DataHubConfig()
    
    async with CinematicOrchestrator(agent_config, datahub_config) as orchestrator:
        workflow = orchestrator.create_single_scene_workflow(
            scene_name=name,
            prompt=prompt,
            model=model,
            resolution=resolution,
            duration_seconds=duration,
            codec=codec,
        )
        console.print(f"[green]Created workflow:[/green] {workflow.id} - {workflow.name}")
        
        result = await orchestrator.execute_workflow(workflow.id)
        
        table = Table(title=f"Workflow {result.id} Result")
        table.add_column("Step")
        table.add_column("Skill")
        table.add_column("Status")
        table.add_column("Output")
        
        for step in result.steps:
            table.add_row(
                step.name,
                step.skill,
                step.status.value,
                step.result.get("urn", "") if step.result else step.error or "",
            )
        
        console.print(table)


@main.command()
def list_skills_cmd():
    """List available DataHub skills."""
    skills = list_skills()
    table = Table(title="Available DataHub Skills")
    table.add_column("Name")
    table.add_column("Description")
    for s in skills:
        table.add_row(s["name"], s["description"])
    console.print(table)


if __name__ == "__main__":
    main()