from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.blueprints.auth import auth_bp
from app.extensions import db
from app.forms import LoginForm, RegisterForm
from app.models.user import Role, User


def get_redirect_for_role(role: str) -> str:
    """Return dashboard URL endpoint for a given role."""
    if role == Role.STUDENT:
        return url_for("student.dashboard")
    elif role == Role.ADMIN:
        return url_for("admin.dashboard")
    else:
        return url_for("staff.dashboard")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(get_redirect_for_role(current_user.role))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash(
                    "Your account has been deactivated. Please contact an administrator.",
                    "danger",
                )
                return render_template("auth/login.html", form=form)

            login_user(user)
            flash(f"Welcome back, {user.name}!", "success")

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(get_redirect_for_role(user.role))
        else:
            flash("Invalid email or password. Please check your credentials.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Allow students to self-register an account."""
    if current_user.is_authenticated:
        return redirect(get_redirect_for_role(current_user.role))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account with this email address already exists.", "warning")
            return render_template("auth/register.html", form=form)

        user = User(
            name=form.name.data.strip(),
            email=email,
            role=Role.STUDENT,
            department=form.department.data.strip() if form.department.data else None,
            phone=form.phone.data.strip() if form.phone.data else None,
            is_active=True,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout")
def logout():
    """Sign the user out."""
    logout_user()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("auth.login"))
