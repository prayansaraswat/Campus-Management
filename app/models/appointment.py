from datetime import datetime, timezone
from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AppointmentStatus:
    """Status lifecycle for staff-student appointments."""

    REQUESTED = "Requested"
    APPROVED = "Approved"
    DECLINED = "Declined"
    RESCHEDULED = "Rescheduled"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

    ALL_STATUSES = [
        REQUESTED,
        APPROVED,
        DECLINED,
        RESCHEDULED,
        COMPLETED,
        CANCELLED,
    ]


class AvailabilitySlot(db.Model):
    """Staff published availability slots for student appointments."""

    __tablename__ = "availability_slots"

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    location = db.Column(db.String(120), nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    appointments = db.relationship(
        "Appointment", backref="slot", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<AvailabilitySlot {self.staff_id} on {self.date} {self.start_time}-{self.end_time}>"


class Appointment(db.Model):
    """Student appointment booking and status."""

    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    staff_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    slot_id = db.Column(
        db.Integer,
        db.ForeignKey("availability_slots.id", ondelete="SET NULL"),
        nullable=True,
    )
    concern_id = db.Column(
        db.Integer, db.ForeignKey("concerns.id", ondelete="SET NULL"), nullable=True
    )
    purpose = db.Column(db.String(255), nullable=False)
    status = db.Column(
        db.String(30),
        nullable=False,
        default=AppointmentStatus.REQUESTED,
        index=True,
    )
    rescheduled_date = db.Column(db.Date, nullable=True)
    rescheduled_start_time = db.Column(db.Time, nullable=True)
    rescheduled_end_time = db.Column(db.Time, nullable=True)
    rescheduled_location = db.Column(db.String(120), nullable=True)
    staff_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    concern = db.relationship("Concern", backref="appointments")

    def __repr__(self) -> str:
        return f"<Appointment {self.id} [Student {self.student_id} with Staff {self.staff_id}: {self.status}]>"
