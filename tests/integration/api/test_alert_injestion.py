"""
DOCSTRING:
Integration tests for the alert ingestion API endpoint. These tests cover various scenarios of alert submission, including
- successful alert ingestion
- missing required fields
- invalid data formats
- authentication failures
The tests ensure that the API correctly validates incoming data, handles errors gracefully, and responds with appropriate status codes and messages.
"""

import pytest, uuid, secrets
from src.server.app import create_app
from src.server.core.database import Database
import datetime as dt

@pytest.fixture
def app():
    # Create Flask app in testing mode
    app = create_app(testing=True)
    return app

@pytest.fixture
def client(app):
    # Flask test client
    return app.test_client()

@pytest.fixture(scope="function")
def database():
    """Create a database connection for each test"""
    database = Database()
    yield database
    # Cleanup after test
    database.close()

@pytest.fixture(autouse=True) # create a test client in the database for authentication tests
def test_client(database):
    """Create a test client in the database for authentication tests"""
    client_id = str(uuid.uuid4())
    hostname = "test-host"
    platform = "linux"
    secret_key = secrets.token_hex(32)
    notes = "Test client for alert ingestion tests"

    database.register_client(client_id, hostname, platform, secret_key, notes)

    yield {
        "client_id": client_id,
        "secret_key": secret_key
    } # provide client details to tests

    database.delete_client(client_id) # clean up test client after tests

@pytest.fixture(autouse=True) # auto clean database table "client_alerts"
def clean():
    database = Database()
    try:
        database.clear_table("client_alerts")
    except Exception as e:
        print(f"Cleanup failed: {e}")
        database.conn.rollback()
    
    yield # wait for tests to run and then clean up after tests
    
    try:
        database.clear_table("client_alerts")
    except Exception as e:
        print(f"Cleanup failed: {e}")
        database.conn.rollback()
    finally:
        database.close()

# Testing alert ingestion
class TestAlertIngestion:
    # Tests for POST /api/alerts/

    #! Note: not functional yet due to 401 error
    
    def test_alert_ingestion_success(self, client, test_client, database):
        import hmac, hashlib, json
        timestamp = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
        payload = {
            "event_type": "test_event",
            "severity": "high",
            "details": {"description": "This is a test alert for integration testing."}
        }
        body = json.dumps(payload).encode('utf-8')
        message = f"{test_client['client_id']}{timestamp}".encode('utf-8') + body
        signature = hmac.new(
            key=test_client["secret_key"].encode('utf-8'),
            msg=message,
            digestmod=hashlib.sha256
        ).hexdigest()
        headers = {
            "X-Client-ID": test_client["client_id"],
            "X-Timestamp": timestamp,
            "X-Signature": f"sha256={signature}"
        }

        response = client.post(
            '/api/alerts/',
            headers=headers,
            json=payload,
            content_type='application/json'
        )
        print('RESPONSE BODY:', response.get_data(as_text=True))
        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "received"
        assert "alert_id" in data
        assert "ack_id" in data
        client_id = test_client["client_id"]

        alerts = database.get_alerts_by_client(client_id, limit=1)

    def test_alert_ingestion_missing_fields(self, client, clean):
        pass

    def test_alert_ingestion_invalid_data(self, client, clean):
        pass

    def test_alert_ingestion_auth_failure(self, client, clean):
        pass

    