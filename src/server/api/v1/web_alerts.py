from flask import Blueprint, request, jsonify, session

from ...core.database import Database

web_alerts_bp = Blueprint('web_alerts', __name__, url_prefix='/web/alerts')


def _require_session():
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorised'}), 401
    return None


def _get_session_role():
    """Return the role of the currently logged-in web user, or None."""
    if not session.get('user_id'):
        return None
    db = Database()
    try:
        user = db.get_web_user_by_id(session['user_id']) or {}
        return user.get('role', 'read-only')
    finally:
        db.close()


@web_alerts_bp.route('', methods=['GET'])
def web_alerts():
    err = _require_session()
    if err: return err
    db = Database()
    try:
        alerts = db.get_all_alerts(
            client_id=request.args.get('client_id'),
            severity=request.args.get('severity'),
            status=request.args.get('status'),
            event_type=request.args.get('event_type'),
            limit=request.args.get('limit', type=int, default=200),
        )
        for a in alerts:
            for k in ('created_at', 'acknowledged_at'):
                if a.get(k) and hasattr(a[k], 'isoformat'):
                    a[k] = a[k].isoformat() + 'Z'
        return jsonify({'alerts': alerts, 'returned': len(alerts)})
    finally:
        db.close()


@web_alerts_bp.route('/count', methods=['GET'])
def web_alerts_count():
    err = _require_session()
    if err: return err
    db = Database()
    try:
        count = db.get_unresolved_alert_count()
        return jsonify({'unresolved': count})
    finally:
        db.close()


@web_alerts_bp.route('/<alert_id>/acknowledge', methods=['POST'])
def web_acknowledge_alert(alert_id):
    err = _require_session()
    if err: return err
    role = _get_session_role()
    if role == 'read-only':
        return jsonify({'error': 'Read-only users cannot acknowledge alerts'}), 403
    db = Database()
    try:
        user = db.get_web_user_by_id(session['user_id']) or {}
        ok = db.acknowledge_alert(alert_id, acknowledged_by=user.get('username', 'admin'))
        if not ok:
            return jsonify({'error': 'Alert not found or already acknowledged'}), 404
        return jsonify({'status': 'acknowledged', 'alert_id': alert_id})
    finally:
        db.close()


@web_alerts_bp.route('/<alert_id>/resolve', methods=['POST'])
def web_resolve_alert(alert_id):
    err = _require_session()
    if err: return err
    role = _get_session_role()
    if role == 'read-only':
        return jsonify({'error': 'Read-only users cannot resolve alerts'}), 403
    db = Database()
    try:
        ok = db.resolve_alert(alert_id)
        if not ok:
            return jsonify({'error': 'Alert not found or already resolved'}), 404
        return jsonify({'status': 'resolved', 'alert_id': alert_id})
    finally:
        db.close()
