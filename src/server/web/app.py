from flask import Flask, render_template, url_for
import os, importlib.util

file_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), './templates/pre_renders/dashboard_prerender.py')
)

spec = importlib.util.spec_from_file_location("dashboard_prerender", file_path)
dashboard_preprender = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard_preprender)

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
    return render_template('Capcan-html-settings.html')

@app.route('/login')
def Login():
    return render_template('Capcan-html-login.html')

@app.route('/register')
def Register():
    return render_template('Capcan-html-register.html')

# if __name__ == '__main__':
    # app.run(debug=True)