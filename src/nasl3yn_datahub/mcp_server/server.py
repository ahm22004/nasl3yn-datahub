"""
MCP Server Integration — Exposes cinematic operations to agents via MCP.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel

from nasl3yn_datahub.api.client import DataHubClient, DataHubConfig, VideoAsset, PipelineRun

logger = logging.getLogger(__name__)


@dataclass
class CinematicMCPContext:
    """Context shared across MCP tools."""
    client: DataHubClient


class VideoAssetInput(BaseModel):
    """Input for creating a video asset."""
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


class LineageQueryInput(BaseModel):
    """Input for lineage queries."""
    urn: str
    direction: str = "BOTH"  # UPSTREAM, DOWNSTREAM, BOTH
    degree: int = 2


class PipelineInput(BaseModel):
    """Input for pipeline registration."""
    name: str
    description: str = ""
    pipeline_type: str  # "airflow", "prefect", "dagster", "custom"
    dag_yaml: str
    input_assets: List[str] = []
    output_assets: List[str] = []


class SearchInput(BaseModel):
    """Input for entity search."""
    query: str
    types: List[str] = ["DATASET"]
    limit: int = 20


def create_cinematic_mcp_server(client: DataHubClient) -> Server:
    """Create and configure the MCP server with cinematic tools."""
    server = Server("nasl3yn-cinematic")

    context = CinematicMCPContext(client=client)

    # ===== Tool: Create Video Asset =====
    @server.tool()
    async def create_video_asset(input: VideoAssetInput) -> str:
        """
        Register a new cinematic video asset in DataHub.
        
        Args:
            input: Video asset metadata including prompt, model, resolution, etc.
        
        Returns:
            URN of the created asset.
        """
        # Generate URN
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
        
        await context.client.create_entity(asset.to_entity())
        
        # Add lineage edges if output_assets specified (handled separately)
        logger.info(f"Created video asset: {urn}")
        return urn

    # ===== Tool: Get Video Asset =====
    @server.tool()
    async def get_video_asset(urn: str) -> str:
        """
        Retrieve a video asset by URN.
        
        Args:
            urn: The asset URN.
        
        Returns:
            JSON representation of the video asset.
        """
        entity = await context.client.get_entity(urn)
        if not entity:
            return f"Asset not found: {urn}"
        
        asset = VideoAsset.from_entity(entity)
        return asset.model_dump_json(indent=2)

    # ===== Tool: Trace Lineage =====
    @server.tool()
    async def trace_lineage(input: LineageQueryInput) -> str:
        """
        Trace upstream/downstream lineage for a cinematic asset.
        
        Args:
            input: URN and lineage direction parameters.
        
        Returns:
            Lineage graph as JSON.
        """
        result = await context.client.get_lineage(
            urn=input.urn,
            direction=input.direction,
            degree=input.degree,
        )
        return json.dumps(result, indent=2)

    # ===== Tool: Add Lineage Edge =====
    @server.tool()
    async def add_lineage_edge(upstream_urn: str, downstream_urn: str) -> str:
        """
        Create a lineage relationship between two assets.
        
        Args:
            upstream_urn: Source asset URN (e.g., prompt asset).
            downstream_urn: Target asset URN (e.g., rendered video).
        
        Returns:
            Success confirmation.
        """
        success = await context.client.add_lineage_edge(upstream_urn, downstream_urn)
        return f"Lineage edge created: {upstream_urn} -> {downstream_urn}" if success else "Failed to create lineage edge"

    # ===== Tool: Register Pipeline =====
    @server.tool()
    async def register_pipeline(input: PipelineInput) -> str:
        """
        Register a video generation pipeline run in DataHub.
        
        Args:
            input: Pipeline metadata including DAG YAML and asset references.
        
        Returns:
            URN of the pipeline run.
        """
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
        
        await context.client.create_entity(pipeline.to_entity())
        logger.info(f"Registered pipeline: {urn}")
        return urn

    # ===== Tool: Search Cinematic Assets =====
    @server.tool()
    async def search_cinematic_assets(input: SearchInput) -> str:
        """
        Search for video assets and pipelines in DataHub.
        
        Args:
            input: Search query and filters.
        
        Returns:
            List of matching assets as JSON.
        """
        entities = await context.client.search_entities(
            query=input.query,
            types=input.types,
            limit=input.limit,
        )
        
        results = []
        for e in entities:
            if e.type == "DATASET":
                try:
                    asset = VideoAsset.from_entity(e)
                    results.append(asset.model_dump())
                except Exception:
                    results.append({"urn": e.urn, "type": e.type, "name": e.properties.get("name", "")})
            else:
                results.append({"urn": e.urn, "type": e.type, "name": e.properties.get("name", "")})
        
        return json.dumps(results, indent=2)

    # ===== Tool: Update Pipeline Status =====
    @server.tool()
    async def update_pipeline_status(urn: str, status: str, error: str = "") -> str:
        """
        Update the status of a pipeline run.
        
        Args:
            urn: Pipeline URN.
            status: One of pending, running, completed, failed.
            error: Error message if failed.
        
        Returns:
            Success confirmation.
        """
        entity = await context.client.get_entity(urn)
        if not entity:
            return f"Pipeline not found: {urn}"
        
        # Update the status property
        entity.properties["customProperties"]["status"] = status
        if error:
            entity.properties["customProperties"]["error"] = error
        
        await context.client.create_entity(entity)
        return f"Pipeline {urn} status updated to: {status}"

    # ===== Tool: Get ML Lineage =====
    @server.tool()
    async def get_ml_lineage(model_urn: str) -> str:
        """
        Get end-to-end ML lineage for a video generation model.
        
        Args:
            model_urn: URN of the ML model.
        
        Returns:
            ML lineage graph (training data, features, deployments).
        """
        result = await context.client.get_ml_lineage(model_urn)
        return json.dumps(result, indent=2)

    return server


async def run_mcp_server(config: DataHubConfig, transport: str = "stdio"):
    """Run the MCP server with the given configuration."""
    async with DataHubClient(config) as client:
        server = create_cinematic_mcp_server(client)
        
        if transport == "stdio":
            from mcp.server.stdio import stdio_server
            async with stdio_server() as (read_stream, write_stream):
                await server.run(read_stream, write_stream, server.create_initialization_options())
        elif transport == "sse":
            from mcp.server.sse import sse_server
            async with sse_server("0.0.0.0", 8001) as (read_stream, write_stream):
                await server.run(read_stream, write_stream, server.create_initialization_options())
        else:
            raise ValueError(f"Unknown transport: {transport}")