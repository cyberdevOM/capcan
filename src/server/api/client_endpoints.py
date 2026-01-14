"""
Client API Endpoints

This module handles al client-related API operations:
- Registration: New clients join the system.
- Heartbeats: Clients send periodic "I'm alive" signals.
- Info Retrieval: Get client details and status.

Security Model:
1. Registration client sends basic info -> server generates shared secret.
2. All future requests: Client signs with secret -> server validates signature.
3. Timestamps preventing replay attacks (5 minutes window).

Endpoint Flow:
POST /api/clients/register
    Client Gets secret key.
POST /api/clients/<id>/heartbeat (with auth)
GET /api/clients/<id> (with auth)
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import secrets
import uuid
from typing import Dict, Any

# Import security validators
from ..utils.validators import (
    validate_timestamp,
    validate_signature,
    extract_security_headers,
    generate_ack_id,
    register_client_secret,
    get_client_secret
)

# create blueprint for client endpoints
client_bp = Blueprint('clients', __name__, url_prefix='/api/clients')

# ================ Mock DataStorage =================
# In production, this would be a database model

MOCK_CLIENTS = {

}

# ================ Helper Functions ==================

def generate_secret_key() -> str:
    """Generates a cryptographically secure random secret key."""
    return secrets.token_hex(32)  # 256-bit key

def validate_client_request(client_id: str) -> tuple[bool, Dict[str, any], int]:
    """
    Common validation logic for auth client requests.

    Args:
        client_id (str): UUID of the client making the request.
    Returns:
        tuple: (is_valid (bool), response (dict), status_code (int))
        - If validation fails: (False, error_dict, 401-404)
        - If validation succeeds: (True, {}, 200)
    """

    headers_client_id, timestamp, signature = extract_security_headers(request.headers)

    # check all headers present
    if not headers_client_id:
        return False, {"error": "Missing security headers (X-Client-ID, X-Timestamp, X-Signature)"}, 401
    
    # check client ID matches URL
    if headers_client_id != client_id:
        return False, {"error": "Client ID mismatch between URL and headers"}, 403
    
    # check client exists
    if client_id not in MOCK_CLIENTS:
        return False, {"error": "Client ID not registered"}, 404

    # validate timestamp and signature
    valid_time, time_errror = validate_timestamp(timestamp)
    if not valid_time:
        return False, {"error": f"Invalid timestamp: {time_errror}"}, 401
    
    # get client secret
    secret_key = get_client_secret(client_id)
    if not secret_key:
        return False, {"error": "Client secret not found - re-register required"}, 401
    
    valid_sig, sig_error = validate_signature(
        client_id=client_id,
        timestamp=timestamp,
        body=request.get_data(),
        received_signature=signature,
        secret_key=secret_key
    )

    if not valid_sig:
        return False, {"error": f"Invalid signature: {sig_error}"}, 401
    
    return True, {}, 200


# ================ API Endpoints ==================

@client_bp.route('/register', methods=['POST'])
def register_client():
    """
    Register a new client with the system.

    Endpoint: POST /api/clients/register

    Request Body (JSON):
    {
        "hostname": "server-01", # client hostname
        "platform": "linux", # client host os
        "ip_address": "192.168.1.100", # optional
        "version": "0.03" # client software version
    }

    Response Success (JSON):
    {
        "client_id": "<uuid>",
        "secret_key": "<secret_key>",
        "message": "Client registered successfully",
        "registered_at": "<timestamp>"
    }
    Response Error (JSON):
    {
        "error": "<error_message>"
    }
    """

    try: 
        # Parse and validate request JSON
        data = request.get_json()
        if not data:
            return jsonify({"error": "No json data provided"}), 400
        
        # Validate required fields
        required_fields = ["hostname", "platform"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate platform
        valid_platforms = ["linux", "windows", "macos"]
        if data["platform"] not in valid_platforms:
            return jsonify({"error": f"Invalid platform. Must be one of: {', '.join(valid_platforms)}"}), 400
        
        # Generate client ID and secret key
        client_id = str(uuid.uuid4())
        secret_key = generate_secret_key()
        
        # Register client secret
        register_client_secret(client_id, secret_key)

        # Get client IP from request or data (use X-Forwarded-For if behind proxy)
        ip_address = data.get("ip_address", request.remote_addr)

        # create client record
        current_time = datetime.utcnow().isoformat() + 'Z'
        client_record = {
            "client_id": client_id,
            "hostname": data["hostname"],
            "platform": data["platform"],
            "ip_address": ip_address,
            "version": data.get("version", "unknown"),
            "status": "online", # default status for new client
            "registered_at": current_time, # registration timestamp
            "last_seen": current_time # initialize last_seen to registration time
        }

        # Store in mock database
        MOCK_CLIENTS[client_id] = client_record

        # Return success response
        # This is the only time we return the secret key
        return jsonify({
            "client_id": client_id,
            "secret_key": secret_key,
            "message": "Client registered successfully",
            "registered_at": current_time
        }), 201 # Created
    except Exception as e:
        # catch-all for unexpected errors
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500
    
# ================ Heartbeat Endpoint ==================

@client_bp.route('/<client_id>/heartbeat', methods=['POST'])
def client_heartbeat(client_id: str):
    """
    Client sends periodic hearbeat to show its still alive.
    
    Endpoint: POST /api/clients/<client_id>/heartbeat

    If the server doesnt receive a heartbeat within a timeframe it marks the client as offline.

    Request Body: (optional JSON)
    {
        "status": "online" # or "warning", "error"
        "message": "Optional status message"    
    }

    Response Success: (JSON) 
    {
        "status": "acknowledged",
        "ack_id": "<acknowledgement_id>",
        "server_time": "<timestamp>",
        "next_heartbeat": "<seconds>"
    }
    """

    # validate request
    valid, error_response, status_code = validate_client_request(client_id)
    if not valid:
        return jsonify(error_response), status_code
    
    try:
        # Get optional body data
        data = request.get_json() or {}

        # update clients last seen timestamp
        current_time = datetime.utcnow().isoformat() + 'Z'
        MOCK_CLIENTS[client_id]['last_seen'] = current_time

        # update status if provided
        if 'status' in data:
            valid_statuses = ['online', 'warning', 'error', 'offline']
            if data['status'] in valid_statuses:
                MOCK_CLIENTS[client_id]['status'] = data['status']

        # generate acknowledgement id
        ack_id = generate_ack_id()

        #return success response
        return jsonify({
            "status": "acknowledged",
            "ack_id": ack_id,
            "server_time": current_time,
            "next_heartbeat": 300 # seconds until next heartbeat
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"Heartbeat failed: {str(e)}"}), 500
    
# ================ Client Info Endpoint ==================

@client_bp.route('/<client_id>', methods=['GET'])
def get_client_info(client_id: str):
    """
    Retrieve detailed information about a client.

    Endpoint: GET /api/clients/<client_id>

    Resposnse Success (JSON):
    {
        "client_id": "<uuid>",
        "hostname": "server-01",
        "platform": "linux",
        "ip_address": "<ip_address>",
        "version": "0.03",
        "status": "online",
        "registered_at": "<timestamp>",
        "last_seen": "<timestamp>"    
    }
    """

    # validate request
    valid, error_response, status_code = validate_client_request(client_id)
    if not valid:
        return jsonify(error_response), status_code
    
    try:
        # Get client data from mock database
        client_data = MOCK_CLIENTS[client_id]

        return jsonify(client_data), 200

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve client info: {str(e)}"}), 500
    

# ================ UPDATE CLIENT STATUS ENDPOINT ==================

@client_bp.route('/<client_id>/status', methods=['PUT'])
def update_client_status(client_id: str):
    """
    Update client status and metadata.

    Endpoint: PUT /api/clients/<client_id>/status

    Request Body (JSON):
    {
        "hostname": "<hostname>", # optional
        "ip_address": "<ip_address>", # optional
        "version": "<version>", # optional
        "status": "<status>" # optional
    }

    Response Success (JSON):
    {
        "message": "Client status updated successfully",
        "updated_feilds": ["<field1>", "<field2>", ...]
        "updated_at": "<timestamp>"
    }
    """

    # validate request
    valid, error_response, status_code = validate_client_request(client_id)
    if not valid:
        return jsonify(error_response), status_code
    
    try:
        # Parse request JSON
        data = request.get_json()

        if not data:
            return jsonify({"error": "No update data provided"}), 400
        
        # track which fields were updated
        updated_fields = []

        # Update allowed fields
        allowed_fields = ["hostname", "ip_address", "version", "status"]
        for field in allowed_fields:
            if field in data:
                MOCK_CLIENTS[client_id][field] = data[field]
                updated_fields.append(field)
        
        # update last_seen timestamp
        current_time = datetime.utcnow().isoformat() + 'Z'
        MOCK_CLIENTS[client_id]['last_seen'] = current_time

        # Return success response
        return jsonify({
            "message": "Client status updated successfully",
            "updated_fields": updated_fields,
            "updated_at": current_time
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"Update failed: {str(e)}"}), 500
# Note: In a production system, proper logging, error handling, and database interactions would be implemented.

# =============== List All Clients Endpoint (ADMIN ONLY) ==================

@client_bp.route('/', methods=['GET'])
def list_all_clients():
    """
    List all registered clients
    
    Endpoint: GET /api/clients

    # Note: This endpoint should be protected and accessible only to admin users.
    # for testing it is left open.

    Query Parameters:
        ?status=<status> : Filter clients by status (online, offline, warning, error)
        ?platform=<platform> : Filter clients by platform (linux, windows, macos)
    
    Response Success (JSON):
    {
        "clients": [
            {"client_data_1"}
            {"client_data_2"}
            ...
        ],
        "total_clients": <number>,
        "filtered_clients": <number>
    }
    """

    try:
        # Get filter params
        status_filter = request.args.get('status')
        platform_filter = request.args.get('platform')

        # Start with all clients
        clients = list(MOCK_CLIENTS.values())

        # Apply status filter if provided
        if status_filter:
            clients = [c for c in clients if c['status'] == status_filter]
        
        if platform_filter:
            clients = [c for c in clients if c['platform'] == platform_filter]

        # Return client list
        return jsonify({
            "clients": clients,
            "total": len(MOCK_CLIENTS),
            "filtered": len(clients)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to list clients: {str(e)}"}), 500
