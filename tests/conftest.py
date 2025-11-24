"""
Pytest configuration and shared fixtures
"""

import pytest
import os

@pytest.fixture(scope="session")
def api_base_url():
    """Base URL for API endpoints"""
    return os.getenv("API_BASE_URL", "http://localhost:8000")

@pytest.fixture(scope="session")
def test_timeout():
    """Maximum time to wait for processing"""
    return int(os.getenv("TEST_TIMEOUT", 300))

@pytest.fixture
def test_user_id():
    """Test user ID for chat sessions"""
    return "test_user_e2e"

