"""Common helper utilities"""

import hashlib
import uuid
from datetime import datetime


def generate_job_id(prefix: str = "job") -> str:
    """Generate a unique job ID"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug"""
    return text.lower().replace(" ", "_").replace("/", "_").replace(".", "_")


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division returning default when denominator is zero"""
    if denominator == 0:
        return default
    return numerator / denominator


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to max_length characters"""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def calculate_success_rate(successful: int, total: int) -> float:
    """Calculate success rate as a percentage"""
    return safe_divide(successful * 100.0, total)


def now_iso() -> str:
    """Return current UTC datetime as ISO 8601 string"""
    return datetime.utcnow().isoformat() + "Z"


def sha256_digest(content: str) -> str:
    """Return SHA-256 hex digest of a string"""
    return hashlib.sha256(content.encode()).hexdigest()
