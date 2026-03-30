"Alert Endpoints Module - Handles API requests related to alerts."

from email import utils
from flask import Blueprint, request, jsonify
import datetime as dt
from typing import Dict, Any, List
from src.server.utils.timestamper import parse_timestamp, get_current_timestamp
import uuid

from ..utils.validators import (
    validate_timestamp,
    validate_signature,
    extract_security_headers,
    generate_ack_id,
)

from ..core.database import Database

# Create Flask Blueprint for alert endpoints
alert_bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")

# ========== CONFIGURATION ==========

# valid severities and levels (orderd by importance)
VALID_SEVERITIES = ["info", "warning", "high", "critical"]

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
    "custom"
]

database = Database()  # Initialize database connection

# ========== HELPER FUNCTIONS ==========


def validate_alert_request() -> tuple[bool, Dict[str, Any], int]:
    """
    Validate alert submission request with HMAC authentication.

    This ensures:
    - Security headers are present
    - Timestamp is valid
    - Signature matches
    - client is registered

    args: client_id: uuid from request headers

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

    # Validate client ID matches

    if database.get_client_by_id(headers_client_id) is None:
        return (
            False,
            {
                "error": "Client not registered.",
                "hint": "Register at POST /api/clients/register first.",
            },
            404,
        )

    # Get client secret
    secret_key = database.get_client_secret(headers_client_id)
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
    valid, error_response, status_code = validate_alert_request()
    if not valid:
        return jsonify(error_response), status_code

    headers_client_id, _, _ = extract_security_headers(
        request.headers
    )

    try:
        # Parse JSON body
        data = request.get_json()

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

        database.store_alerts(
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


# ========== SUBMIT BULK ALERTS ENDPOINT ==========
@alert_bp.route("/bulk", methods=["POST"])
def submit_bulk_alerts():  # TODO: Change endpoint to integrate with database
    """
    Submit multiple alerts in a single request.

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

    # validate request authentication
    valid, error_response, status_code = validate_alert_request(headers_client_id)
    if not valid:
        return jsonify(error_response), status_code

    try:
        # parse bulk alert data
        data = request.get_json()

        if not data or "alerts" not in data:
            return jsonify({"error": "No alerts array provided."}), 400

        if not isinstance(data["alerts"], list):
            return jsonify({"error": "alerts must be an array/list."}), 400

        # Process each alert

        current_time = dt.datetime.now(dt.timezone.utc).isoformat() + "Z"
        processed_alerts = []
        failed_alerts = []

        for idx, alert_data in enumerate(data["alerts"]):  #
            # vaidate alert data stjructure
            valid_data, data_error = validate_alert_data(alert_data)

            if (
                not valid_data
            ):  # if not valid alert append index number and error to failed_alerts array and continue
                failed_alerts.append({"index": idx, "error": data_error})
                continue

            # Generate alert metadata
            alert_id = generate_alert_id()
            alert_timestamp = alert_data.get(
                "timestamp", current_time
            )  # Should be ISO 8601 with Z

            # create alert record
            database.store_alerts(
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
            processed_alerts.append(
                alert_id
            )  # append alert ID to processed_alerts array for tracking

        return (
            jsonify(
                {
                    "status": "received",
                    "alerts_processed": len(
                        processed_alerts
                    ),  # return number of successfully processed alerts
                    "alert_ids": processed_alerts,
                    "failed": len(failed_alerts),  # return number of failed alerts
                    "failed_details": (
                        failed_alerts if failed_alerts else None
                    ),  # return details of failed alerts if any
                    "received_at": current_time,
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": f"Error processing bulk alerts: {str(e)}"}), 500


# =========== Acknowledge alert endpoint ==========
@alert_bp.route("/acknowledge/<alert_id>", methods=["POST"])
def acknowledge_alert(alert_id):  # TODO: Change endpoint to integrate with database
    """
    Mark an alert as acknowledged by an administrator.

    Endpoint: POST /api/alerts/acknowledge/<alert_id>

    This endpoint should require admin authentication in production.

    request body (OPTIONAL):
    {
        "acknowledged_by": string (admin username or ID)
        "notes": string (optional notes about the acknowledgment)
    }

    Response (success):
    {
        "status": "acknowledged",
        "alert_id": string,
        "acknowledged_at": ISO 8601 string,
        "acknowledged_by": string
    }
    """
    try:
        # check if alert exists
        if alert_id not in MOCK_ALERTS:
            return jsonify({"error": "Alert not found.", "alert_id": alert_id}), 404

        # Get optional acknowledgment data
        data = request.get_json() or {}

        # update alert status
        current_time = dt.datetime.now(dt.timezone.utc).isoformat() + "Z"
        MOCK_ALERTS[alert_id]["acknowledged"] = True
        MOCK_ALERTS[alert_id]["acknowledged_at"] = current_time
        MOCK_ALERTS[alert_id]["acknowledged_by"] = data.get(
            "acknowledged_by", "unknown"
        )

        # add notes if provided
        if "notes" in data:
            MOCK_ALERTS[alert_id]["notes"] = data["notes"]

        return (
            jsonify(
                {
                    "status": "acknowledged",
                    "alert_id": alert_id,
                    "acknowledged_at": current_time,
                    "acknowledged_by": MOCK_ALERTS[alert_id]["acknowledged_by"],
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Failed to acknowledge alert: {str(e)}"}), 500


# ========== GET ALERT HISTORY ENDPOINT ==========
@alert_bp.route("/", methods=["GET"])
def get_alert_history():  # TODO: Change endpoint to integrate with database
    """
    Retrieve alert history with optional filters.

    Endpoint: GET /api/alerts/

    Query Parameters:
        ?client_id=uuid          # Filter by client ID
        ?severity=string         # Filter by severity level
        ?acknowledged=true/false # Filter by acknowledgment status
        ?event_type=string       # Filter by event type
        ?limit=integer           # Limit number of results

    Response (success):
    {
        "alerts": [
            {
                "alert_id": string,
                "client_id": string,
                "severity": string,
                "event_type": string,
                "timestamp": ISO 8601 string,
                "acknowledged": boolean,
                "details": {...}
            },
            ...
        ],
        "total": integer,
        "filtered": integer
    }
    """

    try:
        # get filter parameters
        client_id_filter = request.args.get("client_id")
        severity_filter = request.args.get("severity")
        ack_filter = request.args.get("acknowledged")
        event_type_filter = request.args.get("event_type")
        limit = request.args.get("limit", type=int, default=100)

        # start with all alerts
        alerts = list(MOCK_ALERTS.values())

        # apply filters
        if client_id_filter:
            alerts = [a for a in alerts if a["client_id"] == client_id_filter]

        if severity_filter:
            alerts = [a for a in alerts if a["severity"] == severity_filter]

        if ack_filter is not None:
            ack_bool = ack_filter.lower() == "true"
            alerts = [a for a in alerts if a["acknowledged"] == ack_bool]

        if event_type_filter:
            alerts = [a for a in alerts if a["event_type"] == event_type_filter]

        # sort by timestamp (newest first)
        alerts.sort(key=lambda x: x["timestamp"], reverse=True)

        # apply limit
        filtered_count = len(alerts)
        alerts = alerts[:limit]

        return (
            jsonify(
                {
                    "alerts": alerts,
                    "total": len(MOCK_ALERTS),
                    "filtered": filtered_count,
                    "returned": len(alerts),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve alerts: {str(e)}"}), 500


# ============ GET SINGLE ALERT ENDPOINT ============
@alert_bp.route("/<alert_id>", methods=["GET"])
def get_single_alert(alert_id):  # TODO: Change endpoint to integrate with database
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

    try:
        if alert_id not in MOCK_ALERTS:
            return jsonify({"error": "Alert not found.", "alert_id": alert_id}), 404

        return jsonify(MOCK_ALERTS[alert_id]), 200

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve alert: {str(e)}"}), 500
