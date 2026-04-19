# API Reference

Base URL: `http://localhost:8000`

## Health

### `GET /health`
Returns application health status.

**Response**
```json
{
  "status": "healthy",
  "service": "ai-workflow-automation",
  "environment": "dev",
  "s3_polling": "disabled",
  "version": "2.0.0",
  "datadog": "disabled"
}
```

---

## CSV Ingestion (`/v1`)

### `POST /v1/upload`
Upload a CSV file for processing.

**Request**: `multipart/form-data` with `file` field (`.csv` only)

**Response**
```json
{
  "job_id": "upload_abc123",
  "status": "completed",
  "total_records": 12,
  "processed_records": 12,
  "message": "CSV processed successfully"
}
```

### `GET /v1/jobs`
List all jobs.

---

## Status (`/v1`)

### `GET /v1/status/{job_id}`
Get processing status of a job.

**Response**
```json
{
  "job_id": "upload_abc123",
  "status": "completed",
  "processed_records": 12,
  "total_records": 12,
  "progress_percent": 100.0
}
```

---

## Results (`/v1`)

### `GET /v1/results/{job_id}`
Get detailed results including classification and summaries.

### `GET /v1/metrics`
Get aggregate application metrics.

---

## S3 (`/v1/s3`)

### `GET /v1/s3/status`
S3 polling service status.

### `GET /v1/s3/pending`
List pending S3 files.

### `POST /v1/s3/process`
Manually trigger processing of the next pending S3 file.

---

## Legacy Routes (backward-compatible)

All original routes are preserved:
- `GET /status/{job_id}`
- `GET /results/{job_id}`
- `GET /s3/status`
- `GET /s3/pending`
- `POST /s3/process`
- `GET /jobs`
- `GET /metrics`
