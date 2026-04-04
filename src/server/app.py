import json
import os
from flask import Flask


def create_app(testing=False):
    # Create Flask app in testing or production mode
    app = Flask(__name__)
    app.config['TESTING'] = testing
    
    # Register API blueprints
    from .api.client_endpoints import client_bp
    from .api.alert_endpoints import alert_bp
    app.register_blueprint(client_bp)
    app.register_blueprint(alert_bp)
    
    return app


def load_config(config_path):
    # Load JSON configuration file
    if not os.path.exists(config_path):
        print(f"[!] Configuration file not found: {config_path}")
        return None
    with open(config_path) as f:
        return json.load(f)