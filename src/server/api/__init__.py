from .client_endpoints import client_bp
from .alert_endpoints import alert_bp
from .login_endpoint import login_bp
from .register_endpoint import register_bp
 
def register_api_blueprints(app):
    app.register_blueprint(client_bp)
    app.register_blueprint(alert_bp)
    app.register_blueprint(login_bp)
    app.register_blueprint(register_bp)