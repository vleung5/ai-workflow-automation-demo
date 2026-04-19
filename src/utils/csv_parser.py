"""CSV parsing utilities"""

import csv
import io
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def parse_csv_content(content: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse CSV string content into a list of row dicts.

    Returns:
        Tuple of (rows, errors) where errors is a list of parsing issues.
    """
    errors: List[str] = []
    rows: List[Dict[str, Any]] = []

    if not content or not content.strip():
        errors.append("CSV content is empty")
        return rows, errors

    try:
        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            errors.append("CSV has no header row")
            return rows, errors

        for idx, row in enumerate(reader, start=1):
            # Strip whitespace from values
            cleaned = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
            rows.append(cleaned)

        logger.debug(f"Parsed {len(rows)} rows from CSV")
    except csv.Error as e:
        errors.append(f"CSV parse error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error parsing CSV: {str(e)}")
        errors.append(f"Unexpected error: {str(e)}")

    return rows, errors


def validate_csv_headers(rows: List[Dict[str, Any]], required_headers: List[str]) -> List[str]:
    """
    Validate that required headers are present.

    Returns a list of missing header names.
    """
    if not rows:
        return required_headers[:]
    actual_headers = set(rows[0].keys())
    return [h for h in required_headers if h not in actual_headers]


def rows_to_csv(rows: List[Dict[str, Any]]) -> str:
    """Convert a list of dicts back to CSV string"""
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
