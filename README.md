# Nasl3yn DataHub Agent — Cinematic Context Platform

Apache 2.0 License

## Overview

An AI agent that gives video generation pipelines full context via DataHub's open-source Context Platform. Tracks video asset lineage, stores cinematic metadata schemas, and exposes MCP Server for autonomous video workflow orchestration.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Nasl3yn Agent  │────▶│  DataHub MCP     │────▶│  DataHub Graph  │
│  (Orchestrator) │     │  Server + Skills │     │  (Cinematic)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Video Pipeline  │     │  Cinematic       │     │  Asset Lineage  │
│  (Airflow/DAG)  │     │  Skills          │     │  (Prompt→Output)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Quick Start

```bash
# Install dependencies
pip install -e .

# Configure DataHub connection
export DATAHUB_GMS_URL="https://your-datahub-instance.com"
export DATAHUB_TOKEN="your-token"

# Run the agent
python -m nasl3yn_datahub.agent.main --config config.yaml
```

## Project Structure

```
nasl3yn-datahub-hackathon/
├── LICENSE                 # Apache 2.0
├── pyproject.toml          # Package config
├── config.yaml.example     # Configuration template
├── src/
│   └── nasl3yn_datahub/
│       ├── __init__.py
│       ├── api/            # DataHub API client
│       ├── mcp_server/     # MCP Server integration
│       ├── skills/         # DataHub Skills for cinematic ops
│       └── agent/          # Autonomous orchestrator
├── examples/               # Sample outputs for judges
├── tests/                  # Unit tests
└── docs/                   # Architecture docs
```

## Core Components

### 1. DataHub API Client (`src/nasl3yn_datahub/api/`)
- GraphQL/REST wrapper for DataHub
- Asset CRUD, lineage, search
- Authentication handling

### 2. MCP Server Integration (`src/nasl3yn_datahub/mcp_server/`)
- Exposes cinematic operations to agents
- Tools: create_asset, trace_lineage, query_metadata, register_pipeline

### 3. Cinematic Skills (`src/nasl3yn_datahub/skills/`)
- `VideoAssetSkill` — register/track video assets
- `PipelineSkill` — manage generation pipelines
- `LineageSkill` — trace prompt→model→render→output
- `MetadataSkill` — schema validation for cinematic metadata

### 4. Orchestrator Agent (`src/nasl3yn_datahub/agent/`)
- Autonomous video pipeline orchestration
- Reads DataHub context via MCP
- Plans and executes generation workflows
- Writes results back to DataHub graph

## Cinematic Metadata Schema

```yaml
# Video Asset Entity
urn: "urn:li:dataset:(urn:li:dataPlatform:nasl3yn,cinematic_asset,PROD)"
properties:
  name: "scene_001_final_render"
  description: "Final render of scene 1 - desert dawn"
  customProperties:
    prompt: "cinematic desert dawn, golden hour, 8k"
    model: "veo-2"
    resolution: "3840x2160"
    duration_seconds: 8
    codec: "hevc"
    seed: 4294967295
    generation_time_ms: 45000
    cost_usd: 0.15
```

## License

Apache 2.0 — see LICENSE file.