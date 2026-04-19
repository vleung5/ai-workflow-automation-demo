"""
Configuration for AI Workflow Automation Demo with environment support
"""
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
    
    # Async Processing
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 4))
    QUEUE_MAX_SIZE = int(os.getenv("QUEUE_MAX_SIZE", 100))
    
    # File Upload
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
    ALLOWED_EXTENSIONS = {"csv"}
    
    # AI Configuration
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
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class DevelopmentConfig(EnvironmentConfig):
    """Development environment configuration"""
    ENV = "dev"
    DEBUG = True
    API_PORT = 8000
    MAX_WORKERS = 2
    MAX_FILE_SIZE_MB = 100
    LOG_LEVEL = "DEBUG"
    AWS_SECRETS_MANAGER_ENABLED = False


class StagingConfig(EnvironmentConfig):
    """Staging environment configuration"""
    ENV = "stage"
    DEBUG = False
    API_PORT = 8000
    MAX_WORKERS = 4
    MAX_FILE_SIZE_MB = 500
    LOG_LEVEL = "INFO"
    AWS_SECRETS_MANAGER_ENABLED = True


class ProductionConfig(EnvironmentConfig):
    """Production environment configuration"""
    ENV = "prod"
    DEBUG = False
    API_PORT = 8000
    MAX_WORKERS = 8
    MAX_FILE_SIZE_MB = 1000
    LOG_LEVEL = "WARNING"
    AWS_SECRETS_MANAGER_ENABLED = True


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
    """
    Retrieve secrets from AWS Secrets Manager
    
    Args:
        secret_name: Name of the secret in AWS Secrets Manager
        
    Returns:
        Dictionary of secrets
    """
    try:
        import boto3
        import base64
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
            logger.warning("Secret retrieved but no SecretString found")
            return {}
            
    except ImportError:
        logger.warning("boto3 not installed, skipping AWS Secrets Manager")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error retrieving secrets: {str(e)}")
        return {}


def apply_secrets_to_config(config: EnvironmentConfig) -> None:
    """
    Apply secrets from AWS to configuration
    
    Args:
        config: Configuration object to update
    """
    if not config.AWS_SECRETS_MANAGER_ENABLED:
        logger.info("AWS Secrets Manager disabled")
        return
    
    logger.info(f"Retrieving secrets from AWS Secrets Manager: {config.SECRET_NAME}")
    secrets = get_secrets_from_aws(config.SECRET_NAME)
    
    # Apply secrets to config
    for key, value in secrets.items():
        if hasattr(config, key):
            setattr(config, key, value)
            logger.debug(f"Applied secret: {key}")
        else:
            logger.warning(f"Secret key not found in config: {key}")


# Initialize config
config = get_config()

# Apply AWS secrets if enabled
if config.AWS_SECRETS_MANAGER_ENABLED:
    apply_secrets_to_config(config)

logger.info(f"Configuration initialized for {config.ENV} environment")
logger.debug(f"Debug mode: {config.DEBUG}")
logger.debug(f"API Port: {config.API_PORT}")
logger.debug(f"Max Workers: {config.MAX_WORKERS}")
