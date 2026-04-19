import os
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class EnvironmentConfig:
    """Base configuration for all environments"""
    
    # Environment
    ENV = os.getenv("ENV", "dev")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    
    # Processing Configuration
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 4))
    QUEUE_MAX_SIZE = int(os.getenv("QUEUE_MAX_SIZE", 100))
    
    # File Upload Configuration
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
    ALLOWED_EXTENSIONS = {"csv"}
    
    # S3 Configuration
    S3_BUCKET = os.getenv("S3_BUCKET", "")
    S3_PREFIX = os.getenv("S3_PREFIX", "incoming/")
    S3_POLLING_INTERVAL = int(os.getenv("S3_POLLING_INTERVAL", 30))
    
    # Classification Configuration
    CLASSIFICATION_CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.6))
    PRIORITY_KEYWORDS = {
        "urgent": ["critical", "emergency", "asap", "urgent", "immediate"],
        "normal": ["important", "needed", "required", "scheduled"],
        "low": ["nice to have", "optional", "future", "backlog"]
    }
    
    # AWS Configuration
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_SECRETS_MANAGER_ENABLED = os.getenv("AWS_SECRETS_MANAGER_ENABLED", "False").lower() == "true"
    SECRET_NAME = os.getenv("SECRET_NAME", f"ai-workflow-automation/{os.getenv('ENV', 'dev')}/secrets")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # ==================== DATADOG CONFIGURATION ====================
    
    # Datadog Enable/Disable
    DATADOG_ENABLED = os.getenv("DATADOG_ENABLED", "False").lower() == "true"
    DATADOG_SITE = os.getenv("DATADOG_SITE", "datadoghq.com")
    
    # Datadog API Keys
    DATADOG_API_KEY = os.getenv("DATADOG_API_KEY", "")
    DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY", "")
    
    # Datadog Agent Configuration
    DATADOG_AGENT_HOST = os.getenv("DATADOG_AGENT_HOST", "localhost")
    DATADOG_AGENT_PORT = int(os.getenv("DATADOG_AGENT_PORT", 8126))
    
    # Datadog Service Configuration
    DD_SERVICE = os.getenv("DD_SERVICE", "ai-workflow-automation")
    DD_VERSION = os.getenv("DD_VERSION", "2.0.0")
    DD_ENV = os.getenv("DD_ENV", ENV)
    
    # Datadog Trace Configuration
    DD_TRACE_ENABLED = os.getenv("DD_TRACE_ENABLED", "True").lower() == "true"
    DD_APM_ENABLED = os.getenv("DD_APM_ENABLED", "True").lower() == "true"
    DD_SAMPLE_RATE = float(os.getenv("DD_SAMPLE_RATE", 1.0 if ENV == "prod" else 0.1))
    DD_TRACE_DEBUG = os.getenv("DD_TRACE_DEBUG", "False").lower() == "true"
    
    # Datadog Metrics Configuration
    DD_METRICS_ENABLED = os.getenv("DD_METRICS_ENABLED", "True").lower() == "true"
    DD_METRICS_NAMESPACE = os.getenv("DD_METRICS_NAMESPACE", "ai_workflow")
    
    # Datadog Profiler Configuration
    DD_PROFILER_ENABLED = os.getenv("DD_PROFILER_ENABLED", "False").lower() == "true"
    DD_PROFILER_SERVICE = os.getenv("DD_PROFILER_SERVICE", DD_SERVICE)
    
    # Datadog Logging Configuration
    DD_JSON_LOGGING = os.getenv("DD_JSON_LOGGING", "True").lower() == "true"
    DD_LOG_CORRELATION = os.getenv("DD_LOG_CORRELATION", "True").lower() == "true"
    
    # Datadog Custom Tags
    DD_TAGS = os.getenv("DD_TAGS", "team:platform,cost_center:engineering")
    
    # Build tags dictionary
    @classmethod
    def get_datadog_tags(cls) -> Dict[str, str]:
        """Build Datadog tags dictionary"""
        tags = {
            "service": cls.DD_SERVICE,
            "version": cls.DD_VERSION,
            "environment": cls.DD_ENV,
        }
        
        # Parse custom tags
        if cls.DD_TAGS:
            for tag_pair in cls.DD_TAGS.split(","):
                if ":" in tag_pair:
                    key, value = tag_pair.strip().split(":", 1)
                    tags[key] = value
        
        return tags


class DevelopmentConfig(EnvironmentConfig):
    """Development Environment Configuration"""
    
    ENV = "dev"
    DEBUG = True
    API_PORT = 8000
    MAX_WORKERS = 2
    MAX_FILE_SIZE_MB = 100
    LOG_LEVEL = "DEBUG"
    AWS_SECRETS_MANAGER_ENABLED = False
    S3_BUCKET = os.getenv("S3_BUCKET", "ai-workflow-automation-dev")
    S3_POLLING_INTERVAL = 10
    
    # Datadog Configuration for Development
    DATADOG_ENABLED = os.getenv("DATADOG_ENABLED", "True").lower() == "true"
    DD_TRACE_ENABLED = True
    DD_APM_ENABLED = True
    DD_SAMPLE_RATE = 0.1  # Low sample rate in dev
    DD_TRACE_DEBUG = os.getenv("DD_TRACE_DEBUG", "True").lower() == "true"
    DD_PROFILER_ENABLED = False  # Disabled in dev for performance
    DD_JSON_LOGGING = True


class StagingConfig(EnvironmentConfig):
    """Staging Environment Configuration"""
    
    ENV = "stage"
    DEBUG = False
    API_PORT = 8000
    MAX_WORKERS = 4
    MAX_FILE_SIZE_MB = 500
    LOG_LEVEL = "INFO"
    AWS_SECRETS_MANAGER_ENABLED = True
    S3_BUCKET = os.getenv("S3_BUCKET", "ai-workflow-automation-stage")
    S3_POLLING_INTERVAL = 20
    
    # Datadog Configuration for Staging
    DATADOG_ENABLED = os.getenv("DATADOG_ENABLED", "True").lower() == "true"
    DD_TRACE_ENABLED = True
    DD_APM_ENABLED = True
    DD_SAMPLE_RATE = 0.5  # Medium sample rate in staging
    DD_TRACE_DEBUG = False
    DD_PROFILER_ENABLED = False
    DD_JSON_LOGGING = True


class ProductionConfig(EnvironmentConfig):
    """Production Environment Configuration"""
    
    ENV = "prod"
    DEBUG = False
    API_PORT = 8000
    MAX_WORKERS = 8
    MAX_FILE_SIZE_MB = 1000
    LOG_LEVEL = "WARNING"
    AWS_SECRETS_MANAGER_ENABLED = True
    S3_BUCKET = os.getenv("S3_BUCKET", "ai-workflow-automation-prod")
    S3_POLLING_INTERVAL = 30
    
    # Datadog Configuration for Production
    DATADOG_ENABLED = os.getenv("DATADOG_ENABLED", "True").lower() == "true"
    DD_TRACE_ENABLED = True
    DD_APM_ENABLED = True
    DD_SAMPLE_RATE = 1.0  # Full sample rate in production
    DD_TRACE_DEBUG = False
    DD_PROFILER_ENABLED = True  # Enabled in prod for profiling
    DD_JSON_LOGGING = True


def get_config() -> EnvironmentConfig:
    """Get configuration based on environment variable"""
    env = os.getenv("ENV", "dev").lower()
    
    config_map = {
        "dev": DevelopmentConfig,
        "stage": StagingConfig,
        "prod": ProductionConfig,
    }
    
    config_class = config_map.get(env, DevelopmentConfig)
    logger.info(f"Loaded configuration for environment: {config_class.ENV}")
    
    return config_class()


def get_secrets_from_aws(secret_name: str) -> Dict[str, Any]:
    """Retrieve secrets from AWS Secrets Manager"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        
        try:
            response = client.get_secret_value(SecretId=secret_name)
        except ClientError as e:
            logger.error(f"Error retrieving secret {secret_name}: {str(e)}")
            return {}
        
        if "SecretString" in response:
            return json.loads(response["SecretString"])
        else:
            return {}
            
    except ImportError:
        logger.warning("boto3 not installed, skipping AWS Secrets Manager")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error retrieving secrets: {str(e)}")
        return {}


def apply_secrets_to_config(config: EnvironmentConfig) -> None:
    """Apply secrets from AWS Secrets Manager to configuration"""
    if not config.AWS_SECRETS_MANAGER_ENABLED:
        logger.info("AWS Secrets Manager disabled")
        return
    
    logger.info(f"Retrieving secrets from AWS Secrets Manager: {config.SECRET_NAME}")
    secrets = get_secrets_from_aws(config.SECRET_NAME)
    
    for key, value in secrets.items():
        if hasattr(config, key):
            setattr(config, key, value)
            logger.debug(f"Applied secret: {key}")


def validate_datadog_config(config: EnvironmentConfig) -> bool:
    """Validate Datadog configuration"""
    
    if not config.DATADOG_ENABLED:
        logger.info("Datadog monitoring disabled")
        return False
    
    # Check if using API or Agent
    has_api_config = config.DATADOG_API_KEY and config.DATADOG_APP_KEY
    has_agent_config = config.DATADOG_AGENT_HOST and config.DATADOG_AGENT_PORT
    
    if not has_api_config and not has_agent_config:
        logger.warning("Datadog enabled but no API keys or agent configured")
        return False
    
    if has_api_config:
        logger.info(f"✓ Datadog API configured (site: {config.DATADOG_SITE})")
    
    if has_agent_config:
        logger.info(f"✓ Datadog Agent configured ({config.DATADOG_AGENT_HOST}:{config.DATADOG_AGENT_PORT})")
    
    logger.info(f"✓ Datadog APM enabled: {config.DD_APM_ENABLED}")
    logger.info(f"✓ Datadog Metrics enabled: {config.DD_METRICS_ENABLED}")
    logger.info(f"✓ Datadog Profiler enabled: {config.DD_PROFILER_ENABLED}")
    logger.info(f"✓ Sample rate: {config.DD_SAMPLE_RATE}")
    
    return True


# Initialize configuration
config = get_config()

# Apply AWS Secrets Manager overrides if enabled
if config.AWS_SECRETS_MANAGER_ENABLED:
    apply_secrets_to_config(config)

# Validate Datadog configuration
validate_datadog_config(config)

# Log configuration summary
logger.info(f"Configuration initialized for {config.ENV} environment")
logger.info(f"Service: {config.DD_SERVICE} v{config.DD_VERSION}")
logger.info(f"API: {config.API_HOST}:{config.API_PORT}")
logger.info(f"Log Level: {config.LOG_LEVEL}")
if config.S3_BUCKET:
    logger.info(f"S3 Bucket: {config.S3_BUCKET}")
