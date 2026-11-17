from datetime import datetime, timezone
from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Category:
    """Standard categories for student concerns."""

    ACADEMIC = "Academic"
    EXAMINATION = "Examination/Results"
    MESS = "Mess"
    RESIDENTIAL = "Residential"
    WELLBEING = "Wellbeing"
    OTHER = "Other"
    MAINTENANCE = "Maintenance/Housekeeping"

    SUBMITTABLE_CATEGORIES = [
        ACADEMIC,
        EXAMINATION,
        MESS,
        RESIDENTIAL,
        WELLBEING,
        OTHER,
    ]


class Urgency:
    """Urgency levels for concerns."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"

    ALL_URGENCIES = [LOW, MEDIUM, HIGH, URGENT]
    URGENCY_ORDER = {URGENT: 1, HIGH: 2, MEDIUM: 3, LOW: 4}


class ConcernStatus:
    """Status lifecycle for concerns."""

    SUBMITTED = "Submitted"
    ACKNOWLEDGED = "Acknowledged"
    IN_PROGRESS = "In Progress"
    ESCALATED = "Escalated"
    RESOLVED = "Resolved"
    CLOSED = "Closed"

    ALL_STATUSES = [
        SUBMITTED,
        ACKNOWLEDGED,
        IN_PROGRESS,
        ESCALATED,
        RESOLVED,
        CLOSED,
    ]

    ACTIVE_STATUSES = [SUBMITTED, ACKNOWLEDGED, IN_PROGRESS, ESCALATED]


class Concern(db.Model):
    """Primary student concern model."""

    __tablename__ = "concerns"

    id = db.Column(db.Integer, primary_key=True)
    tracking_number = db.Column(db.String(24), unique=True, nullable=False, index=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    urgency = db.Column(
        db.String(20), nullable=False, default=Urgency.MEDIUM, index=True
    )
    status = db.Column(
        db.String(30), nullable=False, default=ConcernStatus.SUBMITTED, index=True
    )
    assigned_role = db.Column(db.String(50), nullable=False, index=True)
    assigned_to_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_confidential = db.Column(
        db.Boolean, default=False, nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, default=utc_now, index=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    timeline = db.relationship(
        "ConcernTimeline",
        backref="concern",
        cascade="all, delete-orphan",
        order_by="ConcernTimeline.created_at.asc()",
    )
    comments = db.relationship(
        "ConcernComment",
        backref="concern",
        cascade="all, delete-orphan",
        order_by="ConcernComment.created_at.asc()",
    )

    def is_overdue(self, threshold_hours: int = 24) -> bool:
        """Return True if concern is unacknowledged past the overdue threshold."""
        if self.status != ConcernStatus.SUBMITTED:
            return False
        elapsed_seconds = (utc_now() - self.created_at).total_seconds()
        return elapsed_seconds > (threshold_hours * 3600)

    @property
    def age_hours(self) -> int:
        """Elapsed hours since creation."""
        return int((utc_now() - self.created_at).total_seconds() // 3600)

    @property
    def urgency_rank(self) -> int:
        """Numeric rank for sorting (1=Urgent, 4=Low)."""
        return Urgency.URGENCY_ORDER.get(self.urgency, 99)

    def __repr__(self) -> str:
        return f"<Concern {self.tracking_number} [{self.category} / {self.status}]>"


class ConcernTimeline(db.Model):
    """Audit log entry capturing state transitions and actions for a concern."""

    __tablename__ = "concern_timeline"

    id = db.Column(db.Integer, primary_key=True)
    concern_id = db.Column(
        db.Integer, db.ForeignKey("concerns.id", ondelete="CASCADE"), nullable=False
    )
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    performed_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=utc_now)

    performer = db.relationship("User", foreign_keys=[performed_by_id])

    def __repr__(self) -> str:
        return f"<ConcernTimeline {self.concern_id}: {self.action}>"


class ConcernComment(db.Model):
    """Comments on concerns visible to both staff and student."""

    __tablename__ = "concern_comments"

    id = db.Column(db.Integer, primary_key=True)
    concern_id = db.Column(
        db.Integer, db.ForeignKey("concerns.id", ondelete="CASCADE"), nullable=False
    )
    author_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    message = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    author = db.relationship("User", foreign_keys=[author_id])

    def __repr__(self) -> str:
        return f"<ConcernComment {self.concern_id} by user {self.author_id}>"
