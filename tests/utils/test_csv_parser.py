"""Tests for CSV parsing utilities"""
import pytest
from src.utils.csv_parser import parse_csv_content, validate_csv_headers, rows_to_csv


def test_parse_valid_csv():
    content = "name,value\nalice,1\nbob,2\n"
    rows, errors = parse_csv_content(content)
    assert len(rows) == 2
    assert errors == []
    assert rows[0]["name"] == "alice"


def test_parse_empty_csv():
    rows, errors = parse_csv_content("")
    assert rows == []
    assert len(errors) > 0


def test_validate_csv_headers_present():
    rows = [{"name": "alice", "value": "1"}]
    missing = validate_csv_headers(rows, ["name", "value"])
    assert missing == []


def test_validate_csv_headers_missing():
    rows = [{"name": "alice"}]
    missing = validate_csv_headers(rows, ["name", "value"])
    assert "value" in missing


def test_rows_to_csv_roundtrip():
    rows = [{"col1": "a", "col2": "b"}, {"col1": "c", "col2": "d"}]
    csv_str = rows_to_csv(rows)
    parsed, errors = parse_csv_content(csv_str)
    assert errors == []
    assert len(parsed) == 2
    assert parsed[0]["col1"] == "a"
