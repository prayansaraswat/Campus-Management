from datetime import date, time, timedelta

from app.models.appointment import AppointmentStatus, AvailabilitySlot
from app.models.notification import Notification
from app.services.appointment_service import (
    create_slot,
    request_appointment,
    update_appointment_status,
)


def test_appointment_booking_and_approval_workflow(db, student_user, mentor_user):
    """Test full cycle: publish slot -> student requests -> staff approves."""
    # 1. Mentor publishes slot
    tomorrow = date.today() + timedelta(days=1)
    slot = create_slot(
        staff_id=mentor_user.id,
        slot_date=tomorrow,
        start_time=time(10, 0),
        end_time=time(11, 0),
        location="Cabin 101",
        notes="Bring project report",
    )
    assert slot.is_available is True

    # 2. Student requests appointment
    appt = request_appointment(
        student_id=student_user.id,
        staff_id=mentor_user.id,
        slot_id=slot.id,
        purpose="Project discussion",
    )
    assert appt.status == AppointmentStatus.REQUESTED
    # Slot is marked unavailable to prevent double-booking
    assert slot.is_available is False

    # Staff notified
    notif_staff = Notification.query.filter_by(user_id=mentor_user.id).order_by(Notification.created_at.desc()).first()
    assert "Appointment Request" in notif_staff.title

    # 3. Staff approves
    update_appointment_status(
        appointment=appt,
        staff_user=mentor_user,
        new_status=AppointmentStatus.APPROVED,
        notes="Confirmed. See you tomorrow.",
    )
    assert appt.status == AppointmentStatus.APPROVED
    assert appt.staff_notes == "Confirmed. See you tomorrow."

    # Student notified
    notif_student = Notification.query.filter_by(user_id=student_user.id).order_by(Notification.created_at.desc()).first()
    assert "Approved" in notif_student.title


def test_appointment_decline_releases_slot(db, student_user, mentor_user):
    """Test declining an appointment frees the slot for other students."""
    tomorrow = date.today() + timedelta(days=1)
    slot = create_slot(
        staff_id=mentor_user.id,
        slot_date=tomorrow,
        start_time=time(14, 0),
        end_time=time(15, 0),
        location="Cabin 101",
    )
    appt = request_appointment(
        student_id=student_user.id,
        staff_id=mentor_user.id,
        slot_id=slot.id,
        purpose="Advising",
    )
    assert slot.is_available is False

    # Decline
    update_appointment_status(
        appointment=appt,
        staff_user=mentor_user,
        new_status=AppointmentStatus.DECLINED,
        notes="Unavailable due to emergency faculty meeting.",
    )
    assert appt.status == AppointmentStatus.DECLINED
    # Slot is re-opened!
    assert slot.is_available is True


def test_appointment_reschedule(db, student_user, mentor_user):
    """Test staff proposing rescheduled date and time."""
    appt = request_appointment(
        student_id=student_user.id,
        staff_id=mentor_user.id,
        purpose="Curriculum review",
    )

    new_date = date.today() + timedelta(days=3)
    update_appointment_status(
        appointment=appt,
        staff_user=mentor_user,
        new_status=AppointmentStatus.RESCHEDULED,
        notes="Rescheduled due to conference travel.",
        reschedule_date=new_date,
        reschedule_start_time=time(16, 0),
        reschedule_end_time=time(17, 0),
        reschedule_location="Cabin 101",
    )

    assert appt.status == AppointmentStatus.RESCHEDULED
    assert appt.rescheduled_date == new_date
    assert appt.rescheduled_start_time == time(16, 0)
