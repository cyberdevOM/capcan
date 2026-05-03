from flask import Blueprint, jsonify, session

from ...web.templates.pre_renders import dashboard_prerender

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
