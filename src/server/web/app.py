import os
import socket
from flask import Flask, render_template, redirect, session, url_for, request, jsonify, current_app
from dotenv import load_dotenv

from .templates.pre_renders import dashboard_prerender
from .templates.pre_renders import clients_prerender
from .templates.pre_renders import settings_prerender

from ..api import register_api_blueprints
from ..core.database import Database
from ..utils.deployer import ensure_bundle

load_dotenv()

# Initialize the Flask application
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.getenv('WEB_SECRET_KEY')

# Register API blueprints
register_api_blueprints(app)

# Create default web user on startup if it does not already exist
_db = Database()
_db.create_default_web_user()
_db.close()

# Build (or refresh) the deployable client bundle.
# SERVER_IP must be the externally reachable IP/hostname that deployed clients
# will use to reach this server.  Set it in your .env file.
_server_ip = os.getenv('SERVER_IP') or socket.gethostbyname(socket.gethostname())
_server_port = int(os.getenv('FLASK_PORT', 5000))
if not os.getenv('SERVER_IP'):
    print(
        f'[deployer] WARNING: SERVER_IP not set in environment — '
        f'using detected address {_server_ip!r}. '
        'Set SERVER_IP in your .env for reliable client deployments.'
    )
ensure_bundle(_server_ip, _server_port)

@app.route('/')
@app.route('/dashboard')
def Dashboard():
    if not session.get('user_id'):
        return redirect('/login')
    context = {
        'quickstats_html': dashboard_prerender.render_quickstats(),
        'recent_activity_html': dashboard_prerender.render_recent_activity(),
        'system_health_html': dashboard_prerender.render_system_health(),
        'network_status_html': dashboard_prerender.render_network_status(),
        'alerts_html': dashboard_prerender.render_alerts(),
    }
    return render_template(
        'Capcan-html-home.html',
        **context
    )

@app.route('/clients')
def Clients():
    if not session.get('user_id'):
        return redirect('/login')
    context = {
        'client_list_html': clients_prerender.render_client_list(),
        'client_details_html': clients_prerender.render_client_details(),
    }
    return render_template(
        'Capcan-html-clients.html',
        **context
    )

@app.route('/settings')
def Settings():
    if not session.get('user_id'):
        return redirect('/login')

    db = Database()
    try:
        current_user = db.get_web_user_by_id(session['user_id']) or {}
        user_role = current_user.get('role', 'read-only')
        users_list = db.get_all_web_users() if user_role == 'admin' else []
    finally:
        db.close()

    demo_mode = current_app.config.get('DEMO_MODE', False)

    context = {
        'current_user': current_user,
        'user_role': user_role,
        'users_list': users_list,
        'demo_mode': demo_mode,
        'account_settings_html': settings_prerender.render_account_settings(),
        'client_settings_html': settings_prerender.render_client_settings(),
        'configs_settings_html': settings_prerender.render_configs_settings(),
        'web_settings_html': settings_prerender.render_web_settings(),
        'demo_settings_html': settings_prerender.render_demo_settings() if demo_mode else '',
    }
    return render_template('Capcan-html-settings.html', **context)

@app.route('/login')
def Login():
    return render_template('Capcan-html-login.html')

@app.route('/register')
def Register():
    return render_template('Capcan-html-register.html')


@app.route('/api/demo/status')
def demo_status():
    """Return current demo mode availability and how many clients have it enabled."""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorised'}), 401

    db = Database()
    try:
        current_user = db.get_web_user_by_id(session['user_id']) or {}
        if current_user.get('role') != 'admin':
            return jsonify({'error': 'Admin only'}), 403

        client_ids = db.get_active_client_ids()
        demo_enabled_count = 0
        for cid in client_ids:
            effective = db.get_effective_settings(cid) or {}
            if effective.get('demo_mode') is True:
                demo_enabled_count += 1
    finally:
        db.close()

    return jsonify({
        'server_demo_mode': current_app.config.get('DEMO_MODE', False),
        'total_active_clients': len(client_ids),
        'demo_enabled_clients': demo_enabled_count,
    })


@app.route('/api/demo/push', methods=['POST'])
def demo_push():
    """Push demo_mode on/off to all active clients. Admin only."""
    if not session.get('user_id'):
        return jsonify({'error': 'Unauthorised'}), 401

    db = Database()
    try:
        current_user = db.get_web_user_by_id(session['user_id']) or {}
        if current_user.get('role') != 'admin':
            return jsonify({'error': 'Admin only'}), 403

        body = request.get_json(silent=True) or {}
        demo_mode_value = bool(body.get('demo_mode', False))

        client_ids = db.get_active_client_ids()
        if not client_ids:
            return jsonify({'status': 'ok', 'queued': 0, 'message': 'No active clients found'})

        queued = db.set_pending_config(client_ids, {'demo_mode': demo_mode_value})
    finally:
        db.close()

    return jsonify({
        'status': 'ok',
        'demo_mode': demo_mode_value,
        'queued': queued,
        'message': f'Demo mode {"enabled" if demo_mode_value else "disabled"} queued for {queued} client(s)',
    })


# if __name__ == '__main__':
    # app.run(debug=True)