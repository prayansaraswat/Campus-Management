from datetime import date, datetime, time
from typing import Dict, List, Optional

from app.extensions import db
from app.models.appointment import (
    Appointment,
    AppointmentStatus,
    AvailabilitySlot,
)
from app.models.user import User
from app.services.notification_service import create_notification


def create_slot(
    staff_id: int,
    slot_date: date,
    start_time: time,
    end_time: time,
    location: str,
    notes: Optional[str] = None,
) -> AvailabilitySlot:
    """Create a new staff availability slot."""
    if start_time >= end_time:
        raise ValueError("Start time must be before end time.")

    slot = AvailabilitySlot(
        staff_id=staff_id,
        date=slot_date,
        start_time=start_time,
        end_time=end_time,
        location=location.strip(),
        notes=notes.strip() if notes else None,
        is_available=True,
    )
    db.session.add(slot)
    db.session.commit()
    return slot


def delete_slot(slot_id: int, staff_id: int) -> bool:
    """Delete an unbooked availability slot."""
    slot = AvailabilitySlot.query.filter_by(
        id=slot_id, staff_id=staff_id
    ).first()
    if not slot:
        return False
    # If there are active appointments on this slot, prevent deletion
    active_appointments = Appointment.query.filter_by(slot_id=slot.id).filter(
        Appointment.status.in_([AppointmentStatus.REQUESTED, AppointmentStatus.APPROVED])
    ).first()
    if active_appointments:
        raise ValueError("Cannot delete slot with active appointment.")
    db.session.delete(slot)
    db.session.commit()
    return True


def request_appointment(
    student_id: int,
    staff_id: int,
    purpose: str,
    slot_id: Optional[int] = None,
    concern_id: Optional[int] = None,
) -> Appointment:
    """Student requests an appointment with a staff member."""
    if not purpose or not purpose.strip():
        raise ValueError("Appointment purpose is required.")

    student = db.session.get(User, student_id)
    staff = db.session.get(User, staff_id)
    if not staff or not staff.is_staff:
        raise ValueError("Selected user is not a staff member.")

    slot = None
    if slot_id:
        slot = db.session.get(AvailabilitySlot, slot_id)
        if not slot or slot.staff_id != staff_id or not slot.is_available:
            raise ValueError("The selected slot is no longer available.")
        slot.is_available = False

    appointment = Appointment(
        student_id=student_id,
        staff_id=staff_id,
        slot_id=slot_id,
        concern_id=concern_id,
        purpose=purpose.strip(),
        status=AppointmentStatus.REQUESTED,
    )
    db.session.add(appointment)
    db.session.commit()

    # Notify staff
    time_str = f" on {slot.date} ({slot.start_time.strftime('%H:%M')})" if slot else ""
    create_notification(
        user_id=staff_id,
        title="New Appointment Request",
        message=f"{student.name} requested an appointment{time_str} regarding '{purpose}'.",
        link=f"/staff/appointments",
    )

    return appointment


def update_appointment_status(
    appointment: Appointment,
    staff_user: User,
    new_status: str,
    notes: Optional[str] = None,
    reschedule_date: Optional[date] = None,
    reschedule_start_time: Optional[time] = None,
    reschedule_end_time: Optional[time] = None,
    reschedule_location: Optional[str] = None,
) -> Appointment:
    """Staff updates appointment status (Approve, Decline, Reschedule, Complete)."""
    if new_status not in AppointmentStatus.ALL_STATUSES:
        raise ValueError(f"Invalid appointment status: {new_status}")

    appointment.status = new_status
    if notes:
        appointment.staff_notes = notes.strip()

    if new_status == AppointmentStatus.RESCHEDULED:
        if not reschedule_date or not reschedule_start_time or not reschedule_end_time:
            raise ValueError("Reschedule date and times must be provided.")
        appointment.rescheduled_date = reschedule_date
        appointment.rescheduled_start_time = reschedule_start_time
        appointment.rescheduled_end_time = reschedule_end_time
        appointment.rescheduled_location = (
            reschedule_location.strip() if reschedule_location else staff_user.cabin_location
        )
    elif new_status in [AppointmentStatus.DECLINED, AppointmentStatus.CANCELLED]:
        # Free up the slot if one was tied
        if appointment.slot:
            appointment.slot.is_available = True

    db.session.commit()

    # Notify student
    msg = f"Your appointment with {staff_user.name} was {new_status.lower()}."
    if notes:
        msg += f" Note: {notes}"
    if new_status == AppointmentStatus.RESCHEDULED:
        msg += f" Proposed time: {reschedule_date} at {reschedule_start_time.strftime('%H:%M')}."

    create_notification(
        user_id=appointment.student_id,
        title=f"Appointment {new_status}",
        message=msg,
        link="/student/appointments",
    )

    return appointment


def get_student_appointments(student_id: int) -> List[Appointment]:
    """List all appointments for a student."""
    return (
        Appointment.query.filter_by(student_id=student_id)
        .order_by(Appointment.created_at.desc())
        .all()
    )


def get_staff_appointments(staff_id: int) -> List[Appointment]:
    """List all appointments for a staff member."""
    return (
        Appointment.query.filter_by(staff_id=staff_id)
        .order_by(Appointment.created_at.desc())
        .all()
    )


def get_staff_slots(staff_id: int) -> List[AvailabilitySlot]:
    """List all published availability slots for a staff member."""
    return (
        AvailabilitySlot.query.filter_by(staff_id=staff_id)
        .order_by(AvailabilitySlot.date.asc(), AvailabilitySlot.start_time.asc())
        .all()
    )
