import os
from flask import Flask, render_template, redirect, session, url_for
from dotenv import load_dotenv

from .templates.pre_renders import dashboard_prerender
from .templates.pre_renders import clients_prerender
from .templates.pre_renders import settings_prerender

from ..api import register_api_blueprints
from ..core.database import Database

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

@app.route('/')
@app.route('/dashboard')
def Dashboard():
    context = {
        'quickstats_html': dashboard_prerender.render_quickstats(),
        'recent_activity_html': dashboard_prerender.render_recent_activity(),
        'system_health_html': dashboard_prerender.render_system_health(),
        'network_status_html': dashboard_prerender.render_network_status(),
        'alerts_html': dashboard_prerender.render_alerts(),
    }
    if not session.get('user_id'):
        return redirect('/login')
    return render_template(
        'Capcan-html-home.html',
        **context
    )

@app.route('/clients')
def Clients():
    context = {
        'client_list_html': clients_prerender.render_client_list(),
        'client_details_html': clients_prerender.render_client_details(),
    }

    if not session.get('user_id'):
        return redirect('/login')
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

    context = {
        'current_user': current_user,
        'user_role': user_role,
        'users_list': users_list,
        'account_settings_html': settings_prerender.render_account_settings(),
        'client_settings_html': settings_prerender.render_client_settings(),
        'configs_settings_html': settings_prerender.render_configs_settings(),
        'web_settings_html': settings_prerender.render_web_settings(),
    }
    return render_template('Capcan-html-settings.html', **context)

@app.route('/login')
def Login():
    return render_template('Capcan-html-login.html')

@app.route('/register')
def Register():
    return render_template('Capcan-html-register.html')

# if __name__ == '__main__':
    # app.run(debug=True)