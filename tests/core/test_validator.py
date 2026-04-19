"""Tests for data validation logic"""
import pytest
from src.core.validator import validate_record


def test_valid_record(sample_record):
    result = validate_record(sample_record)
    assert result.is_valid is True
    assert result.errors == []


def test_missing_required_fields():
    result = validate_record({})
    assert result.is_valid is False
    assert any("description" in e for e in result.errors)
    assert any("category" in e for e in result.errors)
    assert any("priority" in e for e in result.errors)


def test_description_too_short():
    record = {"description": "Hi", "category": "inquiry", "priority": "normal"}
    result = validate_record(record)
    assert result.is_valid is False
    assert any("short" in e.lower() for e in result.errors)


def test_description_too_long():
    record = {
        "description": "x" * 600,
        "category": "inquiry",
        "priority": "normal",
    }
    result = validate_record(record)
    assert result.is_valid is True
    assert any("long" in w.lower() for w in result.warnings)


def test_unknown_category_warning():
    record = {
        "description": "This is a valid description",
        "category": "mystery_category",
        "priority": "normal",
    }
    result = validate_record(record)
    assert any("unknown category" in w.lower() for w in result.warnings)
