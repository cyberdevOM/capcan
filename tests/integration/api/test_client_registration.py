"""
Integration tests for Client Registration API endpoint
Tests the POST /api/clients/register endpoint
"""

import pytest
from src.server.app import create_app
from src.server.core.database import Database


@pytest.fixture
def app():
    # Create Flask app in testing mode
    app = create_app(testing=True)
    return app

@pytest.fixture
def client(app):
    # Flask test client
    return app.test_client()

# auto clean database table "registered _clients" before and after a test to ensure data validity
@pytest.fixture(autouse=True)
def clean():
    database = Database()
    try:
        database.clear_table("registered_clients")
    except Exception as e:
        print(f"Cleanup failed: {e}")
        database.conn.rollback()
 
    yield database
    # clean up after test
    try:
        database.clear_table("registered_clients")
    except Exception as e:
        print(f"Cleanup failed: {e}")
        database.conn.rollback()
    finally:
        database.close()

# Testing client registration
class TestClientRegistration:
    # Tests for POST /api/clients/register endpoint
    
    def test_register_client_success(self, client):
        # Test successful client registration
        payload = {
            "hostname": "test-server-01",
            "platform": "linux"
        }
        response = client.post(
            '/api/clients/register',
            json=payload,
            content_type='application/json'
        )
        
        assert response.status_code == 201 #! Error returned 200 not 201
        data = response.get_json()
        assert "client_id" in data
        assert "secret_key" in data
        assert data["message"] == "Client registered successfully"
    
    def test_register_client_missing_hostname(self, client):
        # Test registration fails without hostname
        payload = {"platform": "linux"}
        response = client.post(
            '/api/clients/register',
            json=payload
        )
        
        assert response.status_code == 400
        assert "Missing required field" in response.get_json()["error"]
    
    def test_register_client_missing_platform(self, client):
        # Test registration fails without platform
        payload = {"hostname": "test-server"}
        response = client.post(
            '/api/clients/register',
            json=payload
        )
        
        assert response.status_code == 400
        assert "Missing required field" in response.get_json()["error"]
    
    def test_register_client_invalid_platform(self, client):
        # Test registration fails with invalid platform
        payload = {
            "hostname": "test-server",
            "platform": "bsd"  # Invalid, must be linux/windows/macos
        }
        response = client.post(
            '/api/clients/register',
            json=payload
        )
        
        assert response.status_code == 400
        assert "Invalid platform" in response.get_json()["error"]
    
    def test_register_client_no_json(self, client):
        # Test registration fails without JSON body
        response = client.post(
            '/api/clients/register',
            content_type='application/json'
        )
        
        assert response.status_code == 400
        assert "No json data provided" in response.get_json()["error"]
    
    def test_register_client_returns_unique_ids(self, client):
        # Test that multiple registrations get unique client IDs
        payload1 = {"hostname": "server-01", "platform": "linux"}
        payload2 = {"hostname": "server-02", "platform": "windows"}
        
        response1 = client.post('/api/clients/register', json=payload1)
        response2 = client.post('/api/clients/register', json=payload2)
        
        data1 = response1.get_json()
        data2 = response2.get_json()
        
        assert data1["client_id"] != data2["client_id"]
        assert data1["secret_key"] != data2["secret_key"]