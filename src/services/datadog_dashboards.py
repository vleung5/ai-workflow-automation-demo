"""
Datadog Dashboard Configuration (create via API)
"""
from src.config import config

DASHBOARD_JSON = {
    "title": "AI Workflow Automation - Performance Monitor",
    "description": "Real-time monitoring of AI Workflow Automation system",
    "layout_type": "ordered",
    "widgets": [
        {
            "id": 1,
            "definition": {
                "title": "Polling Status",
                "show_title": True,
                "type": "query_value",
                "requests": [
                    {
                        "q": "avg:s3.pending_files{service:ai_workflow_automation}",
                        "aggregator": "last",
                    }
                ],
                "custom_links": [],
            },
        },
        {
            "id": 2,
            "definition": {
                "title": "Job Throughput (records/sec)",
                "show_title": True,
                "type": "timeseries",
                "requests": [
                    {
                        "q": "avg:job.throughput{service:ai_workflow_automation}",
                        "display_type": "line",
                    }
                ],
            },
        },
        {
            "id": 3,
            "definition": {
                "title": "Job Duration Distribution",
                "show_title": True,
                "type": "timeseries",
                "requests": [
                    {
                        "q": "avg:job.duration{service:ai_workflow_automation}",
                        "display_type": "line",
                    }
                ],
            },
        },
        {
            "id": 4,
            "definition": {
                "title": "Records Processing Success Rate",
                "show_title": True,
                "type": "gauge",
                "requests": [
                    {
                        "q": "avg:records.success_rate{service:ai_workflow_automation}",
                    }
                ],
            },
        },
        {
            "id": 5,
            "definition": {
                "title": "S3 Operations",
                "show_title": True,
                "type": "timeseries",
                "requests": [
                    {
                        "q": "sum:s3.operation.read{service:ai_workflow_automation}.as_count()",
                        "display_type": "bars",
                        "legend": {"show": True},
                    },
                    {
                        "q": "sum:s3.operation.write{service:ai_workflow_automation}.as_count()",
                        "display_type": "bars",
                    },
                    {
                        "q": "sum:s3.operation.failed{service:ai_workflow_automation}.as_count()",
                        "display_type": "bars",
                    },
                ],
            },
        },
        {
            "id": 6,
            "definition": {
                "title": "HTTP Request Duration",
                "show_title": True,
                "type": "timeseries",
                "requests": [
                    {
                        "q": "avg:http.request.duration{service:ai_workflow_automation} by {path}",
                        "display_type": "line",
                    }
                ],
            },
        },
        {
            "id": 7,
            "definition": {
                "title": "Error Rate",
                "show_title": True,
                "type": "query_value",
                "requests": [
                    {
                        "q": "sum:http.request.error{service:ai_workflow_automation}.as_count()",
                    }
                ],
            },
        },
        {
            "id": 8,
            "definition": {
                "title": "Logs",
                "type": "log_stream",
                "requests": [
                    {
                        "columns": ["timestamp", "status", "service", "message"],
                        "query": "service:ai_workflow_automation",
                    }
                ],
            },
        },
    ],
}


def get_dashboard_config() -> dict:
    """Get Datadog dashboard configuration"""
    return DASHBOARD_JSON


def create_dashboard():
    """Create dashboard via Datadog API"""

    if not config.DATADOG_ENABLED or not config.DATADOG_API_KEY:
        print("Skipping dashboard creation: Datadog monitoring is not enabled or API key is missing")
        return None

    try:
        from datadog import api

        dashboard = api.Dashboard.create(DASHBOARD_JSON)
        print(f"✓ Dashboard created: {dashboard.get('id')}")
        return dashboard

    except Exception as e:
        print(
            f"✗ Failed to create Datadog dashboard: {type(e).__name__}: {str(e)}. "
            "Verify API credentials and Datadog API connectivity."
        )
        return None
