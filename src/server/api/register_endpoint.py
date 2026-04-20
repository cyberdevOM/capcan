"""
register_endpoint.py

Provides a /api/register endpoint that accepts POST requests with JSON containing
'username', 'email', and 'password' (client-side bcrypt hash).
Creates a new read-only web user and returns a JSON success/error response.
"""

from flask import Blueprint, request, jsonify
from ..core.database import Database
from ..utils.encryptors import hash_password

register_bp = Blueprint('register_api', __name__, url_prefix='/api/register')

@register_bp.route('', methods=['POST'])
def register():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    username = data.get('username', '').strip()
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    db = Database()
    try:
        if db.get_web_user(username):
            return jsonify({'success': False, 'message': 'Username already taken'}), 409

        pass_hash = hash_password(password)
        db.create_web_user(username, pass_hash, email, role='read-only')
        return jsonify({'success': True, 'message': 'Account created successfully'}), 201
    finally:
        db.close()
