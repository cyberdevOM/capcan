"Alert Endpoints Module - Handles API requests related to alerts."

from email import utils
from flask import Blueprint, request, jsonify
import datetime as dt
from typing import Dict, Any, List
from src.server.utils.timestamper import parse_timestamp, get_current_timestamp
import uuid
from werkzeug.exceptions import BadRequest
from ...utils.validators import (
    validate_timestamp,
    validate_signature,
    extract_security_headers,
    generate_ack_id,
)

from ...core.database import Database

# Create Flask Blueprint for alert endpoints
alert_bp = Blueprint("alerts", __name__, url_prefix="/alerts")

# ========== CONFIGURATION ==========

# valid severities — must match the ALERT_SEVERITY DB enum
VALID_SEVERITIES = ["critical", "high", "medium", "low", "info", "undefined"]

# Valid event types
VALID_EVENT_TYPES = [
    "file_modified",
    "file_created",
    "file_deleted",
    "process_started",
    "process_terminated",
    "network_connection",
    "login_failed",
    "login_success",
    "service_stopped",
    "honeypot_access",
    "custom"
]

# ========== HELPER FUNCTIONS ==========


def validate_alert_request(db: Database) -> tuple[bool, Dict[str, Any], int]:
    """
    Validate alert submission request with HMAC authentication.

    This ensures:
    - Security headers are present
    - Timestamp is valid
    - Signature matches
    - client is registered

    args: db: open Database connection (caller owns lifecycle)
          client_id: uuid from request headers

    returns: Tuple of (success, response_dict, status_code)
    """

    # Extract security headers
    headers_client_id, timestamp, signature = extract_security_headers(request.headers)

    if not headers_client_id:
        return (
            False,
            {
                "error": "Missing security headers.",
                "required": ["X-Client-ID", "X-Timestamp", "X-Signature"],
            },
            401,
        )

    # Validate timestamp
    valid_time, time_error = validate_timestamp(timestamp)
    if not valid_time:
        return False, {"error": f"Invalid timestamp: {time_error}"}, 401

    # Validate client is registered
    client_check = db.get_client_by_id(headers_client_id)
    if client_check is None:
        return (
            False,
            {
                "error": "Client not registered.",
                "hint": "Register at POST /api/clients/register first.",
            },
            404,
        )

    # Get client secret
    secret_key = db.get_client_secret(headers_client_id)
    if not secret_key:
        return False, {"error": "Client secret not found."}, 401

    # Validate HMAC signature
    valid_sig, sig_error = validate_signature(
        client_id=headers_client_id,
        timestamp=timestamp,
        body=request.get_data(),
        received_signature=signature,
        secret_key=secret_key,
    )

    if not valid_sig:
        return False, {"error": f"Invalid signature: {sig_error}"}, 401

    return True, {}, 200


def validate_alert_data(data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate alert data structure and values.

    Args:
        data: alert data dictionary from client

    Returns:
        Tuple of (is_valid, error_message)

    Example valid alert data:
    {
        "severity": "critical",
        "event_type": "file_modified",
        "timestamp": "2026-12-09T10:30:00Z",
        "details": {
            "file_path": "/etc/dev/trap.txt",
            "process_name": "malicious.exe",
            "process_id": 4321,
            "description": "Honey file was modified."
        }
    }
    """

    # Check required fields
    required_fields = ["severity", "event_type", "details"]
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    # Validate severity
    if data["severity"] not in VALID_SEVERITIES:
        return False, f"Invalid severity. Must be one of: {', '.join(VALID_SEVERITIES)}"

    # Validate event type
    if data["event_type"] not in VALID_EVENT_TYPES:
        return (
            False,
            f"Invalid event_type. Must be one of: {', '.join(VALID_EVENT_TYPES)}",
        )

    # Validate details is a dictionary
    if not isinstance(data["details"], dict):
        return False, "details must be an object/dictionary."

    # Validate timestamp if provided
    if "timestamp" in data:
        try:
            # Parse and convert to ISO 8601 with 'Z'
            parsed_time = parse_timestamp(data["timestamp"])
            data["timestamp"] = (
                parsed_time.replace(tzinfo=dt.timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
        except (ValueError, AttributeError):
            return False, "Invalid timestamp format. Use ISO 8601 format."

    return True, ""


def generate_alert_id() -> str:
    """
    Generate a unique alert ID.

    Format: UUID4 string
    Returns: alert_id string
    """
    return f"alert-{uuid.uuid4()}"


# ========== SUBMIT SINGLE ALERT ENDPOINT ==========
@alert_bp.route("/", methods=["POST"])
def submit_alert():
    """
    Submit a single security alert from a client.

    Endpoint: POST /api/alerts/

    Request Body:
    {
        "severity": string,
        "event_type": string,
        "timestamp": ISO 8601 string (optional),
        "details": {
            "file_path": string,
            "process_name": string,
            "process_id": integer,
            "process_hash": string,
            "command_line": string,
            "description": string
        }
    }

    response (success):
    {
        "status": string,
        "alert_id": string,
        "ack_id": string
        "received_at": ISO 8601 string
        "severity": string,
    }

    response (error):
    {
        "error": string,
    """

    # validate request authentication
    db = Database()
    try:
        valid, error_response, status_code = validate_alert_request(db)
        if not valid:
            return jsonify(error_response), status_code

        headers_client_id, _, _ = extract_security_headers(
            request.headers
        )

        # Parse JSON body
        try: 
            data = request.get_json()
        except BadRequest: 
            return jsonify({"error": "Malformed JSON payload."}), 400

        if not data:
            return jsonify({"error": "No alert data provided."}), 400

        # Validate alert data structure
        valid_data, data_error = validate_alert_data(data)
        if not valid_data:
            return jsonify({"error": f"Invalid alert data: {data_error}"}), 400

        # Generate alert metadata
        alert_id = generate_alert_id()
        # use timezone-aware datetime for DB insertion
        current_time = get_current_timestamp()

        # client timestamp if provided, else use server time
        alert_timestamp = data.get(
            "timestamp", current_time
        )  # Should be ISO 8601 with Z

        # create alert record
        # * Note: Please see database config in /core/config.py for the alert schema.

        db.store_alerts(
            client_id=headers_client_id,
            alert_id=alert_id,  # * Generated unique alert ID
            rule_id=data["event_type"],
            severity=data["severity"],
            score=0,  # ? Default score, update later with correlation engine
            event_type=data["event_type"],
            status="unresolved",  # Default status, update later with acknowledgment or resolution
            created_at=alert_timestamp,
            acknowledged_at=None,  # Default null, update when acknowledged
            acknowledged_by=None,  # Default null, update with admin ID when acknowledged
            details=data["details"],
            tags=None,
        )

        # Generate ack ID
        ack_id = generate_ack_id()
        return (
            jsonify(
                {
                    "status": "received",
                    "alert_id": alert_id,
                    "ack_id": ack_id,
                    "received_at": current_time,
                    "severity": data["severity"],
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": f"Error processing alert: {str(e)}"}), 500
    finally:
        db.close()


# ========== SUBMIT BULK ALERTS ENDPOINT ==========
@alert_bp.route("/bulk", methods=["POST"])
def submit_bulk_alerts():  # TODO: Change endpoint to integrate with database
    """
    Submit multiple alerts in a sprint(f"[DEBUG] Exception in submit_bulk_alerts: {e}", flush=True)ingle request.

    Endpoint: POST /api/alerts/bulk

    Use Cases:
    - Client was offline and accumulated alerts
    - Batch processing of log files
    - Reducing network overhead

    Request Body:
    {
        "alerts": [
            {
                "severity": string,
                "event_type": string,
                "timestamp": ISO 8601 string (optional),
                "details": {...}
            },
            {
                "severity": string,
                "event_type": string,
                "timestamp": ISO 8601 string (optional),
                "details": {...}
            }
        ]
    }

    Response (Success):
    {
        "status": "received",
        "alerts_processed": integer,
        "alert_ids": [string, string, ...],
        "failed": integer,
        "received_at": ISO 8601 string
    }
    """

    # extract client ID from headers
    headers_client_id, _, _ = extract_security_headers(request.headers)

    if not headers_client_id:
        return jsonify({"error": "Missing X-Client-ID header."}), 401

    db = Database()
    try:
        # validate request authentication
        valid, error_response, status_code = validate_alert_request(db)
        if not valid:
            return jsonify(error_response), status_code

        # parse bulk alert data
        try: 
            data = request.get_json()
        except BadRequest: 
            return jsonify({"error": "Malformed JSON payload."}), 400

        if not data or "alerts" not in data:
            return jsonify({"error": "No alerts array provided."}), 400

        if not isinstance(data["alerts"], list):
            return jsonify({"error": "alerts must be an array/list."}), 400

        # Process each alert
        current_time = get_current_timestamp()
        processed_alerts = []
        failed_alerts = []

        for idx, alert_data in enumerate(data["alerts"]):
            valid_data, data_error = validate_alert_data(alert_data)

            if not valid_data:
                failed_alerts.append({"index": idx, "error": data_error})
                continue

            # Generate alert metadata
            alert_id = generate_alert_id()
            alert_timestamp = alert_data.get("timestamp", current_time)
            db.store_alerts(
                client_id=headers_client_id,
                alert_id=alert_id,
                rule_id=alert_data["event_type"],
                severity=alert_data["severity"],
                score=0,
                event_type=alert_data["event_type"],
                status="unresolved",
                created_at=alert_timestamp,
                acknowledged_at=None,
                acknowledged_by=None,
                details=alert_data["details"],
                tags=None,
            )
            processed_alerts.append(alert_id)

        return (
            jsonify(
                {
                    "status": "received",
                    "alerts_processed": len(processed_alerts),
                    "alert_ids": processed_alerts,
                    "failed": len(failed_alerts),
                    "failed_details": (failed_alerts if failed_alerts else None),
                    "received_at": current_time,
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": f"Error processing bulk alerts: {str(e)}"}), 500
    finally:
        db.close()


# =========== Acknowledge alert endpoint ==========
@alert_bp.route("/acknowledge/<alert_id>", methods=["POST"])
def acknowledge_alert(alert_id):
    """
    Mark an alert as acknowledged.

    Endpoint: POST /api/alerts/acknowledge/<alert_id>

    Request body (optional):
    {
        "acknowledged_by": string
    }

    Response (success):
    {
        "status": "acknowledged",
        "alert_id": string,
        "acknowledged_at": ISO 8601 string,
        "acknowledged_by": string
    }
    """
    db = Database()
    try:
        data = request.get_json() or {}
        acknowledged_by = data.get("acknowledged_by", "server")
        current_time = dt.datetime.now(dt.timezone.utc).isoformat() + "Z"

        ok = db.acknowledge_alert(alert_id, acknowledged_by=acknowledged_by)
        if not ok:
            return jsonify({"error": "Alert not found.", "alert_id": alert_id}), 404

        return jsonify({
            "status": "acknowledged",
            "alert_id": alert_id,
            "acknowledged_at": current_time,
            "acknowledged_by": acknowledged_by,
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to acknowledge alert: {str(e)}"}), 500
    finally:
        db.close()


# ========== GET ALERT HISTORY ENDPOINT ==========
@alert_bp.route("/", methods=["GET"])
def get_alert_history():
    """
    Retrieve alert history with optional filters.

    Endpoint: GET /api/alerts/

    Query Parameters:
        ?client_id=uuid     Filter by client ID
        ?severity=string    Filter by severity level
        ?status=string      Filter by status (unresolved/acknowledged/resolved)
        ?event_type=string  Filter by event type
        ?limit=integer      Limit number of results (default 100)
    """
    db = Database()
    try:
        client_id_filter = request.args.get("client_id")
        severity_filter = request.args.get("severity")
        status_filter = request.args.get("status")
        event_type_filter = request.args.get("event_type")
        limit = request.args.get("limit", type=int, default=100)

        alerts = db.get_all_alerts(
            client_id=client_id_filter,
            severity=severity_filter,
            status=status_filter,
            event_type=event_type_filter,
            limit=limit,
        )

        # serialize datetimes
        def _serialize(a):
            for k in ("created_at", "acknowledged_at"):
                if a.get(k) and hasattr(a[k], "isoformat"):
                    a[k] = a[k].isoformat() + "Z"
            return a

        alerts = [_serialize(a) for a in alerts]
        return jsonify({"alerts": alerts, "returned": len(alerts)}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve alerts: {str(e)}"}), 500
    finally:
        db.close()


# ============ GET SINGLE ALERT ENDPOINT ============
@alert_bp.route("/<alert_id>", methods=["GET"])
def get_single_alert(alert_id):
    """
    Get details of a single alert by its ID.

    Endpoint: GET /api/alerts/<alert_id>

    Response (success):
    {
        "alert_id": string,
        "client_id": string,
        "severity": string,
        "event_type": string,
        "timestamp": ISO 8601 string,
        "acknowledged": boolean,
        "acknowledged_at": ISO 8601 string or null,
        "acknowledged_by": string or null,
        "details": {...}
    }
    """

    db = Database()
    try:
        row = None
        try:
            db.cursor.execute(
                "SELECT alert_id, client_id, rule_id, severity, score, event_type, "
                "status, acknowledged_at, acknowledged_by, created_at, details, tags "
                "FROM client_alerts WHERE alert_id = %s",
                (alert_id,),
            )
            row = db.cursor.fetchone()
        except Exception as db_err:
            print(f"[ERROR] get_single_alert DB: {db_err}")
            if db.conn:
                db.conn.rollback()

        if not row:
            return jsonify({"error": "Alert not found.", "alert_id": alert_id}), 404

        cols = ["alert_id", "client_id", "rule_id", "severity", "score", "event_type",
                "status", "acknowledged_at", "acknowledged_by", "created_at", "details", "tags"]
        alert = dict(zip(cols, row))
        for k in ("created_at", "acknowledged_at"):
            if alert.get(k) and hasattr(alert[k], "isoformat"):
                alert[k] = alert[k].isoformat() + "Z"
        return jsonify(alert), 200

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve alert: {str(e)}"}), 500
    finally:
        db.close()


# ============ RESOLVE ALERT ENDPOINT ============
@alert_bp.route("/resolve/<alert_id>", methods=["POST"])
def resolve_alert(alert_id):
    """
    Mark an alert as resolved.

    Endpoint: POST /api/alerts/resolve/<alert_id>
    """
    db = Database()
    try:
        ok = db.resolve_alert(alert_id)
        if not ok:
            return jsonify({"error": "Alert not found.", "alert_id": alert_id}), 404
        return jsonify({"status": "resolved", "alert_id": alert_id}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to resolve alert: {str(e)}"}), 500
    finally:
        db.close()
