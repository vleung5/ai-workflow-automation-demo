# Architecture

## Overview

AI Workflow Automation Demo is a FastAPI-based service that ingests CSV files (via direct upload or S3 polling), classifies each record using keyword-based AI logic, and returns structured results.

## Component Map

```
┌─────────────────────────────────────────────────┐
│                  Clients / UI                   │
└────────────────────┬────────────────────────────┘
                     │ HTTP
┌────────────────────▼────────────────────────────┐
│              src/main.py  (FastAPI)             │
│  ┌──────────────────────────────────────────┐  │
│  │  src/api/middleware.py  (CORS, Datadog)  │  │
│  ├──────────────────────────────────────────┤  │
│  │  src/api/health.py      /health          │  │
│  │  src/api/v1/            /v1/*            │  │
│  │    csv_ingestion.py     /v1/upload       │  │
│  │    status.py            /v1/status/{id} │  │
│  │    results.py           /v1/results/{id}│  │
│  │    s3_routes.py         /v1/s3/*        │  │
│  └──────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│              src/core/                          │
│  processor.py  ← orchestrates the pipeline     │
│  validator.py  ← data validation rules         │
│  classifier.py ← keyword-based AI              │
│  report_generator.py ← report creation         │
└──────┬──────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────┐
│              src/services/                      │
│  s3_service.py     ← S3 polling & file I/O     │
│  datadog_service.py← APM, metrics, events      │
│  llm_service.py    ← OpenAI/Claude (optional)  │
└─────────────────────────────────────────────────┘
```

## Data Flow

1. **Ingest** — CSV arrives via `/v1/upload` or S3 polling (`src/services/s3_service.py`)
2. **Parse** — `src/utils/csv_parser.py` converts raw bytes to row dicts
3. **Validate** — `src/core/validator.py` checks required fields and lengths
4. **Classify** — `src/core/classifier.py` assigns priority, sentiment, and category
5. **Summarise** — A short text summary is generated per record
6. **Store** — Results are stored in memory (`processor.jobs`) and optionally uploaded to S3
7. **Report** — `src/core/report_generator.py` aggregates statistics

## Configuration

Environment-specific configuration is in `config/dev.yaml`, `config/stage.yaml`, `config/prod.yaml` and loaded via environment variables (see `src/config.py`).

## Monitoring

Datadog APM is integrated in `src/services/datadog_service.py`. The middleware in `src/api/middleware.py` automatically tracks HTTP request durations. Job-level metrics are emitted from `src/core/processor.py`.
