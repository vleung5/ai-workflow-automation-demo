"""Data validation rules - decoupled from FastAPI"""
import logging
from typing import Dict, Any, List

from src.models.schemas import ValidationResult

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["description", "category", "priority"]
VALID_CATEGORIES = {"inquiry", "complaint", "feedback", "request", "issue"}
MIN_DESCRIPTION_LENGTH = 5
MAX_DESCRIPTION_LENGTH = 500


def validate_record(record: Dict[str, Any], record_id: int = 0) -> ValidationResult:
    """
    Validate a single CSV record.

    Args:
        record: Dictionary representing one CSV row.
        record_id: Row index for logging purposes.

    Returns:
        ValidationResult with is_valid flag, errors, and warnings.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in record or not str(record[field]).strip():
            errors.append(f"Missing required field: {field}")

    # Validate description length
    desc = str(record.get("description", "")).strip()
    if desc and len(desc) < MIN_DESCRIPTION_LENGTH:
        errors.append(
            f"Description too short (minimum {MIN_DESCRIPTION_LENGTH} characters)"
        )
    elif len(desc) > MAX_DESCRIPTION_LENGTH:
        warnings.append(f"Description is very long (>{MAX_DESCRIPTION_LENGTH} chars)")

    # Validate category
    category = record.get("category", "").lower()
    if category and category not in VALID_CATEGORIES:
        warnings.append(f"Unknown category: {record.get('category')}")

    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
