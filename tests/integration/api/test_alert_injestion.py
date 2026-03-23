"""
DOCSTRING:
Integration tests for the alert ingestion API endpoint. These tests cover various scenarios of alert submission, including
- successful alert ingestion
- missing required fields
- invalid data formats
- authentication failures
The tests ensure that the API correctly validates incoming data, handles errors gracefully, and responds with appropriate status codes and messages.
"""

import pytest
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

# auto clean database table "client_alerts"
@pytest.fixture(autouse=True)
def clean():
    database = Database()
    try:
        database.clear_table("client_alerts")
    except Exception as e:
        print(f"Cleanup failed: {e}")
        database.conn.rollback()
    
    yield database
    # clean up after test
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

    def test_alert_ingestion_success(self, client, clean):
        # Test successful alert ingestion and DB persistence
        import json, time, uuid, hmac, hashlib, secrets

        # prepare client and register in DB
        client_id = str(uuid.uuid4())
        secret = secrets.token_hex(32)
        clean.register_client(client_id, "test-server", "linux", secret)

        payload = {
            "severity": "critical",
            "event_type": "file_modified",
            "details": {
                "file_path": "/tmp/testfile",
                "process_name": "testproc",
                "process_id": 1234,
                "description": "integration test"
            }
        }

        # deterministic JSON serialization for signing
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        timestamp = str(int(time.time()))
        message = f"{client_id}{timestamp}".encode('utf-8') + body.encode('utf-8')
        signature = hmac.new(secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
        signature_header = f"sha256={signature}"

        headers = {
            'X-Client-ID': client_id,
            'X-Timestamp': timestamp,
            'X-Signature': signature_header,
            'Content-Type': 'application/json'
        }

        # send request using the exact body used for signing
        response = client.post('/api/alerts/', data=body, headers=headers)
        assert response.status_code == 201
        data = response.get_json()
        assert data['status'] == 'received'
        assert 'alert_id' in data
        alert_id = data['alert_id']

        # verify alert persisted in the DB
        clean.cursor.execute(
            "SELECT alert_id, client_id, severity, event_type, acknowledged_at, acknowledged_by, created_at, details FROM client_alerts WHERE alert_id = %s",
            (alert_id,)
        )
        row = clean.cursor.fetchone()
        assert row is not None
        assert row[0] == alert_id
        assert row[2] == 'critical'
        assert row[3] == 'file_modified'
        assert row[4] is None
        assert row[5] is None

        # details were stored as JSON string - validate contents
        details_db = row[7]
        assert details_db is not None
        details_json = json.loads(details_db)
        assert details_json['process_name'] == 'testproc'
