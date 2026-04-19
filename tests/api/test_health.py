"""Tests for health check endpoint"""

from unittest.mock import patch


def test_health_check_structure():
    """Health endpoint returns expected keys"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.api.health import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    with patch("src.api.health.get_s3_polling_service", return_value=None):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "service" in data
    assert "environment" in data
    assert "version" in data
    assert "datadog" in data
    assert "s3_polling" in data
