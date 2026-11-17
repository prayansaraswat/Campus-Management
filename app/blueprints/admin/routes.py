from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.blueprints.admin import admin_bp
from app.extensions import db
from app.forms import (
    EscalationRuleForm,
    RoutingRuleForm,
    SystemSettingsForm,
    UserEditForm,
)
from app.models.routing import EscalationRule, RoutingRule, SystemSetting
from app.models.user import Role, User
from app.services.concern_service import get_admin_dashboard_metrics
from app.utils.decorators import admin_required


@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    """Admin dashboard with high-level system overview and privacy-preserving metrics."""
    metrics = get_admin_dashboard_metrics()
    routing_rules_count = RoutingRule.query.count()
    escalation_rules_count = EscalationRule.query.count()

    return render_template(
        "admin/dashboard.html",
        metrics=metrics,
        routing_rules_count=routing_rules_count,
        escalation_rules_count=escalation_rules_count,
    )


@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
@admin_required
def users():
    """Manage user accounts, roles, and status."""
    role_filter = request.args.get("role")
    query = User.query

    if role_filter:
        query = query.filter_by(role=role_filter)

    all_users = query.order_by(User.role.asc(), User.name.asc()).all()
    return render_template(
        "admin/users.html",
        users=all_users,
        roles=Role.ALL_ROLES,
        selected_role=role_filter,
    )


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id: int):
    """Edit user role, department, cabin location, or toggle active status."""
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        user.name = form.name.data.strip()
        user.role = form.role.data
        user.department = form.department.data.strip() if form.department.data else None
        user.cabin_location = (
            form.cabin_location.data.strip() if form.cabin_location.data else None
        )
        user.phone = form.phone.data.strip() if form.phone.data else None
        user.is_active = form.is_active.data

        db.session.commit()
        flash(f"User {user.email} updated successfully.", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin/user_edit.html", form=form, user=user)


@admin_bp.route("/routing-rules", methods=["GET", "POST"])
@login_required
@admin_required
def routing_rules():
    """Manage dynamic routing table from categories to responsible roles."""
    form = RoutingRuleForm()

    if form.validate_on_submit():
        category = form.category.data.strip()
        existing = RoutingRule.query.filter_by(category=category).first()

        if existing:
            existing.target_role = form.target_role.data
            existing.description = form.description.data.strip() if form.description.data else None
            existing.is_active = form.is_active.data
            db.session.commit()
            flash(f"Updated routing rule for '{category}'.", "success")
        else:
            rule = RoutingRule(
                category=category,
                target_role=form.target_role.data,
                description=form.description.data.strip() if form.description.data else None,
                is_active=form.is_active.data,
            )
            db.session.add(rule)
            db.session.commit()
            flash(f"Created new routing rule for '{category}'.", "success")

        return redirect(url_for("admin.routing_rules"))

    rules = RoutingRule.query.order_by(RoutingRule.category.asc()).all()
    return render_template("admin/routing_rules.html", form=form, rules=rules)


@admin_bp.route("/routing-rules/<int:rule_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_routing_rule(rule_id: int):
    """Delete a routing rule."""
    rule = RoutingRule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()
    flash(f"Deleted routing rule for '{rule.category}'.", "info")
    return redirect(url_for("admin.routing_rules"))


@admin_bp.route("/escalation-rules", methods=["GET", "POST"])
@login_required
@admin_required
def escalation_rules():
    """Manage configurable escalation chains."""
    form = EscalationRuleForm()

    if form.validate_on_submit():
        category = form.category.data.strip() if form.category.data else None
        rule = EscalationRule(
            category=category,
            current_role=form.current_role.data,
            next_role=form.next_role.data,
            order_level=form.order_level.data,
            description=form.description.data.strip() if form.description.data else None,
            is_active=form.is_active.data,
        )
        db.session.add(rule)
        db.session.commit()
        flash("New escalation rule created.", "success")
        return redirect(url_for("admin.escalation_rules"))

    rules = EscalationRule.query.order_by(
        EscalationRule.current_role.asc(), EscalationRule.order_level.asc()
    ).all()
    return render_template(
        "admin/escalation_rules.html", form=form, rules=rules
    )


@admin_bp.route("/escalation-rules/<int:rule_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_escalation_rule(rule_id: int):
    """Delete an escalation rule."""
    rule = EscalationRule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()
    flash("Deleted escalation rule.", "info")
    return redirect(url_for("admin.escalation_rules"))


@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
@admin_required
def settings():
    """Manage dynamic system parameters such as overdue threshold and external maintenance URL."""
    form = SystemSettingsForm()

    if request.method == "GET":
        form.overdue_threshold_hours.data = SystemSetting.get_int(
            "overdue_threshold_hours", 24
        )
        form.maintenance_portal_url.data = SystemSetting.get_value(
            "maintenance_portal_url", "https://maintenance.campus.edu"
        )
        form.campus_name.data = SystemSetting.get_value(
            "campus_name", "Bennett University"
        )

    if form.validate_on_submit():
        SystemSetting.set_value(
            "overdue_threshold_hours",
            str(form.overdue_threshold_hours.data),
            "Hours unacknowledged before flagged overdue",
        )
        SystemSetting.set_value(
            "maintenance_portal_url",
            form.maintenance_portal_url.data.strip(),
            "External maintenance portal link",
        )
        SystemSetting.set_value(
            "campus_name",
            form.campus_name.data.strip(),
            "Campus institution display name",
        )
        flash("System settings saved successfully.", "success")
        return redirect(url_for("admin.settings"))

    return render_template("admin/settings.html", form=form)
