"""
Telemetry API Endpoints

This module handles system telemetry data submissions from clients.
- CPU usage, memory, disk I/O
- Network statistics
- process information
- custom metrics

Data Flow
1. Client collects metrics (CPU, RAM, disk, network)
2. Client signs data with HMAC
3. Client sends POST request to /api/telemetry
4. Server validates signature
5. Server stores data (mock dictg for temp, database in prod)
6. Server returns acknowledgement
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, Any, List
import time

from ..utils.validators import (
    validate_timestamp,
    validate_signature,
    extract_security_headers,
    generate_ack_id,
    get_client_secret
)

# create Flask Blueprint for telemetry endpoints
telemetry_bp = Blueprint('telemetry', __name__, url_prefix='/api/telemetry')

# MOCK DATA STORAGE - In production, this would be a database
MOCK_TELEMETRY = {
    # FORMAT: {client_id: [list of telemetry entries]}
    # Example entry:
    # "client-uuid": [
    #     {
    #         "timestamp": "ISO-8601",
    #         "cpu_usage": 23.5,
    #         "memory_usage": 45.2,
    #         "disk_io": {...},
    #         "network_stats": {...},
    #         "process_info": [...],
    #     },
    #     ...
    # ]
}

# Track client existance, in prod this would be a DB query
MOCK_REGISTERED_CLIENTS = set()

# ================= HELPER FUNCTIONS ================= 

def validate_telemetry_request(client_id: str) -> tuple[bool, Dict[str,any], int]:
    """
    Validates telemetry summission request.
    
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
    
    # Check client is registered
    if headers_client_id not in MOCK_REGISTERED_CLIENTS:
        return False, {
            "error": "Client not registered",
            "hint": "Register at POST /api/clients/register first." # possible sec issue if pub
        }
    
    # get client secret key
    secret_key = get_client_secret(headers_client_id)
    if not secret_key:
        return False, {"error": "Client secret not found"}, 401
    
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

    # check required fields presence and types
    required_fields = ['cpu_percent', 'memory_percent', 'disk_usage']
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # validate required percentage fields
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
        "memory_available_mb": int, # Available memory in MB
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

        # Add metadata to telemetry entry
        current_time = datetime.utcnow().isoformat()
        telemetry_entry = {
            "timestamp": current_time,
            "client_id": headers_client_id,
            **data # spread operator merges data dict into telemetry_entry
        }

        # Store telemetry data in mock storage
        if headers_client_id not in MOCK_TELEMETRY:
            MOCK_TELEMETRY[headers_client_id] = []
        
        MOCK_TELEMETRY[headers_client_id].append(telemetry_entry)

        # Generate acknowledgement I
        ack_id = generate_ack_id()

        # Return success response
        return jsonify({
            "status": "received",
            "ack_id": ack_id,
            "received_at": current_time,
            "next_report_in": 300  # clients should report every 5 minutes
        }), 201 # Created
    
    except Exception as e:
        return jsonify({"error": f"Failed to process telemetry data: {str(e)}"}), 500
    
# ================= GET TELEMETRY HISTORY =================

@telemetry_bp.route('/<client_id>', methods=['GET'])
def get_telemetry_history(client_id: str):
    """
    Retrieve telemetry history for a specific client.

    Endpoint: GET /api/telemetry/<client_id>

    Use Cases:
    - Dashboard needs to graph CPU usage over time.
    - Admin wants to analyze historical memory usage trends.
    - Anomaly detection needs a baseline data set.

    Query Parameters:
        ?limit=N          # Limit to last N entries (default 100)
        ?start=ISO-8601   # Start timestamp for filtering
        ?end=ISO-8601     # End timestamp for filtering
        ?metric=cpu,memory# Comma-separated list of metrics to include (cpu, memory, disk, network, processes)
    
    Response (success):
    {
        "client_id": "uuid",
        "records": [
            {
            "timestamp": "ISO-8601",
            "cpu_percent": float,
            "memory_percent": float,
            ...
            },
        ...
        ],
        "count": int,
        "total_available": int
    }
    """

    # validate request authentication
    valid, error_response, status_code = validate_telemetry_request(client_id)
    if not valid:
        return jsonify(error_response), status_code
    
    try:
        # Check if we have any telemetry for this client
        if client_id not in MOCK_TELEMETRY:
            return jsonify({
                "client_id": client_id,
                "records": [],
                "count": 0,
                "message": "No telemetry data found for this client."
            }), 200
        
        # Get all telemetry records for the client
        all_records = MOCK_TELEMETRY[client_id]

        # Parse query parameters
        limit = request.args.get('limit', default=100, type=int)
        since = request.args.get('start', default=None, type=str)
        metrics_filter = request.args.get('metric', default=None, type=str)

        # Filter by timestamp if 'since' provided
        if since:
            # Filter records where timestamp is after since
            # Note: we need to convert ISO-8601 timestamp back to UNIX for comparison
            Filtered_records = [
                r for r in all_records
                if datetime.fromisoformat(r['timestamp'].rstrip('Z')).timestamp() > since
            ]
        else:
            Filtered_records = all_records
        
        # Get the most recent 'limit' records
        recent_records = Filtered_records[-limit:]

        # Filter to specified metrics if requested
        if metrics_filter:
            requested_metrics = [m.strip() for m in metrics_filter.split(',')]
            requested_metrics.append('timestamp') # Always include timestamp

            # filter each record to only include requested metrics
            recent_records = [
                {k: v for k, v in record.items() if k in requested_metrics}
                for record in recent_records
            ]

            # Return telemetry history
            return jsonify({
                "client_id": client_id,
                "records": recent_records,
                "count": len(recent_records),
                "total_available": len(all_records)
            }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve telemetry: {str(e)}"}), 500
    
# ================= Get Latest Telemetry =================
@telemetry_bp.route('/<client_id>/latest', methods=['GET'])
def get_latest_telemetry(client_id: str):
    """
    Get the most recent telemetry snapshot for a client

    Endpoint: GET /api/telemetry/<client_id>/latest

    Use Cases:
    - Dashboard "Current Status" widget needs latest  metrics.
    - Quick health check without fetching full history.
    - Real-time monitoring display

    Response (success):
    {
        "client_id": "uuid",
        "timestamp": "ISO-8601",
        "cpu_percent": float,
        "memory_percent": float,
        "disk_usage": float,
        ...
    }
    """

    # validate request authentication
    valid, error_response, status_code = validate_telemetry_request(client_id)
    if not valid:
        return jsonify(error_response), status_code
    
    try:
        # Check if we have any telemetry for this client
        if client_id not in MOCK_TELEMETRY or not MOCK_TELEMETRY[client_id]:
            return jsonify({
                "error": "No telemetry data found for this client."
            }), 404
        
        latest_record = MOCK_TELEMETRY[client_id][-1]

        return jsonify({latest_record}), 200
    
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve latest telemetry: {str(e)}"}), 500

# ================ Get Telemetry Stats ================
@telemetry_bp.route('/<client_id>/stats', methods=['GET'])
def get_telemetry_stats(client_id: str):
    """
    Get Statical summaries of telemetry data for a client.
    
    Endpoint: GET /api/telemetry/<client_id>/stats

    Use Cases:
    - Dashboard "average CPU Usage" over time.
    - Detect anomalies (current value vs average)
    - Percentiles (95th percentile network usage)

    Response (success):
    {
        "metric": "cpu_percent",
        "period": seconds,
        "sample_count": int,
        "min": float,
        "max": float,
        "avg": float,
        "median": float,
        "percentile_95": float
    }
    """

    # validate request authentication
    valid, error_response, status_code = validate_telemetry_request(client_id)
    if not valid:
        return jsonify(error_response), status_code
    
    try:
        # Check if we have telemetry for this client
        if client_id not in MOCK_TELEMETRY or not MOCK_TELEMETRY[client_id]:
            return jsonify({"error": "No telemetry data found for this client."}), 404
        
        # Get query parameters
        metric = request.args.get('metric', default='cpu_percent', type=str)
        period = request.args.get('period', default=3600, type=int) # default 1 hour

        current_time = time.time()
        cutoff_time = current_time - period # UNIX timestamp

        records = MOCK_TELEMETRY[client_id]
        recent_records = [
            r for r in records
            if datetime.fromisoformat(r['timestamp'].rstrip('Z')).timestamp() >= cutoff_time
        ]

        # Extract metric values
        values = [r.get(metric) for r in recent_records if metric in r and r[metric] is not None]

        if not values:
            return jsonify({"error": f"No data for metric '{metric}' in the specified period."}), 404
        
        # Calculate statistics
        import statistics # python built-in statistics module

        stats = {
            "metric": metric,
            "period": period,
            "sample_count": len(values),
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "avg": round(statistics.mean(values), 2),
            "median": round(statistics.median(values), 2),
        }

        # Calculate 95th percentile
        if len(values) >= 10:
            sorted_values = sorted(values)
            # index for 95th percentile
            percentile_index = int(len(sorted_values) * 0.95)
            stats["percentile_95"] = round(sorted_values[percentile_index], 2)

        return jsonify(stats), 200
    
    except Exception as e:
        return jsonify({"error": f"Failed to calculate telemetry stats: {str(e)}"}), 500
    
# ================= Register Client (for testing only) =================
@telemetry_bp.route('/register-client/<client_id>', methods=['POST'])
def register_client(client_id: str):
    """
    Helper endpoint to register a client for testing.

    NOTE: This is a temporary endpoint, in production clients regist trough /api/clients/register

    This endpoint adds the client_id to the MOCK_REGISTERED_CLIENTS set. 
    so we can test telemetry endpoints without implementing a full client registration flow.
    
    DELETE THIS ENDPOINT IN PRODUCTION.
    """

    MOCK_REGISTERED_CLIENTS.add(client_id)
    return jsonify({
        "message": f"Client registered for telemetry (testing only)",
        "client_id": client_id
    }), 201

# ================= END OF FILE =================