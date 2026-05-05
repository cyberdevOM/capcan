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
from ...core.database import Database

# Create a persistent Database instance for API handlers
database = Database()

# Import security validators
from ...utils.validators import (
    validate_timestamp,
    validate_signature,
    extract_security_headers,
    generate_ack_id,
)

# create blueprint for client endpoints
client_bp = Blueprint('clients', __name__, url_prefix='/clients')



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


# ================ Remote Config Push ==================

@client_bp.route('/config', methods=['PUT'])
def push_client_config():
    """
    Push settings to one or more clients. Requires an active admin web session.

    Endpoint: PUT /api/clients/config

    Request Body (JSON):
    {
        "client_ids": ["uuid1", "uuid2", ...],
        "settings": {
            "interval": 300,
            "collect": {
                "cpu": true,
                "memory": true,
                "disk": true,
                "network": true,
                "processes": true
            }
        }
    }

    Response:
    {
        "updated": N,
        "message": "Settings queued for N client(s)"
    }
    """
    from flask import session as web_session

    if not web_session.get('user_id'):
        return jsonify({"error": "Authentication required"}), 401

    db = Database()
    try:
        user = db.get_web_user_by_id(web_session['user_id']) or {}
    finally:
        db.close()

    role = user.get('role', 'read-only')
    _ADMIN_ROLES = ('super-admin', 'admin')

    if role not in _ADMIN_ROLES and role != 'analyst':
        return jsonify({"error": "Insufficient permissions"}), 403

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    client_ids = body.get("client_ids")
    settings = body.get("settings")

    # "all" as a special value pushes to every active client
    if client_ids == "all":
        db2 = Database()
        try:
            client_ids = db2.get_active_client_ids()
        finally:
            db2.close()
        if not client_ids:
            return jsonify({"updated": 0, "message": "No active clients found"}), 200

    if not isinstance(client_ids, list) or not client_ids:
        return jsonify({"error": "'client_ids' must be a non-empty list"}), 400
    if not isinstance(settings, dict):
        return jsonify({"error": "'settings' must be an object"}), 400

    # Validate settings fields
    allowed_collect_keys = {"cpu", "memory", "disk", "network", "processes"}
    if "interval" in settings:
        try:
            interval = int(settings["interval"])
            min_interval = 10 if role in _ADMIN_ROLES else 1800
            if interval < min_interval:
                return jsonify({"error": f"'interval' must be >= {min_interval} seconds"}), 400
            settings["interval"] = interval
        except (TypeError, ValueError):
            return jsonify({"error": "'interval' must be an integer"}), 400

    if "collect" in settings:
        if not isinstance(settings["collect"], dict):
            return jsonify({"error": "'collect' must be an object"}), 400
        unknown = set(settings["collect"]) - allowed_collect_keys
        if unknown:
            return jsonify({"error": f"Unknown collect keys: {', '.join(unknown)}"}), 400
        for k, v in settings["collect"].items():
            if not isinstance(v, bool):
                return jsonify({"error": f"collect.{k} must be a boolean"}), 400

    # Strip any keys that must not be remotely configurable
    for forbidden in ("server_url", "client_id", "secret_key"):
        settings.pop(forbidden, None)

    db = Database()
    try:
        updated = db.set_pending_config(client_ids, settings)
    finally:
        db.close()

    return jsonify({"updated": updated, "message": f"Settings queued for {updated} client(s)"}), 200

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


# ================ Admin Web UI Client Management ==================

@client_bp.route('/admin/build-status', methods=['GET'])
def admin_build_status():
    """Return the current client bundle build status."""
    from flask import session as web_session
    if not web_session.get('user_id'):
        return jsonify({"error": "Authentication required"}), 401
    from ...utils.deployer import get_build_status
    return jsonify(get_build_status()), 200


@client_bp.route('/admin/add', methods=['POST'])
def admin_add_client():
    """
    Register and deploy a new client from the web admin UI.

    Endpoint: POST /api/clients/admin/add

    Request Body (JSON):
    {
        "username":   "alice",           (SSH user; also used as hostname)
        "ip_address": "192.168.1.100",
        "password":   "secret"           (SSH + sudo — never stored)
    }
    """
    from flask import session as web_session
    from ...utils.deployer import deploy_client

    if not web_session.get('user_id'):
        return jsonify({"error": "Authentication required"}), 401

    db_auth = Database()
    try:
        caller = db_auth.get_web_user_by_id(web_session['user_id']) or {}
    finally:
        db_auth.close()
    if caller.get('role') not in ('super-admin', 'admin'):
        return jsonify({"error": "Admin role required"}), 403

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    username   = (body.get("username")   or "").strip()
    ip_address = (body.get("ip_address") or "").strip()
    password   = body.get("password", "")

    if not username:
        return jsonify({"error": "'username' is required"}), 400
    if not ip_address:
        return jsonify({"error": "'ip_address' is required"}), 400
    if not password:
        return jsonify({"error": "'password' is required"}), 400

    client_id  = str(uuid.uuid4())
    secret_key = generate_secret_key()

    # Register in DB first so the client can authenticate on first contact
    db = Database()
    try:
        db.register_client(
            client_id, hostname=username, client_os='linux',
            client_secret=secret_key, ip_address=ip_address, ssh_user=username,
        )
    except Exception as exc:
        db.close()
        return jsonify({"error": f"Failed to register client: {exc}"}), 500
    finally:
        db.close()

    # Deploy the bundle to the target machine
    success, message, real_hostname = deploy_client(ip_address, username, password, client_id, secret_key)
    if not success:
        # Roll back the DB record so there is no orphaned entry
        db = Database()
        try:
            db.delete_client(client_id)
        finally:
            db.close()
        return jsonify({"error": message}), 500

    # Update with the machine's real hostname (fetched via SSH during deploy)
    if real_hostname and real_hostname != username:
        db = Database()
        try:
            db.update_client_hostname_os(client_id, real_hostname, 'linux')
        finally:
            db.close()
        display_hostname = real_hostname
    else:
        display_hostname = username

    return jsonify({
        "client_id": client_id,
        "hostname":  display_hostname,
        "message":   message,
    }), 201


@client_bp.route('/admin/<client_id>', methods=['DELETE'])
def admin_delete_client(client_id):
    """
    Uninstall and remove a client from the web admin UI.

    Endpoint: DELETE /api/clients/admin/<client_id>

    Request Body (JSON):
    {
        "password": "secret"    (SSH + sudo password for the target machine)
    }
    """
    from flask import session as web_session
    from ...utils.deployer import undeploy_client

    if not web_session.get('user_id'):
        return jsonify({"error": "Authentication required"}), 401

    db_auth = Database()
    try:
        caller = db_auth.get_web_user_by_id(web_session['user_id']) or {}
    finally:
        db_auth.close()
    if caller.get('role') not in ('super-admin', 'admin'):
        return jsonify({"error": "Admin role required"}), 403

    body     = request.get_json(silent=True) or {}
    password = body.get("password", "")
    if not password:
        return jsonify({"error": "'password' is required"}), 400

    db = Database()
    try:
        deploy_info = db.get_client_deploy_info(client_id)
        if not deploy_info:
            return jsonify({"error": "Client not found"}), 404

        ip_address = deploy_info.get("ip_address")
        ssh_user   = deploy_info.get("ssh_user")
    finally:
        db.close()

    warnings = []

    # Attempt remote uninstall; warn but continue if it fails (client may be unreachable)
    if ip_address and ssh_user:
        success, msg = undeploy_client(ip_address, ssh_user, password)
        if not success:
            warnings.append(f"Remote uninstall warning: {msg}")
    else:
        warnings.append("No SSH info stored — skipping remote uninstall.")

    # Always remove the DB record
    db = Database()
    try:
        db.delete_client(client_id)
    except Exception as exc:
        return jsonify({"error": f"Failed to remove client from database: {exc}"}), 500
    finally:
        db.close()

    response = {"message": "Client removed."}
    if warnings:
        response["warnings"] = warnings
    return jsonify(response), 200