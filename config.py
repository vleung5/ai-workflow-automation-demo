import os
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class EnvironmentConfig:
    """Base configuration for all environments"""
    
    ENV = os.getenv("ENV", "dev")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 4))
    QUEUE_MAX_SIZE = int(os.getenv("QUEUE_MAX_SIZE", 100))
    
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
    ALLOWED_EXTENSIONS = {"csv"}
    
    # S3 Configuration (NEW)
    S3_BUCKET = os.getenv("S3_BUCKET", "")
    S3_PREFIX = os.getenv("S3_PREFIX", "incoming/")
    S3_POLLING_INTERVAL = int(os.getenv("S3_POLLING_INTERVAL", 30))
    
    CLASSIFICATION_CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.6))
    PRIORITY_KEYWORDS = {
        "urgent": ["critical", "emergency", "asap", "urgent", "immediate"],
        "normal": ["important", "needed", "required", "scheduled"],
        "low": ["nice to have", "optional", "future", "backlog"]
    }
    
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_SECRETS_MANAGER_ENABLED = os.getenv("AWS_SECRETS_MANAGER_ENABLED", "False").lower() == "true"
    SECRET_NAME = os.getenv("SECRET_NAME", f"ai-workflow-automation/{os.getenv('ENV', 'dev')}/secrets")
    
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class DevelopmentConfig(EnvironmentConfig):
    ENV = "dev"
    DEBUG = True
    API_PORT = 8000
    MAX_WORKERS = 2
    MAX_FILE_SIZE_MB = 100
    LOG_LEVEL = "DEBUG"
    AWS_SECRETS_MANAGER_ENABLED = False
    S3_BUCKET = os.getenv("S3_BUCKET", "ai-workflow-automation-dev")
    S3_POLLING_INTERVAL = 10


class StagingConfig(EnvironmentConfig):
    ENV = "stage"
    DEBUG = False
    API_PORT = 8000
    MAX_WORKERS = 4
    MAX_FILE_SIZE_MB = 500
    LOG_LEVEL = "INFO"
    AWS_SECRETS_MANAGER_ENABLED = True
    S3_BUCKET = os.getenv("S3_BUCKET", "ai-workflow-automation-stage")
    S3_POLLING_INTERVAL = 20


class ProductionConfig(EnvironmentConfig):
    ENV = "prod"
    DEBUG = False
    API_PORT = 8000
    MAX_WORKERS = 8
    MAX_FILE_SIZE_MB = 1000
    LOG_LEVEL = "WARNING"
    AWS_SECRETS_MANAGER_ENABLED = True
    S3_BUCKET = os.getenv("S3_BUCKET", "ai-workflow-automation-prod")
    S3_POLLING_INTERVAL = 30


def get_config() -> EnvironmentConfig:
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
    if not config.AWS_SECRETS_MANAGER_ENABLED:
        logger.info("AWS Secrets Manager disabled")
        return
    
    logger.info(f"Retrieving secrets from AWS Secrets Manager: {config.SECRET_NAME}")
    secrets = get_secrets_from_aws(config.SECRET_NAME)
    
    for key, value in secrets.items():
        if hasattr(config, key):
            setattr(config, key, value)
            logger.debug(f"Applied secret: {key}")


config = get_config()

if config.AWS_SECRETS_MANAGER_ENABLED:
    apply_secrets_to_config(config)

logger.info(f"Configuration initialized for {config.ENV} environment")
