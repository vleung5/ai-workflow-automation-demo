"""
Datadog APM and Monitoring Configuration
"""
import os
import logging
from typing import Optional
from datadog import initialize, api
from ddtrace import config, patch
from ddtrace.contrib.fastapi import patch_all
import structlog
from pythonjsonlogger import jsonlogger

logger = logging.getLogger(__name__)


class DatadogConfig:
    """Datadog configuration for APM, logging, and monitoring"""
    
    # Datadog settings
    DATADOG_ENABLED = os.getenv("DATADOG_ENABLED", "False").lower() == "true"
    DATADOG_API_KEY = os.getenv("DATADOG_API_KEY", "")
    DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY", "")
    DATADOG_SITE = os.getenv("DATADOG_SITE", "datadoghq.com")
    DATADOG_AGENT_HOST = os.getenv("DATADOG_AGENT_HOST", "localhost")
    DATADOG_AGENT_PORT = int(os.getenv("DATADOG_AGENT_PORT", 8126))
    
    # Service configuration
    SERVICE_NAME = os.getenv("DD_SERVICE", "ai-workflow-automation")
    SERVICE_VERSION = os.getenv("DD_VERSION", "2.0.0")
    ENVIRONMENT = os.getenv("DD_ENV", os.getenv("ENV", "dev"))
    
    # Trace settings
    TRACE_ENABLED = os.getenv("DD_TRACE_ENABLED", "True").lower() == "true"
    TRACE_DEBUG = os.getenv("DD_TRACE_DEBUG", "False").lower() == "true"
    SAMPLE_RATE = float(os.getenv("DD_SAMPLE_RATE", 1.0 if ENVIRONMENT == "prod" else 0.1))
    
    # Metrics settings
    METRICS_ENABLED = os.getenv("DD_METRICS_ENABLED", "True").lower() == "true"
    METRICS_NAMESPACE = os.getenv("DD_METRICS_NAMESPACE", "ai_workflow")
    
    # Profiler settings
    PROFILER_ENABLED = os.getenv("DD_PROFILER_ENABLED", "False").lower() == "true"
    PROFILER_SERVICE = os.getenv("DD_PROFILER_SERVICE", SERVICE_NAME)
    
    # Logging settings
    JSON_LOGGING = os.getenv("DD_JSON_LOGGING", "True").lower() == "true"
    LOG_CORRELATION = os.getenv("DD_LOG_CORRELATION", "True").lower() == "true"
    
    # Custom tags
    CUSTOM_TAGS = {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "environment": ENVIRONMENT,
    }


def initialize_datadog():
    """Initialize Datadog APM and monitoring"""
    
    if not DatadogConfig.DATADOG_ENABLED:
        logger.info("Datadog monitoring disabled")
        return False
    
    logger.info("🔍 Initializing Datadog APM and Monitoring...")
    
    try:
        # Initialize Datadog API
        if DatadogConfig.DATADOG_API_KEY and DatadogConfig.DATADOG_APP_KEY:
            initialize(
                api_key=DatadogConfig.DATADOG_API_KEY,
                app_key=DatadogConfig.DATADOG_APP_KEY,
                api_version="v1"
            )
            logger.info("✓ Datadog API initialized")
        
        # Patch libraries for automatic instrumentation
        logger.info("📦 Patching libraries for automatic instrumentation...")
        
        # Patch FastAPI
        patch_all(fastapi=True)
        
        # Patch AWS/boto3
        patch(modules=["boto3", "botocore"])
        
        # Configure ddtrace
        config.dd_trace_enabled = DatadogConfig.TRACE_ENABLED
        config.analytics_enabled = True
        config.analytics_sample_rate = DatadogConfig.SAMPLE_RATE
        config.debug = DatadogConfig.TRACE_DEBUG
        
        # Set trace context
        config.tags = DatadogConfig.CUSTOM_TAGS
        
        logger.info("✓ Datadog APM initialized")
        logger.info(f"  Service: {DatadogConfig.SERVICE_NAME}")
        logger.info(f"  Environment: {DatadogConfig.ENVIRONMENT}")
        logger.info(f"  Version: {DatadogConfig.SERVICE_VERSION}")
        logger.info(f"  Agent: {DatadogConfig.DATADOG_AGENT_HOST}:{DatadogConfig.DATADOG_AGENT_PORT}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Datadog: {str(e)}")
        return False


def setup_structured_logging():
    """Setup structured logging with Datadog correlation"""
    
    logger_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": jsonlogger.JsonFormatter,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            },
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "json" if DatadogConfig.JSON_LOGGING else "standard",
                "stream": "ext://sys.stdout"
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"]
        }
    }
    
    # Setup structlog for structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logger.info("✓ Structured logging configured")


def get_datadog_tags(additional_tags: dict = None) -> dict:
    """Get Datadog tags for custom spans"""
    tags = DatadogConfig.CUSTOM_TAGS.copy()
    if additional_tags:
        tags.update(additional_tags)
    return tags


def send_datadog_event(title: str, text: str, alert_type: str = "info", tags: list = None):
    """Send event to Datadog"""
    
    if not DatadogConfig.DATADOG_ENABLED or not DatadogConfig.DATADOG_API_KEY:
        logger.warning("Datadog not enabled, event not sent")
        return
    
    try:
        from datadog import api
        
        event_tags = tags or []
        event_tags.extend([f"{k}:{v}" for k, v in DatadogConfig.CUSTOM_TAGS.items()])
        
        api.Event.create(
            title=title,
            text=text,
            alert_type=alert_type,
            tags=event_tags,
            priority="normal"
        )
        
        logger.info(f"Datadog event sent: {title}")
        
    except Exception as e:
        logger.error(f"Failed to send Datadog event: {str(e)}")


def send_datadog_metric(metric_name: str, value: float, metric_type: str = "gauge", tags: dict = None):
    """Send custom metric to Datadog"""
    
    if not DatadogConfig.DATADOG_ENABLED or not DatadogConfig.DATADOG_API_KEY:
        return
    
    try:
        from datadog import api
        
        metric_tags = get_datadog_tags(tags)
        tag_list = [f"{k}:{v}" for k, v in metric_tags.items()]
        
        api.Metric.send(
            metric=f"{DatadogConfig.METRICS_NAMESPACE}.{metric_name}",
            points=value,
            metric_type=metric_type,
            tags=tag_list
        )
        
    except Exception as e:
        logger.error(f"Failed to send Datadog metric: {str(e)}")
