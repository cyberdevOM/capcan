"""
login_endpoint.py

Provides a /login endpoint that accepts POST requests with JSON containing 'username' and 'password'.
Checks credentials against the database using bcrypt and returns a JSON response indicating success or failure.
"""

from flask import Blueprint, request, jsonify, session
from ..core.database import Database
from ..utils.encryptors import check_password

login_bp = Blueprint('login_api', __name__, url_prefix='/api/login')

@login_bp.route('', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username').strip()
    password = data.get('password').strip()
    if not username or not password:
        return jsonify({'success': False, 'message': 'Missing credentials'}), 400
    
    db = Database()
    try:
        stored_hash = db.get_user_auth(username)
        if stored_hash and check_password(password, stored_hash):
            session['user_id'] = db.get_web_user_id(username)
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    finally:
        db.close()
