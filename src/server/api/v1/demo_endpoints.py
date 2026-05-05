from flask import Blueprint, request, jsonify, session, current_app

from ...core.database import Database

demo_bp = Blueprint('demo', __name__, url_prefix='/demo')


@demo_bp.route('/status', methods=['GET'])
def demo_status():
    """Return current demo mode availability and how many clients have it enabled."""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorised'}), 401

    db = Database()
    try:
        current_user = db.get_web_user_by_id(session['user_id']) or {}
        if current_user.get('role') not in ('admin', 'super-admin'):
            return jsonify({'error': 'Admin only'}), 403

        client_ids = db.get_active_client_ids()
        demo_enabled_count = 0
        demo_pending_count = 0
        for cid in client_ids:
            settings, is_pending = db.get_latest_settings(cid)
            if (settings or {}).get('demo_mode') is True:
                demo_enabled_count += 1
                if is_pending:
                    demo_pending_count += 1
    finally:
        db.close()

    return jsonify({
        'server_demo_mode':     current_app.config.get('DEMO_MODE', False),
        'total_active_clients': len(client_ids),
        'demo_enabled_clients': demo_enabled_count,
        'demo_pending_clients': demo_pending_count,
    })


@demo_bp.route('/push', methods=['POST'])
def demo_push():
    """Push demo settings to all active clients. Admin only.

    Accepts demo_mode (bool) and/or demo_alerts_per_hour (int).
    If only demo_alerts_per_hour is provided, demo_mode is not overwritten.
    """
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorised'}), 401

    db = Database()
    try:
        current_user = db.get_web_user_by_id(session['user_id']) or {}
        if current_user.get('role') not in ('admin', 'super-admin'):
            return jsonify({'error': 'Admin only'}), 403

        body = request.get_json(silent=True) or {}
        demo_alerts_per_hour = body.get('demo_alerts_per_hour')

        push_payload = {}

        # Only include demo_mode if it was explicitly sent
        if 'demo_mode' in body:
            push_payload['demo_mode'] = bool(body['demo_mode'])

        if isinstance(demo_alerts_per_hour, (int, float)) and demo_alerts_per_hour > 0:
            push_payload['demo_alerts_per_hour'] = int(demo_alerts_per_hour)

        if not push_payload:
            return jsonify({'error': 'No valid settings provided'}), 400

        client_ids = db.get_active_client_ids()
        if not client_ids:
            return jsonify({'status': 'ok', 'queued': 0, 'message': 'No active clients found'})

        queued = db.set_pending_config(client_ids, push_payload)
    finally:
        db.close()

    demo_mode_value = push_payload.get('demo_mode')
    if demo_mode_value is None:
        msg = f'Alert rate updated for {queued} client(s)'
    else:
        msg = f'Demo mode {"enabled" if demo_mode_value else "disabled"} queued for {queued} client(s)'

    return jsonify({
        'status':  'ok',
        'queued':  queued,
        'message': msg,
        **({'demo_mode': demo_mode_value} if demo_mode_value is not None else {}),
    })
