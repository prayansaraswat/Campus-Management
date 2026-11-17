from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc)



class Role:
    """System user roles."""

    STUDENT = "Student"
    MENTOR = "Mentor"
    PROGRAM_COORDINATOR = "Program Coordinator"
    WARDEN = "Warden"
    HEAD_WARDEN = "Head Warden"
    DEAN_STUDENT_AFFAIRS = "Dean of Student Affairs"
    DEAN = "Dean"
    WELLBEING_STAFF = "Wellbeing/Health Staff"
    ADMIN = "Admin"

    ALL_ROLES = [
        STUDENT,
        MENTOR,
        PROGRAM_COORDINATOR,
        WARDEN,
        HEAD_WARDEN,
        DEAN_STUDENT_AFFAIRS,
        DEAN,
        WELLBEING_STAFF,
        ADMIN,
    ]

    STAFF_ROLES = [
        MENTOR,
        PROGRAM_COORDINATOR,
        WARDEN,
        HEAD_WARDEN,
        DEAN_STUDENT_AFFAIRS,
        DEAN,
        WELLBEING_STAFF,
    ]


class User(UserMixin, db.Model):
    """User account model supporting students, staff members, and administrators."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default=Role.STUDENT, index=True)
    department = db.Column(db.String(100), nullable=True)
    cabin_location = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    bio = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    concerns_raised = db.relationship(
        "Concern",
        foreign_keys="Concern.student_id",
        backref="student",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    concerns_assigned = db.relationship(
        "Concern",
        foreign_keys="Concern.assigned_to_user_id",
        backref="assigned_staff",
        lazy="dynamic",
    )
    availability_slots = db.relationship(
        "AvailabilitySlot",
        foreign_keys="AvailabilitySlot.staff_id",
        backref="staff",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    appointments_as_student = db.relationship(
        "Appointment",
        foreign_keys="Appointment.student_id",
        backref="student",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    appointments_as_staff = db.relationship(
        "Appointment",
        foreign_keys="Appointment.staff_id",
        backref="staff",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    notifications = db.relationship(
        "Notification",
        foreign_keys="Notification.user_id",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify given password against hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_student(self) -> bool:
        return self.role == Role.STUDENT

    @property
    def is_staff(self) -> bool:
        return self.role in Role.STAFF_ROLES

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_wellbeing_staff(self) -> bool:
        return self.role == Role.WELLBEING_STAFF

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
