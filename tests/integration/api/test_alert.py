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
import uuid, secrets, hmac, hashlib, json
from src.server.app import create_app
from src.server.core.database import Database
from src.server.utils.timestamper import parse_timestamp, get_current_timestamp


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
def db():
    """Create a db connection for each test"""
    db = Database()
    yield db
    # Cleanup after test
    db.close()


@pytest.fixture(autouse=True)  # create a test client in the db for authentication tests
def test_client(db):
    """Create a test client in the db for authentication tests"""
    client_id = str(uuid.uuid4())
    hostname = "test-host"
    platform = "linux"
    secret_key = secrets.token_hex(32)
    notes = "Test client for alert ingestion tests"

    db.register_client(client_id, hostname, platform, secret_key, notes)

    yield {
        "client_id": client_id,
        "secret_key": secret_key,
    }  # provide client details to tests

    db.delete_client(client_id)  # clean up test client after tests


@pytest.fixture(autouse=True)  # auto clean db table "client_alerts"
def clean():
    db = Database()
    try:
        db.clear_table("client_alerts")
    except Exception as e:
        print(f"Cleanup failed: {e}")
        db.conn.rollback()

    yield  # wait for tests to run and then clean up after tests

    try:
        db.clear_table("client_alerts")
    except Exception as e:
        print(f"Cleanup failed: {e}")
        db.conn.rollback()
    finally:
        db.close()


# Testing alert ingestion
class TestAlertIngestion:
    # Tests for POST /api/alerts/

    def test_success(self, client, test_client, db):
        timestamp = get_current_timestamp()
        payload = {
            "event_type": "custom",
            "severity": "high",
            "details": {"description": "This is a test alert for integration testing."},
        }
        # Use Flask's test client to get the exact bytes sent in the request
        json_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
        message = f"{test_client['client_id']}{timestamp}".encode("utf-8") + json_bytes
        signature = hmac.new(
            key=test_client["secret_key"].encode("utf-8"),
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest()
        headers = {
            "X-Client-ID": test_client["client_id"],
            "X-Timestamp": timestamp,
            "X-Signature": f"sha256={signature}",
        }

        response = client.post(
            "/api/alerts/",
            headers=headers,
            data=json_bytes,
            content_type="application/json",
        )
        print("RESPONSE BODY:", response.get_data(as_text=True))
        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "received"
        assert "alert_id" in data
        assert "ack_id" in data
        client_id = test_client["client_id"]

        alerts = db.get_alerts_by_client(client_id, status="unresolved", limit=1)
        alert = alerts[0] if alerts else None
        print("INGESTED ALERT:", alert)
        assert alert is not None

        if alert:
            columns = [
                desc[0] for desc in db.cursor.description
            ]  # Get column names from cursor description
            alert_dict = dict(zip(columns, alert))
            assert alert_dict["client_id"] == client_id
            assert alert_dict["event_type"] == payload["event_type"]
            assert alert_dict["severity"] == payload["severity"]
            assert json.loads(alert_dict["details"]) == payload["details"]
            assert alert_dict["status"] == "unresolved"

    def test_missing_fields(self, client, test_client):
        #TODO - test missing event_type, severity, details

        timestamp = get_current_timestamp()
        payload = {
            "severity": "high",
            "details": {"description": "This is a test alert with missing event_type."},
        }

        json_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
        message = f"{test_client['client_id']}{timestamp}".encode("utf-8") + json_bytes
        signature = hmac.new(
            key=test_client["secret_key"].encode("utf-8"),
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest()
        headers = {
            "X-Client-ID": test_client["client_id"],
            "X-Timestamp": timestamp,
            "X-Signature": f"sha256={signature}",
        }

        response = client.post(
            "/api/alerts/",
            headers=headers,
            data=json_bytes,
            content_type="application/json",
        )
        print("RESPONSE BODY:", response.get_data(as_text=True))
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "Missing required field: event_type" in data["error"]

    def test_invalid_data(self, client, test_client):
        #TODO - test invalid severity value, invalid details format

        timestamp = get_current_timestamp()
        payload = {
            "event_type": "custom",
            "severity": "test_severity",  # invalid severity
            "details": {"description": "This is a test alert with invalid severity."},
        }

        json_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
        message = f"{test_client['client_id']}{timestamp}".encode("utf-8") + json_bytes
        signature = hmac.new(
            key=test_client["secret_key"].encode("utf-8"),
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest()
        headers = {
            "X-Client-ID": test_client["client_id"],
            "X-Timestamp": timestamp,
            "X-Signature": f"sha256={signature}",
        }

        response = client.post(
            "/api/alerts/",
            headers=headers,
            data=json_bytes,
            content_type="application/json",
        )
        print("RESPONSE BODY:", response.get_data(as_text=True))
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "Invalid alert data" in data["error"]

    def test_auth_failure(self, client, test_client):
        #TODO - test invalid signature, missing signature, invalid client ID

        timestamp = get_current_timestamp()
        payload = {
            "event_type": "custom",
            "severity": "high",
            "details": {"description": "This is a test alert for authentication failure."},
        }

        json_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        headers = {
            "X-Client-ID": test_client["client_id"],
            "X-Timestamp": timestamp,
            "X-Signature": "sha256=invalidsignature",  # invalid signature
        }
        response = client.post(
            "/api/alerts/",
            headers=headers,
            data=json_bytes,
            content_type="application/json",
        )
        print("RESPONSE BODY:", response.get_data(as_text=True))
        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "Invalid signature" in data["error"]

    def test_malformed_payload(self, client, test_client):
        # TODO: create test to test malformed json payload
        # copilot fill in
        pass
    
    def test_extra_fields(self, client, test_client):
        # TODO: create test to test additional feilds in payload, headers & post request
        # copilot fill in
        pass
    
    def test_single_submit_rate_limit(self, client, test_client):
        # TODO: create rate limit test for single submit
        # copilot fill in
        pass
    
class TestAlertBulk:
    def test_success(self, client, test_client, db):
        # Submit multiple valid alerts
        timestamp = get_current_timestamp()
        alerts = [
            {
                "event_type": "custom",
                "severity": "high",
                "details": {"description": f"Bulk alert {i}"},
                "timestamp": timestamp
            }
            for i in range(3)
        ]
        payload = {"alerts": alerts}
        json_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        message = f"{test_client['client_id']}{timestamp}".encode("utf-8") + json_bytes
        signature = hmac.new(
            key=test_client["secret_key"].encode("utf-8"),
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest()
        headers = {
            "X-Client-ID": test_client["client_id"],
            "X-Timestamp": timestamp,
            "X-Signature": f"sha256={signature}",
        }
        response = client.post(
            "/api/alerts/bulk",
            headers=headers,
            data=json_bytes,
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["alerts_processed"] == 3
        assert len(data["alert_ids"]) == 3
        assert data["failed"] == 0
        db

    
    def test_missing_fields(self, client, test_client):
        # One alert missing severity, one valid
        timestamp = get_current_timestamp()
        alerts = [
            {
                "event_type": "custom",
                "details": {"description": "Missing severity"},
                "timestamp": timestamp
            },
            {
                "event_type": "custom",
                "severity": "high",
                "details": {"description": "Valid alert"},
                "timestamp": timestamp
            }
        ]
        payload = {"alerts": alerts}
        json_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        message = f"{test_client['client_id']}{timestamp}".encode("utf-8") + json_bytes
        signature = hmac.new(
            key=test_client["secret_key"].encode("utf-8"),
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest()
        headers = {
            "X-Client-ID": test_client["client_id"],
            "X-Timestamp": timestamp,
            "X-Signature": f"sha256={signature}",
        }
        response = client.post(
            "/api/alerts/bulk",
            headers=headers,
            data=json_bytes,
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["alerts_processed"] == 1
        assert data["failed"] == 1
        assert data["failed_details"] is not None
        assert "Missing required field: severity" in data["failed_details"][0]["error"]

    
    def test_extra_fields(self, client, test_client):
        # Alert with extra field
        timestamp = get_current_timestamp()
        alerts = [
            {
                "event_type": "custom",
                "severity": "high",
                "details": {"description": "Extra field test"},
                "timestamp": timestamp,
                "extra_field": "should be ignored"
            }
        ]
        payload = {"alerts": alerts}
        json_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        message = f"{test_client['client_id']}{timestamp}".encode("utf-8") + json_bytes
        signature = hmac.new(
            key=test_client["secret_key"].encode("utf-8"),
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest()
        headers = {
            "X-Client-ID": test_client["client_id"],
            "X-Timestamp": timestamp,
            "X-Signature": f"sha256={signature}",
        }
        response = client.post(
            "/api/alerts/bulk",
            headers=headers,
            data=json_bytes,
            content_type="application/json",
        )
        # Accept 201 if extra fields are ignored, or 400 if strict
        assert response.status_code in (201, 400)

    
    def test_invalid_data(self, client, test_client):
        # Alert with invalid severity
        timestamp = get_current_timestamp()
        alerts = [
            {
                "event_type": "custom",
                "severity": "not_a_severity",
                "details": {"description": "Invalid severity"},
                "timestamp": timestamp
            }
        ]
        payload = {"alerts": alerts}
        json_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        message = f"{test_client['client_id']}{timestamp}".encode("utf-8") + json_bytes
        signature = hmac.new(
            key=test_client["secret_key"].encode("utf-8"),
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest()
        headers = {
            "X-Client-ID": test_client["client_id"],
            "X-Timestamp": timestamp,
            "X-Signature": f"sha256={signature}",
        }
        response = client.post(
            "/api/alerts/bulk",
            headers=headers,
            data=json_bytes,
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["alerts_processed"] == 0
        assert data["failed"] == 1
        assert data["failed_details"] is not None
        assert "Invalid severity" in data["failed_details"][0]["error"]

    
    def test_auth_faliure(self, client, test_client):
        # Missing signature
        timestamp = get_current_timestamp()
        alerts = [
            {
                "event_type": "custom",
                "severity": "high",
                "details": {"description": "Auth fail test"},
                "timestamp": timestamp
            }
        ]
        payload = {"alerts": alerts}
        json_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        headers = {
            "X-Client-ID": test_client["client_id"],
            "X-Timestamp": timestamp,
            # Missing X-Signature
        }
        response = client.post(
            "/api/alerts/bulk",
            headers=headers,
            data=json_bytes,
            content_type="application/json",
        )
        assert response.status_code in (401, 404)

    
    def test_malformed_payload(self, client, test_client):
        # Malformed JSON
        timestamp = get_current_timestamp()
        malformed_json = '{"alerts": [{"event_type": "custom", "severity": "high", "details": "missing end brace"}'
        message = f"{test_client['client_id']}{timestamp}".encode("utf-8") + malformed_json.encode("utf-8")
        signature = hmac.new(
            key=test_client["secret_key"].encode("utf-8"),
            msg=message,
            digestmod=hashlib.sha256,
        ).hexdigest()
        headers = {
            "X-Client-ID": test_client["client_id"],
            "X-Timestamp": timestamp,
            "X-Signature": f"sha256={signature}",
        }
        response = client.post(
            "/api/alerts/bulk",
            headers=headers,
            data=malformed_json,
            content_type="application/json",
        )
        assert response.status_code == 400
    