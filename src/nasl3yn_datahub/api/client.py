"""
DataHub API Client — GraphQL/REST wrapper for Nasl3yn cinematic operations.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DataHubConfig(BaseSettings):
    gms_url: str = Field(..., description="DataHub GMS endpoint URL")
    token: str = Field(..., description="DataHub personal access token")
    timeout_seconds: int = 30

    class Config:
        env_prefix = "DATAHUB_"
        case_sensitive = False


@dataclass
class DataHubEntity:
    urn: str
    type: str
    properties: Dict[str, Any]
    aspects: Dict[str, Any] = None

    def __post_init__(self):
        if self.aspects is None:
            self.aspects = {}


class DataHubClient:
    """GraphQL/REST client for DataHub operations."""

    def __init__(self, config: DataHubConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._graphql_url = f"{config.gms_url.rstrip('/')}/api/graphql"

    async def __aenter__(self) -> DataHubClient:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout_seconds),
            headers={
                "Authorization": f"Bearer {self.config.token}",
                "Content-Type": "application/json",
            },
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
    )
    async def _graphql(self, query: str, variables: Dict = None) -> Dict:
        """Execute GraphQL query with retry."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        resp = await self._client.post(
            self._graphql_url,
            json={"query": query, "variables": variables or {}},
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            raise ValueError(f"GraphQL errors: {data['errors']}")
        return data.get("data", {})

    # ===== Entity Operations =====

    async def get_entity(self, urn: str) -> Optional[DataHubEntity]:
        """Fetch entity by URN."""
        query = """
        query getEntity($urn: String!) {
            entity(urn: $urn) {
                urn
                type
                ... on Dataset {
                    name
                    description
                    properties {
                        customProperties {
                            key
                            value
                        }
                    }
                }
            }
        }
        """
        data = await self._graphql(query, {"urn": urn})
        entity_data = data.get("entity")
        if not entity_data:
            return None
        return self._parse_entity(entity_data)

    async def create_entity(self, entity: DataHubEntity) -> DataHubEntity:
        """Create or update entity (upsert via REST)."""
        # Use REST API for entity creation
        url = f"{self.config.gms_url.rstrip('/')}/openapi/entity/upsert"
        payload = {
            "entity": {
                "urn": entity.urn,
                "type": entity.type,
                "properties": entity.properties,
                "aspects": entity.aspects,
            }
        }
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        return entity

    async def search_entities(
        self,
        query: str,
        types: List[str] = None,
        limit: int = 20,
    ) -> List[DataHubEntity]:
        """Search entities across DataHub."""
        gql = """
        query search($input: SearchInput!) {
            search(input: $input) {
                searchResults {
                    entity {
                        urn
                        type
                        ... on Dataset {
                            name
                            description
                            properties {
                                customProperties {
                                    key
                                    value
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        variables = {
            "input": {
                "query": query,
                "types": types or ["DATASET", "DASHBOARD", "CHART", "ML_MODEL", "ML_FEATURE"],
                "start": 0,
                "count": limit,
            }
        }
        data = await self._graphql(gql, variables)
        results = data.get("search", {}).get("searchResults", [])
        return [self._parse_entity(r["entity"]) for r in results if r.get("entity")]

    # ===== Lineage Operations =====

    async def get_lineage(
        self,
        urn: str,
        direction: str = "BOTH",
        degree: int = 2,
    ) -> Dict[str, Any]:
        """Get upstream/downstream lineage for an entity."""
        query = """
        query getLineage($urn: String!, $direction: LineageDirection!, $degree: Int!) {
            lineage(urn: $urn, direction: $direction, degree: $degree) {
                edges {
                    source { urn type }
                    destination { urn type }
                }
            }
        }
        """
        data = await self._graphql(query, {"urn": urn, "direction": direction, "degree": degree})
        return data.get("lineage", {})

    async def add_lineage_edge(self, upstream_urn: str, downstream_urn: str) -> bool:
        """Add a lineage edge between two entities."""
        mutation = """
        mutation addLineage($input: AddLineageEdgeInput!) {
            addLineageEdge(input: $input)
        }
        """
        data = await self._graphql(mutation, {
            "input": {"upstreamUrn": upstream_urn, "downstreamUrn": downstream_urn}
        })
        return data.get("addLineageEdge", False)

    # ===== ML Lineage =====

    async def get_ml_lineage(self, model_urn: str) -> Dict[str, Any]:
        """Get end-to-end ML lineage for a model."""
        query = """
        query getMLLineage($urn: String!) {
            entity(urn: $urn) {
                ... on MLModel {
                    mlLineage {
                        trainingData { urn }
                        features { urn }
                        deployments { urn }
                    }
                }
            }
        }
        """
        data = await self._graphql(query, {"urn": model_urn})
        return data.get("entity", {}).get("mlLineage", {})

    # ===== Helper =====

    def _parse_entity(self, data: Dict) -> DataHubEntity:
        props = data.get("properties", {})
        custom = {}
        for cp in props.get("customProperties", []):
            custom[cp["key"]] = cp["value"]
        return DataHubEntity(
            urn=data["urn"],
            type=data["type"],
            properties={**props, "customProperties": custom},
        )


# ===== Cinematic-Specific Models =====

class VideoAsset(BaseModel):
    """Cinematic video asset metadata."""
    urn: str
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
    tags: List[str] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)

    def to_entity(self) -> DataHubEntity:
        custom = {
            "prompt": self.prompt,
            "model": self.model,
            "resolution": self.resolution,
            "duration_seconds": str(self.duration_seconds),
            "codec": self.codec,
        }
        if self.seed is not None:
            custom["seed"] = str(self.seed)
        if self.generation_time_ms is not None:
            custom["generation_time_ms"] = str(self.generation_time_ms)
        if self.cost_usd is not None:
            custom["cost_usd"] = str(self.cost_usd)
        if self.tags:
            custom["tags"] = ",".join(self.tags)
        for k, v in self.extra.items():
            custom[k] = str(v)

        return DataHubEntity(
            urn=self.urn,
            type="DATASET",
            properties={
                "name": self.name,
                "description": self.description,
                "customProperties": [{"key": k, "value": v} for k, v in custom.items()],
            },
        )

    @classmethod
    def from_entity(cls, entity: DataHubEntity) -> VideoAsset:
        cp = entity.properties.get("customProperties", {})
        return cls(
            urn=entity.urn,
            name=entity.properties.get("name", ""),
            description=entity.properties.get("description", ""),
            prompt=cp.get("prompt", ""),
            model=cp.get("model", ""),
            resolution=cp.get("resolution", ""),
            duration_seconds=float(cp.get("duration_seconds", 0)),
            codec=cp.get("codec", ""),
            seed=int(cp["seed"]) if cp.get("seed") else None,
            generation_time_ms=int(cp["generation_time_ms"]) if cp.get("generation_time_ms") else None,
            cost_usd=float(cp["cost_usd"]) if cp.get("cost_usd") else None,
            tags=cp.get("tags", "").split(",") if cp.get("tags") else [],
        )


class PipelineRun(BaseModel):
    """Video generation pipeline run record."""
    urn: str
    name: str
    description: str = ""
    pipeline_type: str  # "airflow", "prefect", "dagster", "custom"
    dag_yaml: str
    status: str  # "pending", "running", "completed", "failed"
    input_assets: List[str] = Field(default_factory=list)
    output_assets: List[str] = Field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None

    def to_entity(self) -> DataHubEntity:
        custom = {
            "pipeline_type": self.pipeline_type,
            "dag_yaml": self.dag_yaml,
            "status": self.status,
            "input_assets": ",".join(self.input_assets),
            "output_assets": ",".join(self.output_assets),
        }
        if self.started_at:
            custom["started_at"] = self.started_at
        if self.completed_at:
            custom["completed_at"] = self.completed_at
        if self.error:
            custom["error"] = self.error

        return DataHubEntity(
            urn=self.urn,
            type="DATA_PROCESS",
            properties={
                "name": self.name,
                "description": self.description,
                "customProperties": [{"key": k, "value": v} for k, v in custom.items()],
            },
        )