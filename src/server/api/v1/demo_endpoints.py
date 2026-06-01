from flask import Blueprint, request, jsonify, session, current_app

from ...core.database import Database

demo_bp = Blueprint('demo', __name__, url_prefix='/demo')


@demo_bp.route('/status', methods=['GET'])
def demo_status():
    """Return current demo mode status broken down by simulation mode.

    Returns per-mode client counts ('off', 'synthetic', 'script') plus a
    total pending-changes count for clients that haven't yet applied the
    last push.
    """
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorised'}), 401

    db = Database()
    try:
        current_user = db.get_web_user_by_id(session['user_id']) or {}
        if current_user.get('role') not in ('admin', 'super-admin'):
            return jsonify({'error': 'Admin only'}), 403

        client_ids = db.get_active_client_ids()
        mode_counts = {'false': 0, 'simulated': 0, 'script': 0}
        pending_count = 0

        for cid in client_ids:
            settings, is_pending = db.get_latest_settings(cid)
            cfg = settings or {}
            # Resolve mode from stored config — handle both wire formats
            sim = cfg.get('demo_sim_mode')
            if sim in ('off', 'synthetic', 'script'):
                _sim_map = {'off': 'false', 'synthetic': 'simulated', 'script': 'script'}
                dm = _sim_map[sim]
            else:
                dm = cfg.get('demo_mode', 'false')
                if isinstance(dm, bool):
                    dm = 'simulated' if dm else 'false'
                elif dm not in mode_counts:
                    dm = 'false'
            mode_counts[dm] += 1
            if is_pending:
                pending_count += 1
    finally:
        db.close()

    return jsonify({
        'server_demo_mode':     current_app.config.get('DEMO_MODE', False),
        'total_active_clients': len(client_ids),
        'modes':                mode_counts,
        'pending_changes':      pending_count,
    })


@demo_bp.route('/push', methods=['POST'])
def demo_push():
    """Push demo simulation mode to all active clients. Admin only.

    Accepted fields:
      demo_mode (str)          – 'false' | 'simulated' | 'script'
      demo_alerts_per_hour (int) – alert rate (simulated mode only)
    """
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorised'}), 401

    db = Database()
    try:
        current_user = db.get_web_user_by_id(session['user_id']) or {}
        if current_user.get('role') not in ('admin', 'super-admin'):
            return jsonify({'error': 'Admin only'}), 403

        body = request.get_json(silent=True) or {}
        demo_mode            = body.get('demo_mode')
        demo_alerts_per_hour = body.get('demo_alerts_per_hour')

        push_payload = {}

        if demo_mode is not None:
            if demo_mode not in ('false', 'simulated', 'script'):
                return jsonify({'error': 'demo_mode must be false, simulated, or script'}), 400
            # Push using the wire format that running clients understand:
            # old clients expect demo_mode (bool) + demo_sim_mode (str)
            # new clients handle both via apply_remote_settings
            _wire = {
                'false':     {'demo_mode': False, 'demo_sim_mode': 'off'},
                'simulated': {'demo_mode': True,  'demo_sim_mode': 'synthetic'},
                'script':    {'demo_mode': False, 'demo_sim_mode': 'script'},
            }
            push_payload.update(_wire[demo_mode])

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

    if demo_mode is None:
        msg = f'Alert rate updated for {queued} client(s)'
    else:
        labels = {'false': 'disabled', 'simulated': 'simulated', 'script': 'script-based'}
        msg = f'Demo mode set to {labels[demo_mode]} for {queued} client(s)'

    return jsonify({
        'status':  'ok',
        'queued':  queued,
        'message': msg,
        **({'demo_mode': demo_mode} if demo_mode is not None else {}),
    })
