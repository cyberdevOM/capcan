"""
api/v1/__init__.py

All v1 API endpoints are nested under a single `v1_bp` Blueprint with the
prefix /api/v1.  Sub-blueprints declare only their own sub-path, making the
version prefix a single source of truth here.

To add a v2, create src/server/api/v2/ with an identical structure and register
v2_bp alongside v1_bp in src/server/api/__init__.py.
"""

from flask import Blueprint

from .auth_endpoints import auth_bp
from .alert_endpoints import alert_bp
from .client_endpoints import client_bp
from .telemetry_endpoints import telemetry_bp
from .web_alerts import web_alerts_bp
from .web_dashboard import web_dashboard_bp
from .demo_endpoints import demo_bp

v1_bp = Blueprint('v1', __name__, url_prefix='/api/v1')

v1_bp.register_blueprint(auth_bp)
v1_bp.register_blueprint(alert_bp)
v1_bp.register_blueprint(client_bp)
v1_bp.register_blueprint(telemetry_bp)
v1_bp.register_blueprint(web_alerts_bp)
v1_bp.register_blueprint(web_dashboard_bp)
v1_bp.register_blueprint(demo_bp)
