"""
login_endpoint.py

Provides a /login endpoint that accepts POST requests with JSON containing 'username' and 'password' (SHA-256 hex hash).
Checks credentials against the database and returns a JSON response indicating success or failure.
"""

from flask import Blueprint, request, jsonify
from ..core.database import Database

login_bp = Blueprint('login_api', __name__, url_prefix='/api/login')

@login_bp.route('', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password_hash = data.get('password')
    if not username or not password_hash:
        return jsonify({'success': False, 'message': 'Missing credentials'}), 400
    
    # Fetch the stored password hash for the given username from the database
    db = Database()
    stored_hash = db.get_user_auth(username)  
    if stored_hash and stored_hash == password_hash:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
