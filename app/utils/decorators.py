from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from app.models.user import Role


def roles_required(*allowed_roles):
    """Decorator requiring the logged-in user to have one of the specified roles."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def student_required(f):
    """Require user to be a Student."""
    return roles_required(Role.STUDENT)(f)


def staff_required(f):
    """Require user to have any recognized staff role."""
    return roles_required(*Role.STAFF_ROLES)(f)


def admin_required(f):
    """Require user to be an Administrator."""
    return roles_required(Role.ADMIN)(f)


def wellbeing_required(f):
    """Require user to be Wellbeing/Health Staff."""
    return roles_required(Role.WELLBEING_STAFF)(f)
