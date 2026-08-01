# Example: Multi-Scene Project — "Nasl3yn Covenant" (6 scenes)

## Project Overview
**Name:** Nasl3yn Covenant Documentary  
**Scenes:** 6 scenes (day_1 through day_6)  
**Theme:** Arabic civilizational narrative — tools, AI, sovereignty  
**Model:** veo-2  
**Resolution:** 3840x2160 (4K)  
**Total Duration:** ~48 seconds (8s per scene)

## Scene Breakdown

| Scene | Name | Prompt Summary | Duration |
|-------|------|----------------|----------|
| 1 | origins | Primitive tools, early civilization, fire, stone | 8s |
| 2 | tools_evolution | Tools evolving from simple to complex | 8s |
| 3 | knowledge_library | Circular library, knowledge accumulation | 8s |
| 4 | electrical_dawn | Electrical/mechanical revolution | 8s |
| 5 | ai_emergence | AI systems emerging, neural networks | 8s |
| 6 | covenant_tree | QSR roots → MineAIder trunk → HADA/ZAKA branches | 8s |

## DataHub Asset URNs
```
urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_1_render,PROD)
urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_2_render,PROD)
urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_3_render,PROD)
urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_4_render,PROD)
urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_5_render,PROD)
urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_6_render,PROD)
```

## Multi-Scene Pipeline DAG (Prefect)
```yaml
flow_name: "nasl3yn_covenant_documentary"
description: "6-scene cinematic documentary generation pipeline"
tasks:
  # Parallel scene generation
  - name: "generate_day_1"
    depends_on: []
    params:
      scene: "day_1"
      prompt: "Primitive tools, early human civilization discovering fire and stone tools, cinematic lighting, 8k"
  
  - name: "generate_day_2"
    depends_on: []
    params:
      scene: "day_2"
      prompt: "Evolution of tools from primitive stone to bronze to iron, montage, cinematic"
  
  - name: "generate_day_3"
    depends_on: []
    params:
      scene: "day_3"
      prompt: "Massive circular library of knowledge, glowing books, aerial view, cinematic"
  
  - name: "generate_day_4"
    depends_on: []
    params:
      scene: "day_4"
      prompt: "Industrial revolution, electrical machinery, steam engines, dawn lighting"
  
  - name: "generate_day_5"
    depends_on: []
    params:
      scene: "day_5"
      prompt: "AI neural networks visualizing, data flowing, futuristic, bioluminescent"
  
  - name: "generate_day_6"
    depends_on: []
    params:
      scene: "day_6"
      prompt: "Great covenant tree: QSR roots, MineAIder trunk, HADA knowledge branch, ZAKA business branch, data streams forming calligraphic Arabic letters"

  # Encoding (parallel after generation)
  - name: "encode_all"
    depends_on: ["generate_day_1", "generate_day_2", "generate_day_3", "generate_day_4", "generate_day_5", "generate_day_6"]
    params:
      codec: "hevc"
      crf: 18
  
  # Registration
  - name: "register_assets"
    depends_on: ["encode_all"]
    params:
      asset_urns: [
        "urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_1_render,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_2_render,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_3_render,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_4_render,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_5_render,PROD)",
        "urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_6_render,PROD)"
      ]
```

## Lineage Graph (Day 6 - Covenant Tree)
```
prompt_nasl3yn_covenant
         │
         ├──▶ day_1_render (origins)
         ├──▶ day_2_render (tools)
         ├──▶ day_3_render (knowledge)
         ├──▶ day_4_render (electrical)
         ├──▶ day_5_render (AI)
         └──▶ day_6_render (covenant tree)
                        │
                        ├──▶ QRS_root_asset
                        ├──▶ MineAIder_trunk_asset
                        ├──▶ HADA_branch_asset
                        └──▶ ZAKA_branch_asset
```

## Cinematic Metadata Schema (per scene)
```json
{
  "urn": "urn:li:dataset:(urn:li:dataPlatform:nasl3yn,nasl3yn_covenant_day_6_render,PROD)",
  "name": "nasl3yn_covenant_day_6_render",
  "description": "Covenant tree finale - QSR roots, MineAIder trunk, HADA/ZAKA branches",
  "customProperties": {
    "prompt": "Great covenant tree: QSR roots, MineAIder trunk, HADA knowledge branch, ZAKA business branch, data streams forming calligraphic Arabic letters",
    "model": "veo-2",
    "resolution": "3840x2160",
    "duration_seconds": "8.0",
    "codec": "hevc",
    "seed": "1234567890",
    "generation_time_ms": "52000",
    "cost_usd": "0.18",
    "tags": "covenant,tree,QSR,MineAIder,HADA,ZAKA,arabic,calligraphy,finale",
    "project": "nasl3yn_covenant",
    "scene_number": "6",
    "scene_name": "covenant_tree"
  }
}
```