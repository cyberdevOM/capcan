from flask import Blueprint, jsonify, session

from ...web.templates.pre_renders import dashboard_prerender
from ...web.templates.pre_renders.dashboard_prerender import _is_online, _humanize_time
from ...core.database import Database

web_dashboard_bp = Blueprint('web_dashboard', __name__, url_prefix='/web/dashboard')


@web_dashboard_bp.route('/tiles', methods=['GET'])
def dashboard_tiles():
    """Return rendered HTML for all dashboard tiles (used by live polling)."""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorised'}), 401
    return jsonify({
        'quickstats':      str(dashboard_prerender.render_quickstats()),
        'recent_activity': str(dashboard_prerender.render_recent_activity()),
        'system_health':   str(dashboard_prerender.render_system_health()),
        'network_status':  str(dashboard_prerender.render_network_status()),
        'alerts':          str(dashboard_prerender.render_alerts()),
    })


@web_dashboard_bp.route('/clients/status', methods=['GET'])
def clients_status():
    """Return JSON list of all clients with online status and last-seen string."""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorised'}), 401
    db = Database()
    try:
        clients = db.get_all_clients_with_status()
    finally:
        db.close()
    result = []
    for c in clients:
        last_seen = c.get('last_seen')
        result.append({
            'client_id': c['client_id'],
            'is_online': _is_online(last_seen),
            'last_seen': _humanize_time(last_seen),
        })
    return jsonify({'clients': result}), 200
