"""Tests for classification logic"""

from src.core.classifier import classify_record, generate_summary
from src.models.enums import PriorityLevel, SentimentType


def test_classify_urgent_priority():
    record = {"description": "CRITICAL server outage", "category": "issue", "priority": "urgent"}
    result = classify_record(record)
    assert result.priority == PriorityLevel.URGENT


def test_classify_negative_sentiment():
    record = {
        "description": "Terrible experience, broken system, angry about this",
        "category": "complaint",
        "priority": "normal",
    }
    result = classify_record(record)
    assert result.sentiment == SentimentType.NEGATIVE
    assert result.confidence > 0.6


def test_classify_positive_sentiment():
    record = {
        "description": "Great service, excellent support, very happy and satisfied",
        "category": "feedback",
        "priority": "normal",
    }
    result = classify_record(record)
    assert result.sentiment == SentimentType.POSITIVE


def test_generate_summary_urgent():
    record = {
        "description": "Critical issue needs immediate attention.",
        "category": "issue",
        "priority": "urgent",
    }
    from src.models.enums import PriorityLevel, SentimentType
    from src.models.schemas import RecordClassification

    classification = RecordClassification(
        priority=PriorityLevel.URGENT,
        confidence=0.9,
        sentiment=SentimentType.NEGATIVE,
        category="issue",
    )
    summary = generate_summary(record, classification)
    assert "URGENT" in summary
    assert "⚠️" in summary


def test_classify_unknown_category_defaults_to_inquiry():
    record = {
        "description": "Some description text here",
        "category": "xyz_unknown",
        "priority": "normal",
    }
    result = classify_record(record)
    assert result.category == "inquiry"
