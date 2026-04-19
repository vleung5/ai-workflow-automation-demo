"""Pytest fixtures shared across all tests"""

import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped asyncio event loop"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_csv_content() -> str:
    return (
        "description,category,priority\n"
        "Critical payment system failure,issue,urgent\n"
        "Feature request for dark mode,request,low\n"
        "Happy with the new update,feedback,normal\n"
        "Broken login page,issue,urgent\n"
        "Inquiry about billing,inquiry,normal\n"
    )


@pytest.fixture
def sample_record() -> dict:
    return {
        "description": "Customer complaints about product delivery being late",
        "category": "complaint",
        "priority": "high",
    }


@pytest.fixture
def invalid_record() -> dict:
    return {"description": "", "category": "unknown_cat", "priority": ""}
