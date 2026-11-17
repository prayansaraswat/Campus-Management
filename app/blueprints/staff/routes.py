from datetime import datetime
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.blueprints.staff import staff_bp
from app.forms import (
    AppointmentActionForm,
    AvailabilitySlotForm,
    CommentForm,
    EscalationForm,
    StatusUpdateForm,
)
from app.models.appointment import Appointment, AppointmentStatus, AvailabilitySlot
from app.models.concern import Category, Concern, ConcernStatus, Urgency
from app.models.routing import EscalationRule, SystemSetting
from app.models.user import Role
from app.services.appointment_service import (
    create_slot,
    delete_slot,
    get_staff_appointments,
    get_staff_slots,
    update_appointment_status,
)
from app.services.concern_service import (
    add_concern_comment,
    escalate_concern,
    get_concern_by_id,
    get_staff_queue,
    update_concern_status,
)
from app.utils.decorators import staff_required


@staff_bp.route("/dashboard")
@login_required
@staff_required
def dashboard():
    """Staff dashboard showing queue sorted by urgency/age and pending appointments."""
    concerns = get_staff_queue(current_user)
    threshold = SystemSetting.get_int("overdue_threshold_hours", 24)

    # Key metrics
    urgent_count = sum(1 for c in concerns if c.urgency == Urgency.URGENT)
    overdue_count = sum(1 for c in concerns if c.is_overdue(threshold))
    in_progress_count = sum(
        1 for c in concerns if c.status == ConcernStatus.IN_PROGRESS
    )

    appointments = get_staff_appointments(current_user.id)
    pending_appts = [
        a for a in appointments if a.status == AppointmentStatus.REQUESTED
    ]

    return render_template(
        "staff/dashboard.html",
        concerns=concerns[:8],
        total_in_queue=len(concerns),
        urgent_count=urgent_count,
        overdue_count=overdue_count,
        in_progress_count=in_progress_count,
        pending_appointments=pending_appts,
        overdue_threshold=threshold,
    )


@staff_bp.route("/queue")
@login_required
@staff_required
def queue():
    """View entire assigned concern queue with multi-facet filters."""
    category = request.args.get("category")
    urgency = request.args.get("urgency")
    status = request.args.get("status")
    overdue_only = request.args.get("overdue_only") == "1"

    concerns = get_staff_queue(
        staff_user=current_user,
        category=category,
        urgency=urgency,
        status=status,
        overdue_only=overdue_only,
    )

    threshold = SystemSetting.get_int("overdue_threshold_hours", 24)

    # Categories selectable (hide wellbeing for non-wellbeing staff)
    if current_user.role == Role.WELLBEING_STAFF:
        available_categories = [Category.WELLBEING]
    else:
        available_categories = [
            c for c in Category.SUBMITTABLE_CATEGORIES if c != Category.WELLBEING
        ]

    return render_template(
        "staff/queue.html",
        concerns=concerns,
        categories=available_categories,
        urgenies=Urgency.ALL_URGENCIES,
        statuses=ConcernStatus.ALL_STATUSES,
        selected_category=category,
        selected_urgency=urgency,
        selected_status=status,
        overdue_only=overdue_only,
        overdue_threshold=threshold,
    )


@staff_bp.route("/concerns/<int:concern_id>")
@login_required
@staff_required
def view_concern(concern_id: int):
    """View detailed concern information with status update and escalation controls."""
    try:
        concern = get_concern_by_id(concern_id, current_user)
    except PermissionError:
        abort(403)

    status_form = StatusUpdateForm(status=concern.status)
    escalate_form = EscalationForm()
    comment_form = CommentForm()

    # Determine preview of next role in escalation chain
    escalation_rule = EscalationRule.query.filter_by(
        current_role=concern.assigned_role, category=concern.category, is_active=True
    ).first()
    if not escalation_rule:
        escalation_rule = EscalationRule.query.filter_by(
            current_role=concern.assigned_role, category=None, is_active=True
        ).first()

    next_role_preview = escalation_rule.next_role if escalation_rule else "Next Authority"
    threshold = SystemSetting.get_int("overdue_threshold_hours", 24)

    return render_template(
        "staff/concern_detail.html",
        concern=concern,
        status_form=status_form,
        escalate_form=escalate_form,
        comment_form=comment_form,
        next_role_preview=next_role_preview,
        overdue_threshold=threshold,
    )


@staff_bp.route("/concerns/<int:concern_id>/status", methods=["POST"])
@login_required
@staff_required
def update_status(concern_id: int):
    """Update concern lifecycle status."""
    try:
        concern = get_concern_by_id(concern_id, current_user)
    except PermissionError:
        abort(403)

    form = StatusUpdateForm()
    if form.validate_on_submit():
        new_status = form.status.data
        comment_note = form.comment.data
        try:
            update_concern_status(
                concern=concern,
                new_status=new_status,
                user=current_user,
                comment_text=comment_note,
            )
            flash(
                f"Concern {concern.tracking_number} updated to '{new_status}'.",
                "success",
            )
        except ValueError as e:
            flash(str(e), "danger")
    else:
        flash("Invalid status submission.", "danger")

    return redirect(url_for("staff.view_concern", concern_id=concern.id))


@staff_bp.route("/concerns/<int:concern_id>/escalate", methods=["POST"])
@login_required
@staff_required
def escalate(concern_id: int):
    """Escalate concern to the next role in chain."""
    try:
        concern = get_concern_by_id(concern_id, current_user)
    except PermissionError:
        abort(403)

    form = EscalationForm()
    if form.validate_on_submit():
        reason = form.reason.data
        try:
            concern, next_role = escalate_concern(
                concern=concern, user=current_user, escalation_reason=reason
            )
            flash(
                f"Concern {concern.tracking_number} successfully escalated to {next_role}.",
                "warning",
            )
            return redirect(url_for("staff.queue"))
        except ValueError as e:
            flash(str(e), "danger")
    else:
        flash("Please provide a valid escalation reason.", "danger")

    return redirect(url_for("staff.view_concern", concern_id=concern.id))


@staff_bp.route("/concerns/<int:concern_id>/comment", methods=["POST"])
@login_required
@staff_required
def post_comment(concern_id: int):
    """Post a staff response visible to student."""
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
            flash("Response posted for the student.", "success")
        except ValueError as e:
            flash(str(e), "danger")
    else:
        flash("Message cannot be empty.", "warning")

    return redirect(url_for("staff.view_concern", concern_id=concern.id))


@staff_bp.route("/availability", methods=["GET", "POST"])
@login_required
@staff_required
def availability():
    """Publish and manage staff cabin/office hours availability slots."""
    form = AvailabilitySlotForm()
    if form.validate_on_submit():
        try:
            create_slot(
                staff_id=current_user.id,
                slot_date=form.slot_date.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data,
                location=form.location.data,
                notes=form.notes.data,
            )
            flash("Availability slot published successfully.", "success")
            return redirect(url_for("staff.availability"))
        except ValueError as e:
            flash(str(e), "danger")

    # Set default location to user's cabin
    if request.method == "GET" and current_user.cabin_location:
        form.location.data = current_user.cabin_location

    slots = get_staff_slots(current_user.id)
    return render_template("staff/availability.html", form=form, slots=slots)


@staff_bp.route("/availability/<int:slot_id>/delete", methods=["POST"])
@login_required
@staff_required
def delete_availability_slot(slot_id: int):
    """Remove a published availability slot."""
    try:
        if delete_slot(slot_id, current_user.id):
            flash("Slot removed successfully.", "info")
        else:
            flash("Slot could not be removed.", "warning")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("staff.availability"))


@staff_bp.route("/appointments")
@login_required
@staff_required
def appointments():
    """Manage incoming student appointment requests."""
    staff_appts = get_staff_appointments(current_user.id)
    action_form = AppointmentActionForm()
    return render_template(
        "staff/appointments.html",
        appointments=staff_appts,
        action_form=action_form,
    )


@staff_bp.route("/appointments/<int:appointment_id>/action", methods=["POST"])
@login_required
@staff_required
def appointment_action(appointment_id: int):
    """Approve, decline, or reschedule an appointment."""
    appt = Appointment.query.filter_by(
        id=appointment_id, staff_id=current_user.id
    ).first_or_404()

    form = AppointmentActionForm()
    if form.validate_on_submit():
        action = form.action.data
        notes = form.notes.data
        reschedule_date = form.reschedule_date.data
        reschedule_start = form.reschedule_start_time.data
        reschedule_end = form.reschedule_end_time.data
        reschedule_loc = form.reschedule_location.data

        try:
            update_appointment_status(
                appointment=appt,
                staff_user=current_user,
                new_status=action,
                notes=notes,
                reschedule_date=reschedule_date,
                reschedule_start_time=reschedule_start,
                reschedule_end_time=reschedule_end,
                reschedule_location=reschedule_loc,
            )
            flash(f"Appointment marked as '{action}'.", "success")
        except ValueError as e:
            flash(str(e), "danger")
    else:
        flash("Could not update appointment. Check input details.", "danger")

    return redirect(url_for("staff.appointments"))
