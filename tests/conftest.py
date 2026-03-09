# Written by Claude Sonnet 4.5
# filepath: /home/dev/Desktop/capcan/tests/conftest.py

"""
Global pytest configuration and fixtures for Capcan tests.

This file provides:
- Mock data reset between tests
- Common test utilities
- Global test configuration
"""

import pytest
from unittest.mock import MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import mock storage reset functions
from tests.mocks.mock_storage import reset_all_mocks


@pytest.fixture(autouse=True)
def reset_mocks():
    """
    Automatically reset all mock data before each test.

    This ensures test isolation - no test affects another.
    """
    reset_all_mocks()
    yield


@pytest.fixture(scope="session")
def mock_config():
    """
    Mock configuration for tests.

    Returns a dictionary with test configuration values.
    """
    return {
        "server_url": "http://localhost:5000",
        "api_prefix": "/api",
        "max_timestamp_age": 300,
        "valid_algorithms": ["sha256"]
    }


@pytest.fixture
def sample_client_data():
    """
    Sample client data for testing.

    Returns a dictionary representing a typical client registration.
    """
    return {
        "hostname": "test-server-01",
        "platform": "linux",
        "ip_address": "192.168.1.100",
        "version": "0.03"
    }


@pytest.fixture
def sample_telemetry_data():
    """
    Sample telemetry data for testing.

    Returns a dictionary with typical system metrics.
    """
    return {
        "cpu_percent": 45.2,
        "memory_percent": 62.8,
        "disk_usage": 78.5,
        "network_sent_bytes": 1024000,
        "network_recv_bytes": 2048000,
        "process_count": 156,
        "load_average": [1.5, 1.3, 1.1]
    }


@pytest.fixture
def sample_alert_data():
    """
    Sample alert data for testing.

    Returns a dictionary representing a security alert.
    """
    return {
        "severity": "critical",
        "event_type": "file_modified",
        "details": {
            "file_path": "/var/honeyfiles/trap.txt",
            "process_name": "suspicious.exe",
            "process_id": 1234,
            "description": "Honeyfile was modified by unknown process"
        }
    }


# Global test configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "security: marks tests as security-critical")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Mark e2e tests
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)

        # Mark security tests
        if "security" in str(item.fspath) or "api_security" in str(item.fspath):
            item.add_marker(pytest.mark.security)