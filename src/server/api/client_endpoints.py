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
import datetime as dt
import secrets
import uuid
from typing import Dict, Any
from ..core.database import Database

# Create a persistent Database instance for API handlers
database = Database()

# Import security validators
from ..utils.validators import (
    validate_timestamp,
    validate_signature,
    extract_security_headers,
    generate_ack_id,
)

# create blueprint for client endpoints
client_bp = Blueprint('clients', __name__, url_prefix='/api/clients')



# ================ Helper Functions ==================

def generate_secret_key() -> str:
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
    #! REPLACED WITH DATABASE CALL TO SEE IF CLIENT ID MATCHES CLIENT
    if not database.get_client_by_id(client_id):
        return False, {"error": "Client ID Does not exist"}

    # validate timestamp and signature
    valid_time, time_errror = validate_timestamp(timestamp)
    if not valid_time:
        return False, {"error": f"Invalid timestamp: {time_errror}"}, 401
    
    # get client secret from database
    secret_key = database.get_client_secret(client_id)
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
    
    # NOTE: do not close the shared Database instance here; other handlers may reuse it
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

    #! Only register clients once aproval is given from the dashboard.

    try: 
        # Parse and validate request JSON
        # Use silent=True to avoid raising a BadRequest on empty/malformed JSON
        data = request.get_json(silent=True)
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

        # Validate version if provided, otherwise default to 0.0
        version = data.get("version", 0.0)
        try:
            # Accept either numeric or string representations of floats
            version = float(version)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid version. Version must be a floating point number"}), 400

        current_time = dt.datetime.now(dt.timezone.utc)

        # Persist client record (client_secret stored with client data)
        database.register_client(client_id, data["hostname"], data["platform"], secret_key)

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