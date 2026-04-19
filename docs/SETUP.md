# Development Setup Guide

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- AWS CLI (optional, for S3 features)
- Datadog account (optional, for APM)

## Quick Start

```bash
# Clone the repo
git clone https://github.com/vleung5/ai-workflow-automation-demo.git
cd ai-workflow-automation-demo

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your settings

# Run the app
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Running Tests

```bash
pip install pytest pytest-asyncio pytest-cov
pytest tests/ -v --cov=src
```

## Linting

```bash
pip install black flake8
black --check src/ tests/
flake8 src/ tests/ --max-line-length=100
```

## Docker

```bash
# Development (with hot-reload)
docker-compose up app-dev

# With Datadog Agent
DD_API_KEY=your_key_here docker-compose up datadog-agent app-dev
```

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values.

| Variable | Default | Description |
|---|---|---|
| `ENV` | `dev` | Environment name (`dev`, `stage`, `prod`) |
| `API_PORT` | `8000` | Application port |
| `S3_BUCKET` | `` | S3 bucket for CSV ingestion |
| `DATADOG_ENABLED` | `false` | Enable Datadog monitoring |
| `DATADOG_API_KEY` | `` | Datadog API key |
| `DD_SERVICE` | `ai-workflow-automation` | Datadog service name |

See `.env.example` for the full list.

## Project Structure

```
src/               Core application code
  api/             HTTP route handlers
    v1/            API version 1 routes
  core/            Business logic (no FastAPI dependencies)
  models/          Pydantic schemas and enums
  services/        External integrations (S3, Datadog, LLM)
  queue/           Celery workers
  utils/           Utility functions
tests/             Test suite (mirrors src/ structure)
scripts/           Developer utility scripts
docs/              Documentation
config/            YAML configs per environment
deploy/            Deployment artifacts
```
