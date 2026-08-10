# Agentic Cinema: The Blockbuster Hackathon - Nasl3yn Submission Plan

**Hackathon:** Agentic Cinema: The Blockbuster Hackathon
**URL:** https://agentic-cinema.devpost.com/
**Deadline:** September 7, 2026
**Prize:** $75,000
**Tracks:** 5 partner tracks (Google Cloud/Gemini, IBM, Grafana, Parallel, Confluent)

---

## Nasl3yn Asset Inventory for Submission

### Core Cinematic Assets (Ready)
| Asset | Description | Status |
|-------|-------------|--------|
| **Nasl3yn Orchestrator** | Autonomous cinematic agent orchestrating video pipelines via MCP | ✅ Built |
| **Video Pipeline DAGs** | Airflow/Prefect DAGs for Veo-2 generation, encoding, QC | ✅ Built |
| **Cinematic Metadata Schema** | Prompt, model, resolution, duration, codec, seed, cost tracking | ✅ Defined |
| **DataHub MCP Integration** | Cinematic asset lineage in DataHub graph | ✅ Integrated |
| **Demo Scenes** | 6-scene "Nasl3yn Covenant" documentary (48s total) | 🔄 Rendering |
| **Cinematic Skills** | DataHub Skills for video asset CRUD, lineage, pipeline registration | ✅ Built |

### Partner Track Mapping

| Partner | Track | Nasl3yn Component | Integration Status | Demo Hook |
|---------|-------|-------------------|-------------------|-----------|
| **Google Cloud / Gemini** | Core | Veo-2 generation, Gemini Pro for prompt engineering | ✅ Native | "Powered by Veo-2 on Vertex AI" |
| **Grafana** | Observability | Grafana MCP Server for agent telemetry, token spend, latency | 🔄 MCP Server ready | Live dashboards in demo |
| **Parallel** | Web Grounding | Parallel Search API for cinematic reference research | 🔄 SDK ready | Real-time reference fetching |
| **IBM** | Enterprise | watsonx integration for compliance/audit trails | 🔄 Planned | watsonx.governance badge |
| **Confluent** | Streaming | Kafka for real-time pipeline event streaming | 🔄 Planned | Event-driven pipeline |

---

## Submission Deliverables Checklist

### Required (All)
- [ ] **Project URL** - Live demo or hosted app with clear setup instructions
- [ ] **Public GitHub Repo** - Apache 2.0 license visible in About section
- [ ] **Text Description** - Features, functionality, technologies, data used
- [ ] **Demo Video** - <3 min, YouTube/Vimeo public, shows project functioning
- [ ] **Sample Outputs** - `examples/` folder with generated artifacts

### Track-Specific
- [ ] **Grafana**: MCP Server running, dashboards showing agent telemetry
- [ ] **Parallel**: Search API calls visible in pipeline logs
- [ ] **IBM**: watsonx.governance or Bob integration evidence
- [ ] **Confluent**: Kafka topics for pipeline events
- [ ] **Gemini**: Vertex AI project with Veo-2 quota

---

## Demo Video Script (3 min max)

### 0:00-0:30 - Problem & Vision
> "Cinematic AI production is chaotic. No lineage, no observability, no grounding. Nasl3yn fixes this."

### 0:30-1:00 - Architecture Overview
> Show DataHub graph with cinematic assets, lineage from prompt → Veo-2 → render → encode.

### 1:00-1:30 - Grafana MCP Observability
> Live dashboard: token spend, latency, errors per agent. "Production context for AI agents."

### 1:30-2:00 - Parallel Web Grounding
> Agent fetches cinematic references in real-time via Parallel Search API.

### 2:00-2:30 - Pipeline Execution
> Trigger 6-scene "Nasl3yn Covenant" generation. Show DataHub lineage updates in real-time.

### 2:30-3:00 - Results & Impact
> "48s cinematic documentary, full lineage, $0.15/scene, enterprise-ready."

---

## Repository Structure for Submission

```
nasl3yn-agentic-cinema/
├── LICENSE (Apache 2.0)
├── README.md (setup, architecture, demo instructions)
├── .github/workflows/ci.yml
├── docker-compose.yml (full stack: orchestrator, grafana, kafka, mcp)
├── nasl3yn_orchestrator/          # Core agent
├── nasl3yn_mcp_server/            # DataHub MCP Server
├── nasl3yn_skills/                # DataHub Skills
├── nasl3yn_grafana_mcp/           # Grafana MCP Server
├── nasl3yn_parallel/              # Parallel Search integration
├── pipelines/                     # Airflow/Prefect DAGs
├── examples/
│   ├── covenant_day_1_render.mp4
│   ├── covenant_day_2_render.mp4
│   ├── pipeline_dag.yaml
│   └── cinematic_metadata.json
├── grafana/
│   ├── dashboards/nasl3yn_orchestrator.json
│   └── datasources/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── demo_instructions.md
└── demo_video.mp4 (YouTube link in README)
```

---

## Timeline to Sep 7 Deadline

| Week | Focus | Deliverable |
|------|-------|-------------|
| **Aug 4-10** | Core Demo | 6-scene renders, DataHub lineage, demo video |
| **Aug 11-17** | Grafana MCP | MCP Server + dashboards live |
| **Aug 18-24** | Parallel Integration | Search API in pipeline |
| **Aug 25-31** | IBM/Confluent | watsonx + Kafka integration |
| **Sep 1-7** | Polish & Submit | Demo video, README, GitHub public, Devpost submit |

---

## Quick Wins for Higher Score

| Criteria | Action |
|----------|--------|
| **Use of Partner Tech** | Explicitly call out each partner in README + demo |
| **Technical Execution** | All pipelines run end-to-end in demo |
| **Originality** | "Cinematic Context Platform" - first of its kind |
| **Real-World Usefulness** | Solves actual cinematic AI production pain |
| **Submission Quality** | 3-min demo video, comprehensive README |
| **Open Source Contribution** | DataHub Skills + Grafana MCP as reusable packages |

---

## Submission Commands

```bash
# 1. Finalize repo
cd /home/ahm/nasl3yn-datahub-hackathon
git init && git add . && git commit -m "Agentic Cinema submission"

# 2. Push to GitHub (public, Apache 2.0)
gh repo create nasl3yn/agentic-cinema --public --license Apache-2.0 --push

# 3. Record demo video (3 min)
# Upload to YouTube (public), add link to README

# 4. Submit on Devpost
# https://agentic-cinema.devpost.com/register?flow[data][challenge_id]=...&flow[name]=register_for_challenge

# 5. Select tracks: Gemini, Grafana, Parallel, IBM, Confluent
```

---

## Contact & Support

- **Devpost Questions**: [Devpost Discord](https://discord.gg/devpost)
- **Partner SDKs**:
  - [Grafana MCP](https://grafana.com/docs/grafana-cloud/developer-platform/mcp/)
  - [Parallel SDK](https://docs.parallel.ai/)
  - [IBM Bob](https://www.ibm.com/products/bob)
  - [Confluent Cloud](https://confluent.io/cloud/)
  - [Vertex AI Veo-2](https://cloud.google.com/vertex-ai/docs/generative-ai/video/generate-video)

---

*Last updated: 2026-08-04*
*Target submit: 2026-09-05 (2 days buffer)*