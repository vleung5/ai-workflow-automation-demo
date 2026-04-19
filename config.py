"""Configuration for AI Workflow Automation Demo"""
import os

class Config:
    """Application configuration"""
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", 8000))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 4))
    QUEUE_MAX_SIZE = int(os.getenv("QUEUE_MAX_SIZE", 100))
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
    ALLOWED_EXTENSIONS = {"csv"}
    CLASSIFICATION_CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.6))
    PRIORITY_KEYWORDS = {
        "urgent": ["critical", "emergency", "asap", "urgent", "immediate"],
        "normal": ["important", "needed", "required", "scheduled"],
        "low": ["nice to have", "optional", "future", "backlog"]
    }

config = Config()
