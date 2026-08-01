# Example: Single Scene Generation Output

## Scene: desert_dawn_001

**Prompt:** "Cinematic desert dawn, golden hour lighting, sand dunes stretching to horizon, 8k resolution, photorealistic"

**Model:** veo-2  
**Resolution:** 3840x2160  
**Duration:** 8 seconds  
**Codec:** hevc  
**Generation Time:** ~45 seconds  
**Estimated Cost:** $0.15

## DataHub Asset URN
```
urn:li:dataset:(urn:li:dataPlatform:nasl3yn,desert_dawn_001_render,PROD)
```

## Pipeline DAG (Airflow)
```yaml
# Pipeline for desert_dawn_001
dag_id: "nasl3yn_desert_dawn_001"
schedule: "@once"
start_date: "2026-08-01"
tasks:
  - task_id: "generate_video"
    operator: "PythonOperator"
    python_callable: "generate_with_veo2"
    op_kwargs:
      prompt: "Cinematic desert dawn, golden hour lighting, sand dunes stretching to horizon, 8k resolution, photorealistic"
      model: "veo-2"
      resolution: "3840x2160"
      duration_seconds: 8
      seed: 4294967295
  
  - task_id: "encode_video"
    operator: "PythonOperator"
    python_callable: "encode_hevc"
    op_kwargs:
      input_path: "{{ ti.xcom_pull(task_ids='generate_video') }}"
      codec: "hevc"
      crf: 18
  
  - task_id: "register_asset"
    operator: "PythonOperator"
    python_callable: "register_in_datahub"
    op_kwargs:
      asset_urn: "urn:li:dataset:(urn:li:dataPlatform:nasl3yn,desert_dawn_001_render,PROD)"
      lineage_upstream: ["prompt_desert_dawn_001"]
```

## Lineage Graph
```
prompt_desert_dawn_001
       │
       ▼
generate_video (veo-2)
       │
       ▼
encode_video (hevc)
       │
       ▼
desert_dawn_001_render ───▶ DataHub Asset
       │
       ▼
[downstream: editing, distribution, analytics]
```

## Cinematic Metadata (stored in DataHub)
```json
{
  "urn": "urn:li:dataset:(urn:li:dataPlatform:nasl3yn,desert_dawn_001_render,PROD)",
  "name": "desert_dawn_001_render",
  "description": "Cinematic desert dawn scene - golden hour",
  "customProperties": {
    "prompt": "Cinematic desert dawn, golden hour lighting, sand dunes stretching to horizon, 8k resolution, photorealistic",
    "model": "veo-2",
    "resolution": "3840x2160",
    "duration_seconds": "8.0",
    "codec": "hevc",
    "seed": "4294967295",
    "generation_time_ms": "45000",
    "cost_usd": "0.15",
    "tags": "desert,dawn,golden_hour,cinematic,8k"
  }
}
```