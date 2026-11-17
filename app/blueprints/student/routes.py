from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.blueprints.student import student_bp
from app.forms import AppointmentRequestForm, CommentForm, ConcernForm
from app.models.appointment import Appointment, AvailabilitySlot
from app.models.concern import Category, Concern, ConcernStatus
from app.models.routing import SystemSetting
from app.models.user import Role, User
from app.services.appointment_service import (
    get_student_appointments,
    request_appointment,
)
from app.services.concern_service import (
    add_concern_comment,
    create_concern,
    get_concern_by_id,
    get_student_concerns,
)
from app.utils.decorators import student_required


@student_bp.route("/dashboard")
@login_required
@student_required
def dashboard():
    """Student dashboard displaying current concerns, appointments, and quick actions."""
    concerns = get_student_concerns(current_user.id)
    appointments = get_student_appointments(current_user.id)

    active_concerns = [
        c for c in concerns if c.status in ConcernStatus.ACTIVE_STATUSES
    ]
    resolved_concerns = [
        c for c in concerns if c.status in [ConcernStatus.RESOLVED, ConcernStatus.CLOSED]
    ]

    return render_template(
        "student/dashboard.html",
        concerns=concerns[:5],
        all_concerns_count=len(concerns),
        active_concerns=active_concerns,
        resolved_concerns=resolved_concerns,
        appointments=appointments[:5],
        all_appointments_count=len(appointments),
    )


@student_bp.route("/concerns/new", methods=["GET", "POST"])
@login_required
@student_required
def submit_concern():
    """Submit a new student concern with automatic routing."""
    maintenance_url = SystemSetting.get_value(
        "maintenance_portal_url", "https://maintenance.campus.edu"
    )

    form = ConcernForm()
    if form.validate_on_submit():
        category = form.category.data

        # Explicit safeguard: redirect maintenance concerns to the external system
        if category == Category.MAINTENANCE:
            flash(
                "Maintenance and housekeeping issues are managed through our dedicated campus facility portal.",
                "info",
            )
            return redirect(url_for("main.maintenance"))

        try:
            concern = create_concern(
                student_id=current_user.id,
                category=category,
                title=form.title.data,
                description=form.description.data,
                urgency=form.urgency.data,
            )
            flash(
                f"Concern submitted successfully! Tracking ID: {concern.tracking_number}. "
                f"Auto-routed to {concern.assigned_role}.",
                "success",
            )
            return redirect(
                url_for("student.view_concern", concern_id=concern.id)
            )
        except ValueError as e:
            flash(str(e), "danger")

    return render_template(
        "student/submit_concern.html",
        form=form,
        maintenance_url=maintenance_url,
    )


@student_bp.route("/concerns/<int:concern_id>")
@login_required
def view_concern(concern_id: int):
    """View concern detail, progress timeline, and comments."""
    try:
        concern = get_concern_by_id(concern_id, current_user)
    except PermissionError:
        abort(403)

    comment_form = CommentForm()
    return render_template(
        "student/concern_detail.html",
        concern=concern,
        comment_form=comment_form,
    )


@student_bp.route("/concerns/<int:concern_id>/comment", methods=["POST"])
@login_required
def post_comment(concern_id: int):
    """Add a message/comment to a concern."""
    try:
        concern = get_concern_by_id(concern_id, current_user)
    except PermissionError:
        abort(403)

    form = CommentForm()
    if form.validate_on_submit():
        try:
            add_concern_comment(
                concern=concern,
                user=current_user,
                message=form.message.data,
                is_internal=False,
            )
            flash("Your message has been posted.", "success")
        except ValueError as e:
            flash(str(e), "danger")
    else:
        flash("Message cannot be empty.", "warning")

    return redirect(url_for("student.view_concern", concern_id=concern.id))


@student_bp.route("/appointments")
@login_required
@student_required
def appointments():
    """List all appointments booked by the student."""
    user_appointments = get_student_appointments(current_user.id)
    return render_template(
        "student/appointments.html", appointments=user_appointments
    )


@student_bp.route("/appointments/new", methods=["GET", "POST"])
@login_required
@student_required
def book_appointment():
    """Book an appointment with a staff member."""
    preselected_staff_id = request.args.get("staff_id", type=int)
    preselected_slot_id = request.args.get("slot_id", type=int)

    form = AppointmentRequestForm()

    # Populate staff choices
    staff_users = (
        User.query.filter(User.role.in_(Role.STAFF_ROLES), User.is_active == True)
        .order_by(User.name.asc())
        .all()
    )
    form.staff_id.choices = [(0, "-- Select Staff Member --")] + [
        (s.id, f"{s.name} ({s.role} - {s.department or 'Campus'})")
        for s in staff_users
    ]

    # Populate slot choices
    available_slots = (
        AvailabilitySlot.query.filter_by(is_available=True)
        .order_by(AvailabilitySlot.date.asc(), AvailabilitySlot.start_time.asc())
        .all()
    )
    form.slot_id.choices = [(0, "-- No specific slot (Ad-hoc request) --")] + [
        (
            slot.id,
            f"{slot.staff.name} - {slot.date.strftime('%a %b %d')} ({slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}) at {slot.location}",
        )
        for slot in available_slots
    ]

    # Populate student's active concerns
    student_concerns = (
        Concern.query.filter_by(student_id=current_user.id)
        .filter(Concern.status.in_(ConcernStatus.ACTIVE_STATUSES))
        .all()
    )
    form.concern_id.choices = [(0, "-- Not related to a specific concern --")] + [
        (c.id, f"#{c.tracking_number}: {c.title}") for c in student_concerns
    ]

    if request.method == "GET":
        if preselected_staff_id:
            form.staff_id.data = preselected_staff_id
        if preselected_slot_id:
            form.slot_id.data = preselected_slot_id

    if form.validate_on_submit():
        staff_id = form.staff_id.data
        if not staff_id or staff_id == 0:
            flash("Please choose a valid staff member.", "warning")
            return render_template(
                "student/book_appointment.html", form=form, staff_users=staff_users
            )

        slot_id = form.slot_id.data if form.slot_id.data != 0 else None
        concern_id = form.concern_id.data if form.concern_id.data != 0 else None

        try:
            appt = request_appointment(
                student_id=current_user.id,
                staff_id=staff_id,
                purpose=form.purpose.data,
                slot_id=slot_id,
                concern_id=concern_id,
            )
            flash(
                f"Appointment request submitted to {appt.staff.name}. Status: Requested.",
                "success",
            )
            return redirect(url_for("student.appointments"))
        except ValueError as e:
            flash(str(e), "danger")

    return render_template(
        "student/book_appointment.html",
        form=form,
        staff_users=staff_users,
        available_slots=available_slots,
    )
