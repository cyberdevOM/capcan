from flask import Flask, render_template, url_for
import os, sys

sys.path.insert(0, os.path.dirname(__file__))

from templates.pre_renders import dashboard_prerender
from templates.pre_renders import clients_prerender
from templates.pre_renders import settings_prerender

# Initialize the Flask application
app = Flask(__name__, static_folder='static', template_folder='templates')

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
    return render_template(
        'Capcan-html-clients.html',
        **context
    )

@app.route('/settings')
def Settings():
    context = {
        'dashboard_settings_html': settings_prerender.render_dashboard_settings(),
        'appearance_settings_html': settings_prerender.render_appearance_settings(),
        'client_settings_html': settings_prerender.render_client_settings(),
        'security_settings_html': settings_prerender.render_security_settings(),
        'notification_settings_html': settings_prerender.render_notification_settings(),
    }

    return render_template(
        'Capcan-html-settings.html',
        **context
    )

@app.route('/login')
def Login():
    return render_template('Capcan-html-login.html')

@app.route('/register')
def Register():
    return render_template('Capcan-html-register.html')

# if __name__ == '__main__':
    # app.run(debug=True)