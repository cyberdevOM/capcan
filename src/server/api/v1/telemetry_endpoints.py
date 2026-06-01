"""
Telemetry API Endpoints

Handles telemetry data submitted by clients:
- CPU, memory, disk, network, process metrics
- Data is stored in and read from the database
- HMAC authentication on all client-facing routes

Data Flow:
1. Client collects metrics and signs payload with HMAC
2. Client POSTs to /api/v1/telemetry/
3. Server validates signature and stores to DB
4. Server returns acknowledgement + any pending config
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, Any
import statistics as _statistics

from ...utils.validators import (
    validate_timestamp,
    validate_signature,
    extract_security_headers,
    generate_ack_id,
)
from ...core.database import Database
from ...utils import telemetry_cache

telemetry_bp = Blueprint('telemetry', __name__, url_prefix='/telemetry')

# ================= HELPER FUNCTIONS ================= 

def validate_telemetry_request(client_id: str) -> tuple[bool, Dict[str,any], int]:
    """
    Validates telemetry submission request against the database.

    args:
        client_id (str): UUID of the client from request headers.

    returns:
        Tuple of (success, response_dict, http_status_code)
    """

    # Extract security headers
    headers_client_id, timestamp, signature = extract_security_headers(request.headers)

    if not headers_client_id:
        return False, {
            "error": "Missing security headers",
            "required": ["X-Client-ID", "X-Timestamp", "X-Signature"]
        }, 401

    # validate timestamp is recent
    valid_time, time_error = validate_timestamp(timestamp)
    if not valid_time:
        return False, {"error": f"Invalid timestamp: {time_error}"}, 401

    # Check client is registered in the database
    db = Database()
    try:
        if not db.get_client_by_id(headers_client_id):
            return False, {
                "error": "Client not registered",
                "hint": "Register at POST /api/clients/register first."
            }, 401

        # get client secret from database
        secret_key = db.get_client_secret(headers_client_id)
        if not secret_key:
            return False, {"error": "Client secret not found"}, 401
    finally:
        db.close()

    # validate signature
    valid_sig, sig_error = validate_signature(
        client_id=headers_client_id,
        timestamp=timestamp,
        body=request.get_data(),
        received_signature=signature,
        secret_key=secret_key
    )

    if not valid_sig:
        return False, {"error": f"Invalid signature: {sig_error}"}, 401

    return True, {}, 200

def validate_telemetry_data(data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate telemetry data structure and values.

    Args:
        data (dict): Telemetry data dictionary from client.
    Returns:
        Tuple of (is_valid (bool), error_message (str))

    Example Valid Data:
    {
        "cpu_percent": 23.5,
        "memory_percent": 45.2,
        "disk_usage": 78.5,
        "network_sent_bytes": 123456,
        "network_recv_bytes": 654321,
        "process_count": 150,
        "load_average": [0.5, 0.7, 0.6] # optional
    }
    """

    # check required fields presence and types (only if present — fields may be disabled via remote config)
    percentage_fields = ['cpu_percent', 'memory_percent', 'disk_usage']
    for field in percentage_fields:
        if field in data:
            value = data[field]
            # check type
            if not isinstance(value, (int, float)):
                return False, f"{field} must be a number, got {type(value).__name__}"
            # check range (overflow for cpu on multi-core systems)
            if value < 0 or value > 100:
                return False, f"{field} must be between 0 and 100, got {value}"
            
    # validate byte count fields
    byte_fields = ['network_sent_bytes', 'network_recv_bytes','disk_read_bytes','disk_write_bytes']
    for field in byte_fields:
        if field in data:
            value = data[field]
            if not isinstance(value, int) or value < 0:
                return False, f"{field} must be a non-negative integer"
            
    # validate process count
    if 'process_count' in data:
        value = data['process_count']
        if not isinstance(value, int) or value < 0:
            return False, "process_count must be a non-negative integer"
    
    # validate load average
    if 'load_average' in data:
        value = data['load_average']
        if not isinstance(value, list) or len(value) !=3:
            return False, "load_average must be a list of 3 numbers"
        if not all(isinstance(x, (int,float)) for x in value):
            return False, "load_average values must be numbers"
    
    # validate uptime_seconds
    if 'uptime_seconds' in data:
        value = data['uptime_seconds']
        if not isinstance(value, int) or value < 0:
            return False, "uptime_seconds must be a non-negative integer"
        
    return True, ""
    
# ================= TELEMETRY ENDPOINTS =================

@telemetry_bp.route('/', methods=['POST'])
def submit_telemetry():
    """
    Submit telemetry data from client.

    Endpoint: POST /api/telemetry/

    This is the core endpoint for clients to submit system metrics. Clients call this every N minutes.

    Expected JSON payload:
    {
        "cpu_percent": float,       # CPU usage percentage
        "memory_percent": float,    # Memory usage percentage
        "memory_available": int, # Available memory in MB
        "disk_usage": float,        # Disk usage percentage
        "disk_read_bytes": int,     # Disk read bytes since last report
        "disk_write_bytes": int,    # Disk write bytes since last report
        "network_sent_bytes": int,  # Network sent bytes since last report
        "network_recv_bytes": int,  # Network received bytes since last report
        "process_count": int,       # Number of running processes
        "load_average": [float, float, float] # 1, 5, 15 min load averages (optional)
        "uptime_seconds": int,      # System uptime in seconds
        "custom_metrics": {         # Optional custom metrics
            "database_connections": int,
            "queue_size": int
        }
    }

    Response (success):
    {
        "status": "received",                   # acknowledgement status
        "ack_id": "unique_acknowledgement_id",  # unique ID for this submission
        "received_at": "ISO-8601 timestamp"     # time of receipt,
        "next_report_in": int                   # seconds until next report    
    }

    Response (error):
    {
        "error": "Invalid signature: signature mismatch"
    }
    """

    # extract client ID from headers for validation
    headers_client_id, _, _ = extract_security_headers(request.headers)

    if not headers_client_id:
        return jsonify({
            "error": "Missing X-Client-ID header"
        }), 401
    
    # validate request authentication
    valid, error_response, status_code = validate_telemetry_request(headers_client_id)
    if not valid:
        return jsonify(error_response), status_code

    try:
        # Parse telemetry data from request body
        data = request.get_json()

        if not data:
            return jsonify({"error": "Invalid or missing telemetry data"}), 400
        
        # validate telemetry data from request body
        valid_data, data_error = validate_telemetry_data(data)
        if not valid_data:
            return jsonify({"error": f"Invalid telemetry data: {data_error}"}), 400

        current_time = datetime.utcnow().isoformat()

        # Persist to database
        db = Database()
        try:
            db.store_client_telemetry(headers_client_id, data)
            pending_settings = db.deliver_pending_config(headers_client_id)
            effective = db.get_effective_settings(headers_client_id)
            reported_platform = data.get("platform")
            reported_hostname = data.get("hostname")
            if reported_platform and reported_hostname:
                db.update_client_os_hostname_on_first_contact(
                    headers_client_id, reported_platform, reported_hostname
                )
        finally:
            db.close()

        ack_id = generate_ack_id()

        # Derive next_report_in from effective settings (fallback to 300s)
        effective_interval = 300
        if pending_settings and isinstance(pending_settings.get("interval"), (int, float)):
            effective_interval = int(pending_settings["interval"])
        elif effective and isinstance(effective.get("interval"), (int, float)):
            effective_interval = int(effective["interval"])

        response = {
            "status": "received",
            "ack_id": ack_id,
            "received_at": current_time,
            "next_report_in": effective_interval,
        }
        if pending_settings:
            response["settings"] = pending_settings

        # Return success response
        return jsonify(response), 201 # Created
    
    except Exception as e:
        return jsonify({"error": f"Failed to process telemetry data: {str(e)}"}), 500
    
# ================= GET TELEMETRY HISTORY =================

@telemetry_bp.route('/<client_id>', methods=['GET']) 
# this should be a database query not an api endpoint
def get_telemetry_history(client_id: str):
    """Retrieve telemetry history for a client (HMAC authenticated).

    Query Parameters:
        ?limit=N   — number of records to return (default 100)
    """
    valid, error_response, status_code = validate_telemetry_request(client_id)
    if not valid:
        return jsonify(error_response), status_code

    try:
        limit = request.args.get('limit', default=100, type=int)
        db = Database()
        try:
            rows = db.get_client_telemetry(client_id, limit=limit)
        finally:
            db.close()

        records = [
            {"timestamp": r["timestamp"], **r["telemetry"]} for r in rows
        ]
        return jsonify({
            "client_id": client_id,
            "records": records,
            "count": len(records),
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve telemetry: {str(e)}"}), 500


# ================= Get Latest Telemetry =================
@telemetry_bp.route('/<client_id>/latest', methods=['GET'])
def get_latest_telemetry(client_id: str):
    """Return the most recent telemetry snapshot for a client (HMAC authenticated)."""
    valid, error_response, status_code = validate_telemetry_request(client_id)
    if not valid:
        return jsonify(error_response), status_code

    try:
        db = Database()
        try:
            row = db.get_latest_client_telemetry(client_id)
        finally:
            db.close()

        if not row:
            return jsonify({"error": "No telemetry data found for this client."}), 404

        return jsonify({
            "client_id": client_id,
            "timestamp": row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else row["timestamp"],
            **row["telemetry"],
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve latest telemetry: {str(e)}"}), 500


# ================ Get Telemetry Stats ================
@telemetry_bp.route('/<client_id>/stats', methods=['GET'])
def get_telemetry_stats(client_id: str):
    """Return statistical summary of a telemetry metric for a client (HMAC authenticated).

    Query Parameters:
        ?metric=cpu_percent   — metric field name (default: cpu_percent)
        ?limit=100            — number of recent records to include (default: 100)
    """
    valid, error_response, status_code = validate_telemetry_request(client_id)
    if not valid:
        return jsonify(error_response), status_code

    try:
        metric = request.args.get('metric', default='cpu_percent', type=str)
        limit = request.args.get('limit', default=100, type=int)

        db = Database()
        try:
            rows = db.get_client_telemetry(client_id, limit=limit)
        finally:
            db.close()

        values = [
            r["telemetry"][metric]
            for r in rows
            if isinstance(r.get("telemetry"), dict) and r["telemetry"].get(metric) is not None
        ]

        if not values:
            return jsonify({"error": f"No data for metric '{metric}'."}), 404

        result = {
            "metric": metric,
            "sample_count": len(values),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "avg": round(_statistics.mean(values), 2),
            "median": round(_statistics.median(values), 2),
        }
        if len(values) >= 10:
            sorted_values = sorted(values)
            result["percentile_95"] = round(sorted_values[int(len(sorted_values) * 0.95)], 2)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Failed to calculate telemetry stats: {str(e)}"}), 500


# ================= WEB UI TELEMETRY ENDPOINTS =================

@telemetry_bp.route('/web/<client_id>/history', methods=['GET'])
def web_client_telemetry(client_id):
    """Return recent telemetry history for a client (web session authenticated).

    Endpoint: GET /api/v1/telemetry/web/<client_id>/history?limit=50
    Returns records in chronological order (oldest first).
    """
    from flask import session as web_session
    if not web_session.get('user_id'):
        return jsonify({'error': 'Unauthorised'}), 401
    limit = request.args.get('limit', type=int, default=50)
    db = Database()
    try:
        rows = db.get_client_telemetry(client_id, limit=limit)
        # DB returns newest-first; reverse for chronological chart display
        rows = list(reversed(rows))
        return jsonify({'telemetry': rows, 'client_id': client_id})
    finally:
        db.close()
# ================= END OF FILE =================