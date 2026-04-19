"""AI classification and summarization - decoupled from FastAPI"""
import logging
from typing import Dict, Any

from src.models.enums import PriorityLevel, SentimentType
from src.models.schemas import RecordClassification
from src.config import config

logger = logging.getLogger(__name__)

_POSITIVE_WORDS = {"great", "excellent", "thanks", "appreciate", "happy", "satisfied"}
_NEGATIVE_WORDS = {"terrible", "bad", "angry", "disappointed", "broken", "issue"}


def classify_record(record: Dict[str, Any]) -> RecordClassification:
    """
    Classify a record by priority, sentiment, and category.

    Uses keyword matching as a lightweight AI substitute.
    """
    description = str(record.get("description", "")).lower()

    # Priority classification
    priority = PriorityLevel.NORMAL
    for level, keywords in config.PRIORITY_KEYWORDS.items():
        if any(keyword in description for keyword in keywords):
            priority = PriorityLevel(level)
            break

    # Sentiment classification
    positive_count = sum(1 for w in _POSITIVE_WORDS if w in description)
    negative_count = sum(1 for w in _NEGATIVE_WORDS if w in description)

    if negative_count > positive_count:
        sentiment = SentimentType.NEGATIVE
        confidence = min(0.95, 0.6 + negative_count * 0.1)
    elif positive_count > negative_count:
        sentiment = SentimentType.POSITIVE
        confidence = min(0.95, 0.6 + positive_count * 0.1)
    else:
        sentiment = SentimentType.NEUTRAL
        confidence = 0.7

    # Category normalization
    category = record.get("category", "inquiry").lower()
    if category not in {"inquiry", "complaint", "feedback", "request", "issue"}:
        category = "inquiry"

    return RecordClassification(
        priority=priority,
        confidence=float(confidence),
        sentiment=sentiment,
        category=category,
    )


def generate_summary(record: Dict[str, Any], classification: RecordClassification) -> str:
    """Generate a short human-readable summary of the record."""
    description = str(record.get("description", "")).strip()
    summary_base = description.split(".")[0][:100]
    summary = f"[{classification.priority.upper()}] {summary_base}"

    if classification.sentiment == SentimentType.NEGATIVE:
        summary += " (⚠️ Negative feedback)"
    elif classification.sentiment == SentimentType.POSITIVE:
        summary += " (✓ Positive)"

    return summary
