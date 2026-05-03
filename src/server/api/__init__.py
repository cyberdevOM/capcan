from .v1 import v1_bp


def register_api_blueprints(app):
    app.register_blueprint(v1_bp)
