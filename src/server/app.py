import json
import os
from flask import Flask
from .core.database import Database
from .models import load_pretrained_models


def create_app(testing=False):
    # Create Flask app in testing or production mode
    app = Flask(__name__)
    app.config['TESTING'] = testing

    #TODO check for first initalization, create database and tables if not exist.

    # Database default user setup
    db = Database()
    db.create_default_web_user()
    db.close()

    # Load pretrained models
    # svm_model, forest_model = load_pretrained_models()
    # pre trained models can be used to provide insight on client behaviour and generate alerts based on anomalous telemetry data.
    # This is a future enhancement and not critical for functionality.
    
    # Register API blueprints
    from .api import register_api_blueprints
    register_api_blueprints(app)
    return app


def load_config(config_path):
    # Load JSON configuration file
    if not os.path.exists(config_path):
        print(f"[!] Configuration file not found: {config_path}")
        return None
    with open(config_path) as f:
        return json.load(f)