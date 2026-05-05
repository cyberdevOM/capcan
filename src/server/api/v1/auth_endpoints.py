"""
auth_endpoints.py

Web user authentication endpoints:
  POST  /api/v1/login               — authenticate and establish a session
  POST  /api/v1/register            — create a new web user account
  PATCH /api/v1/users/<user_id>/role — update another user's role (admin/super-admin only)

Role hierarchy (highest → lowest):
  super-admin  — owner account; can create/promote admins; cannot be edited
  admin        — can manage analyst and read-only users
  analyst      — read/write access
  read-only    — view access only
"""

from flask import Blueprint, request, jsonify, session

from ...core.database import Database
from ...utils.encryptors import check_password, hash_password

auth_bp = Blueprint('auth', __name__)

# Roles that each caller level may assign
_SUPER_ADMIN_ASSIGNABLE = {'admin', 'analyst', 'read-only'}
_ADMIN_ASSIGNABLE       = {'analyst', 'read-only'}


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

        role = 'read-only'
        caller_id = session.get('user_id')
        if caller_id:
            caller = db.get_web_user_by_id(caller_id)
            caller_role = caller.get('role') if caller else None
            requested_role = data.get('role', 'read-only')
            if caller_role == 'super-admin' and requested_role in _SUPER_ADMIN_ASSIGNABLE:
                role = requested_role
            elif caller_role == 'admin' and requested_role in _ADMIN_ASSIGNABLE:
                role = requested_role

        db.create_web_user(username, pass_hash, email, role=role)
        return jsonify({'success': True, 'message': 'Account created successfully'}), 201
    finally:
        db.close()


@auth_bp.route('/users/<user_id>/role', methods=['PATCH'])
def update_user_role(user_id):
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    db = Database()
    try:
        caller = db.get_web_user_by_id(session['user_id'])
        caller_role = caller.get('role') if caller else None

        if caller_role not in ('super-admin', 'admin'):
            return jsonify({'success': False, 'message': 'Forbidden'}), 403

        if session['user_id'] == user_id:
            return jsonify({'success': False, 'message': 'Cannot modify your own role'}), 403

        target = db.get_web_user_by_id(user_id)
        if not target:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        target_role = target.get('role')

        # super-admin accounts can never be modified by anyone
        if target_role == 'super-admin':
            return jsonify({'success': False, 'message': 'Cannot modify the owner account'}), 403

        # regular admins cannot modify other admin accounts
        if caller_role == 'admin' and target_role == 'admin':
            return jsonify({'success': False, 'message': 'Cannot modify admin users'}), 403

        data = request.get_json(silent=True) or {}
        new_role = data.get('role')

        assignable = _SUPER_ADMIN_ASSIGNABLE if caller_role == 'super-admin' else _ADMIN_ASSIGNABLE
        if new_role not in assignable:
            return jsonify({'success': False, 'message': f'Invalid role for your permission level'}), 400

        ok = db.update_web_user(user_id, role=new_role)
        if not ok:
            return jsonify({'success': False, 'message': 'Database update failed'}), 500

        return jsonify({'success': True, 'role': new_role}), 200
    finally:
        db.close()
