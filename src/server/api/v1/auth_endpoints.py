"""
auth_endpoints.py

Web user authentication endpoints:
  POST /api/v1/login    — authenticate and establish a session
  POST /api/v1/register — create a new read-only web user account
"""

from flask import Blueprint, request, jsonify, session

from ...core.database import Database
from ...utils.encryptors import check_password, hash_password

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
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


@auth_bp.route('/register', methods=['POST'])
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
