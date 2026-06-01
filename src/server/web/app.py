import os
import socket
from flask import Flask, render_template, redirect, session, url_for, request, jsonify, current_app
from dotenv import load_dotenv

from .templates.pre_renders import dashboard_prerender
from .templates.pre_renders import clients_prerender
from .templates.pre_renders import settings_prerender

from ..api import register_api_blueprints
from ..core.database import Database
from ..utils.deployer import ensure_bundle  # noqa: F401 — re-exported for __main__

load_dotenv()

# Initialize the Flask application
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.getenv('WEB_SECRET_KEY')

# Register API blueprints
register_api_blueprints(app)

# Create default web user on startup if it does not already exist
db = Database()
db.create_default_web_user()
db.close()

# Build (or refresh) the deployable client bundle.
# SERVER_IP must be the externally reachable IP/hostname that deployed clients
# will use to reach this server.  Set it in your .env file.
server_ip = os.getenv('SERVER_IP') or socket.gethostbyname(socket.gethostname())
server_port = int(os.getenv('FLASK_PORT', 5000))
if not os.getenv('SERVER_IP'):
    print(
        f'[INFO] WARNING: SERVER_IP not set in environment — using detected address {server_ip!r}.\n'
        f'[INFO] Set SERVER_IP in your .env for reliable client deployments.'
    )
# ensure_bundle is called from __main__.py after the --demo flag is parsed,
# so demo_mode is correctly forwarded to the build script.

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
    db = Database()
    try:
        current_user = db.get_web_user_by_id(session['user_id'])
    finally:
        db.close()
    if current_user is None:
        session.clear()
        return redirect('/login')
    user_role = current_user.get('role', 'read-only')
    client_id = request.args.get('client_id')
    context = {
        'client_list_html': clients_prerender.render_client_list(user_role),
        'client_details_html': clients_prerender.render_client_details(client_id, user_role),
        'user_role': user_role,
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
        current_user = db.get_web_user_by_id(session['user_id'])
        users_list = db.get_all_web_users() if current_user and current_user.get('role') in ('admin', 'super-admin') else []
    finally:
        db.close()

    if current_user is None:
        session.clear()
        return redirect('/login')

    user_role = current_user.get('role', 'read-only')

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


@app.route('/alerts')
def Alerts():
    if not session.get('user_id'):
        return redirect(url_for('Login'))
    db = Database()
    try:
        current_user = db.get_web_user_by_id(session['user_id'])
    finally:
        db.close()
    if current_user is None:
        session.clear()
        return redirect(url_for('Login'))
    user_role = current_user.get('role', 'read-only')
    selected_id = request.args.get('selected', '')
    return render_template('Capcan-html-alerts.html', preselected_alert=selected_id, user_role=user_role)


# if __name__ == '__main__':
    # app.run(debug=True)
