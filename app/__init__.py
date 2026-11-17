import os
from flask import Flask, render_template
from flask_login import current_user

from app.config import config_by_name
from app.extensions import csrf, db, login_manager
from app.models.appointment import AppointmentStatus
from app.models.concern import Category, ConcernStatus, Urgency
from app.models.routing import SystemSetting
from app.models.user import Role, User
from app.services.notification_service import get_unread_count
from app.utils.helpers import time_ago


def create_app(config_name: str = None) -> Flask:
    """Application factory for the Campus Student Support and Concern Portal."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_obj)

    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    # Register Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.student import student_bp
    from app.blueprints.staff import staff_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)

    # Global context processor
    @app.context_processor
    def inject_portal_globals():
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = get_unread_count(current_user.id)

        return {
            "unread_notifications_count": unread_count,
            "campus_name": SystemSetting.get_value(
                "campus_name", "Central University Campus"
            ),
            "maintenance_portal_url": SystemSetting.get_value(
                "maintenance_portal_url", "https://maintenance.campus.edu"
            ),
            "Role": Role,
            "Category": Category,
            "Urgency": Urgency,
            "ConcernStatus": ConcernStatus,
            "AppointmentStatus": AppointmentStatus,
        }

    # Custom template filters
    @app.template_filter("timeago")
    def timeago_filter(dt):
        return time_ago(dt)

    @app.template_filter("date_fmt")
    def date_filter(d, fmt="%b %d, %Y"):
        return d.strftime(fmt) if d else ""

    @app.template_filter("time_fmt")
    def time_filter(t, fmt="%H:%M"):
        return t.strftime(fmt) if t else ""

    # Error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return (
            render_template(
                "error.html",
                status_code=403,
                title="Access Forbidden",
                message="You do not have permission to view or manage this resource. "
                "Confidential wellbeing records are strictly restricted.",
            ),
            403,
        )

    @app.errorhandler(404)
    def not_found_error(error):
        return (
            render_template(
                "error.html",
                status_code=404,
                title="Resource Not Found",
                message="The requested page or record could not be found.",
            ),
            404,
        )

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return (
            render_template(
                "error.html",
                status_code=500,
                title="System Error",
                message="An unexpected server error occurred. Please try again shortly.",
            ),
            500,
        )

    return app
