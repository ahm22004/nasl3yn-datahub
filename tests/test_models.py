"""
Tests for Nasl3yn DataHub components.
"""

import pytest
from pydantic import ValidationError

from nasl3yn_datahub.api.client import VideoAsset, PipelineRun, DataHubEntity
from nasl3yn_datahub.skills.registry import (
    VideoAssetCreateInput,
    PipelineRegisterInput,
    VideoAssetSkill,
    PipelineSkill,
    get_skill,
    list_skills,
)


class TestVideoAsset:
    """Test VideoAsset model."""
    
    def test_valid_video_asset(self):
        asset = VideoAsset(
            urn="urn:li:dataset:(urn:li:dataPlatform:nasl3yn,test_render,PROD)",
            name="test_render",
            prompt="Test prompt",
            model="veo-2",
            resolution="3840x2160",
            duration_seconds=8.0,
            codec="hevc",
        )
        assert asset.name == "test_render"
        assert asset.model == "veo-2"
        assert asset.duration_seconds == 8.0
    
    def test_video_asset_to_entity(self):
        asset = VideoAsset(
            urn="urn:li:dataset:(urn:li:dataPlatform:nasl3yn,test_render,PROD)",
            name="test_render",
            prompt="Test prompt",
            model="veo-2",
            resolution="3840x2160",
            duration_seconds=8.0,
            codec="hevc",
            seed=12345,
            tags=["test", "cinematic"],
        )
        entity = asset.to_entity()
        assert entity.urn == asset.urn
        assert entity.type == "DATASET"
        cp = {p["key"]: p["value"] for p in entity.properties["customProperties"]}
        assert cp["prompt"] == "Test prompt"
        assert cp["seed"] == "12345"
        assert cp["tags"] == "test,cinematic"
    
    def test_video_asset_from_entity(self):
        entity = DataHubEntity(
            urn="urn:li:dataset:(urn:li:dataPlatform:nasl3yn,test_render,PROD)",
            type="DATASET",
            properties={
                "name": "test_render",
                "description": "Test",
                "customProperties": {
                    "prompt": "Test prompt",
                    "model": "veo-2",
                    "resolution": "3840x2160",
                    "duration_seconds": "8.0",
                    "codec": "hevc",
                    "seed": "12345",
                    "tags": "test,cinematic",
                },
            },
        )
        asset = VideoAsset.from_entity(entity)
        assert asset.name == "test_render"
        assert asset.seed == 12345
        assert asset.tags == ["test", "cinematic"]


class TestPipelineRun:
    """Test PipelineRun model."""
    
    def test_valid_pipeline(self):
        pipeline = PipelineRun(
            urn="urn:li:dataProcess:(urn:li:dataPlatform:nasl3yn,test_pipeline,PROD)",
            name="Test Pipeline",
            pipeline_type="airflow",
            dag_yaml="tasks:\n  - generate",
            status="pending",
            input_assets=[],
            output_assets=["urn:li:dataset:..."],
        )
        assert pipeline.pipeline_type == "airflow"
        assert pipeline.status == "pending"
    
    def test_pipeline_to_entity(self):
        pipeline = PipelineRun(
            urn="urn:li:dataProcess:(urn:li:dataPlatform:nasl3yn,test_pipeline,PROD)",
            name="Test Pipeline",
            pipeline_type="airflow",
            dag_yaml="test: yaml",
            status="running",
            input_assets=["urn:upstream"],
            output_assets=["urn:downstream"],
        )
        entity = pipeline.to_entity()
        assert entity.type == "DATA_PROCESS"
        cp = {p["key"]: p["value"] for p in entity.properties["customProperties"]}
        assert cp["pipeline_type"] == "airflow"
        assert cp["status"] == "running"
        assert cp["input_assets"] == "urn:upstream"
        assert cp["output_assets"] == "urn:downstream"


class TestSkills:
    """Test skill input/output models."""
    
    def test_video_asset_create_input(self):
        input = VideoAssetCreateInput(
            name="test",
            prompt="test prompt",
            model="veo-2",
            resolution="1920x1080",
            duration_seconds=5.0,
            codec="h264",
        )
        assert input.name == "test"
    
    def test_pipeline_register_input(self):
        input = PipelineRegisterInput(
            name="test pipeline",
            pipeline_type="prefect",
            dag_yaml="flow: test",
        )
        assert input.pipeline_type == "prefect"
    
    def test_list_skills(self):
        skills = list_skills()
        assert len(skills) >= 7  # All registered skills
        names = {s["name"] for s in skills}
        assert "create_video_asset" in names
        assert "register_pipeline" in names
        assert "trace_lineage" in names
        assert "validate_metadata" in names
    
    def test_get_skill(self):
        from nasl3yn_datahub.api.client import DataHubClient, DataHubConfig
        # Can't easily test without real client, but verify registry works
        from nasl3yn_datahub.skills.registry import SKILL_REGISTRY
        assert "create_video_asset" in SKILL_REGISTRY
        assert "register_pipeline" in SKILL_REGISTRY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])