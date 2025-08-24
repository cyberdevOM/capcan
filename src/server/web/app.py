from flask import Flask, render_template, url_for
import os, importlib.util

# Import the dashboard pre-rendering module
file_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), './templates/pre_renders/dashboard_prerender.py')
)
spec = importlib.util.spec_from_file_location("dashboard_prerender", file_path)
dashboard_preprender = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard_preprender)

# Import the settings pre-rendering module
file_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), './templates/pre_renders/settings_prerender.py')
)
spec = importlib.util.spec_from_file_location("settings_prerender", file_path)
settings_preprender = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings_preprender)

# Initialize the Flask application
app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
@app.route('/dashboard')
def Dashboard():
    context = {
        'quickstats_html': dashboard_preprender.render_quickstats(),
        'recent_activity_html': dashboard_preprender.render_recent_activity(),
        'system_health_html': dashboard_preprender.render_system_health(),
        'network_status_html': dashboard_preprender.render_network_status(),
        'alerts_html': dashboard_preprender.render_alerts(),
    }

    return render_template(
        'Capcan-html-home.html',
        **context
    )

@app.route('/clients')
def Clients():
    return render_template(
        'Capcan-html-clients.html', 
        clients=dashboard_preprender.export_client_list()
    )

@app.route('/settings')
def Settings():
    context = {
        'dashboard_settings_html': settings_preprender.render_dashboard_settings(),
        'appearance_settings_html': settings_preprender.render_appearance_settings(),
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