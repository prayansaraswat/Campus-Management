from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.blueprints.main import main_bp
from app.models.appointment import AvailabilitySlot
from app.models.concern import Category
from app.models.routing import RoutingRule, SystemSetting
from app.models.user import Role, User
from app.services.notification_service import (
    get_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)


@main_bp.route("/")
def index():
    """Home / landing page."""
    if current_user.is_authenticated:
        if current_user.is_student:
            return redirect(url_for("student.dashboard"))
        elif current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        else:
            return redirect(url_for("staff.dashboard"))

    campus_name = SystemSetting.get_value(
        "campus_name", "Bennett University"
    )
    return render_template("index.html", campus_name=campus_name)


@main_bp.route("/directory")
def directory():
    """
    'Who do I contact?' directory:
    Allows students to choose a concern category and immediately see the responsible role,
    the active staff members in that role, their cabin/office location, contact info,
    and their published availability slots.
    """
    selected_category = request.args.get("category", Category.ACADEMIC)

    categories = [
        Category.ACADEMIC,
        Category.EXAMINATION,
        Category.MESS,
        Category.RESIDENTIAL,
        Category.WELLBEING,
        Category.MAINTENANCE,
        Category.OTHER,
    ]

    maintenance_url = SystemSetting.get_value(
        "maintenance_portal_url", "https://maintenance.campus.edu"
    )

    is_maintenance = selected_category == Category.MAINTENANCE
    target_role = None
    staff_members = []
    slots_by_staff = {}

    if not is_maintenance:
        rule = RoutingRule.query.filter_by(
            category=selected_category, is_active=True
        ).first()
        if rule:
            target_role = rule.target_role
        else:
            # Fallbacks
            if selected_category == Category.WELLBEING:
                target_role = Role.WELLBEING_STAFF
            elif selected_category in [Category.MESS, Category.RESIDENTIAL]:
                target_role = Role.WARDEN
            elif selected_category == Category.EXAMINATION:
                target_role = Role.PROGRAM_COORDINATOR
            else:
                target_role = Role.MENTOR

        staff_members = (
            User.query.filter_by(role=target_role, is_active=True)
            .order_by(User.name.asc())
            .all()
        )

        # Retrieve available slots for these staff members
        for staff in staff_members:
            slots = (
                AvailabilitySlot.query.filter_by(
                    staff_id=staff.id, is_available=True
                )
                .order_by(
                    AvailabilitySlot.date.asc(), AvailabilitySlot.start_time.asc()
                )
                .all()
            )
            slots_by_staff[staff.id] = slots

    return render_template(
        "directory.html",
        categories=categories,
        selected_category=selected_category,
        is_maintenance=is_maintenance,
        maintenance_url=maintenance_url,
        target_role=target_role,
        staff_members=staff_members,
        slots_by_staff=slots_by_staff,
    )


@main_bp.route("/maintenance")
def maintenance():
    """Dedicated maintenance page directing students to the existing maintenance portal."""
    maintenance_url = SystemSetting.get_value(
        "maintenance_portal_url", "https://maintenance.campus.edu"
    )
    return render_template(
        "maintenance.html", maintenance_url=maintenance_url
    )


@main_bp.route("/notifications")
@login_required
def notifications():
    """View in-app notifications."""
    notifs = get_user_notifications(current_user.id, limit=50)
    return render_template("notifications.html", notifications=notifs)


@main_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id: int):
    """Mark a single notification as read."""
    mark_notification_read(notification_id, current_user.id)
    return redirect(request.referrer or url_for("main.notifications"))


@main_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def read_all_notifications():
    """Mark all notifications as read."""
    mark_all_notifications_read(current_user.id)
    flash("All notifications marked as read.", "info")
    return redirect(request.referrer or url_for("main.notifications"))
