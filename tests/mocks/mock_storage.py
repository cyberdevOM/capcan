"""
Mock storage for tests.

This module manages mock data used throughout the test suite.
It provides functions to reset mocks between tests for isolation.
"""

# Global mock storage dictionaries
MOCK_CLIENTS = {}
MOCK_ALERTS = {}
MOCK_TELEMETRY = {}
MOCK_EVENTS = {}
MOCK_CHANGES = {}
MOCK_CONFIGS = {}
MOCK_WEB_USERS = {}
MOCK_CLIENT_SECRETS = {}


def reset_all_mocks():
    """Reset all mock storage to empty state.
    
    Called before each test to ensure test isolation.
    """
    global MOCK_CLIENTS, MOCK_ALERTS, MOCK_TELEMETRY, MOCK_EVENTS
    global MOCK_CHANGES, MOCK_CONFIGS, MOCK_WEB_USERS, MOCK_CLIENT_SECRETS
    
    MOCK_CLIENTS.clear()
    MOCK_ALERTS.clear()
    MOCK_TELEMETRY.clear()
    MOCK_EVENTS.clear()
    MOCK_CHANGES.clear()
    MOCK_CONFIGS.clear()
    MOCK_WEB_USERS.clear()
    MOCK_CLIENT_SECRETS.clear()


def reset_mock(mock_name):
    """Reset a specific mock by name.
    
    Args:
        mock_name (str): Name of the mock to reset ('clients', 'alerts', etc.)
    """
    mocks = {
        'clients': MOCK_CLIENTS,
        'alerts': MOCK_ALERTS,
        'telemetry': MOCK_TELEMETRY,
        'events': MOCK_EVENTS,
        'changes': MOCK_CHANGES,
        'configs': MOCK_CONFIGS,
        'web_users': MOCK_WEB_USERS,
        'client_secrets': MOCK_CLIENT_SECRETS
    }
    
    if mock_name in mocks:
        mocks[mock_name].clear()


def get_mock_storage(storage_type):
    """Get a reference to specific mock storage.
    
    Args:
        storage_type (str): Type of storage to retrieve
        
    Returns:
        dict: The requested mock storage dictionary
    """
    mocks = {
        'clients': MOCK_CLIENTS,
        'alerts': MOCK_ALERTS,
        'telemetry': MOCK_TELEMETRY,
        'events': MOCK_EVENTS,
        'changes': MOCK_CHANGES,
        'configs': MOCK_CONFIGS,
        'web_users': MOCK_WEB_USERS,
        'client_secrets': MOCK_CLIENT_SECRETS
    }
    
    return mocks.get(storage_type, {})
