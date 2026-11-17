from datetime import datetime, timedelta, timezone
import pytest

from app.models.concern import Category, ConcernStatus, Urgency
from app.models.routing import SystemSetting
from app.models.user import Role
from app.services.concern_service import (
    create_concern,
    escalate_concern,
    get_staff_queue,
)


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)



def test_escalation_chain_execution(db, student_user, mentor_user, coordinator_user):
    """Test staff escalating a concern along the configured chain."""
    concern = create_concern(
        student_id=student_user.id,
        category=Category.ACADEMIC,
        title="Complex Academic Issue",
        description="Requires deanery level review.",
        urgency=Urgency.HIGH,
    )
    assert concern.assigned_role == Role.MENTOR
    assert concern.status == ConcernStatus.SUBMITTED

    # Mentor escalates -> Configured chain: Mentor (Academic) -> Program Coordinator
    concern, next_role = escalate_concern(
        concern=concern,
        user=mentor_user,
        escalation_reason="Beyond mentor scope; curriculum change needed.",
    )

    assert next_role == Role.PROGRAM_COORDINATOR
    assert concern.assigned_role == Role.PROGRAM_COORDINATOR
    assert concern.status == ConcernStatus.ESCALATED
    assert "Escalated to Program Coordinator" in concern.timeline[-1].action


def test_escalation_requires_reason(student_user, mentor_user):
    """Test escalation requires non-empty reason."""
    concern = create_concern(
        student_id=student_user.id,
        category=Category.ACADEMIC,
        title="Title",
        description="Desc",
    )
    with pytest.raises(ValueError):
        escalate_concern(concern=concern, user=mentor_user, escalation_reason="   ")


def test_overdue_flag_calculation(db, student_user):
    """Test unacknowledged concerns past configurable threshold are flagged overdue."""
    threshold = SystemSetting.get_int("overdue_threshold_hours", 24)

    # 1. Recent concern (2 hours old) -> NOT overdue
    c_recent = create_concern(
        student_id=student_user.id,
        category=Category.ACADEMIC,
        title="Recent Concern",
        description="Just created.",
    )
    assert c_recent.is_overdue(threshold) is False

    # 2. Old unacknowledged concern (30 hours old) -> OVERDUE
    c_old = create_concern(
        student_id=student_user.id,
        category=Category.ACADEMIC,
        title="Old Concern",
        description="Submitted long ago.",
    )
    c_old.created_at = utc_now() - timedelta(hours=30)
    db.session.commit()

    assert c_old.is_overdue(threshold) is True

    # 3. Acknowledged concern is NOT overdue even if older than 24h
    c_old.status = ConcernStatus.ACKNOWLEDGED
    db.session.commit()
    assert c_old.is_overdue(threshold) is False


def test_staff_queue_sorted_by_urgency_and_age(db, student_user, mentor_user):
    """
    CRITICAL REQUIREMENT:
    Staff queue sorted by urgency (Urgent > High > Medium > Low) and age (oldest first).
    """
    # Create Low urgency concern 5 hours ago
    c_low = create_concern(
        student_id=student_user.id,
        category=Category.ACADEMIC,
        title="Low Concern",
        description="Low priority.",
        urgency=Urgency.LOW,
    )
    c_low.created_at = utc_now() - timedelta(hours=5)

    # Create Urgent concern 1 hour ago
    c_urgent = create_concern(
        student_id=student_user.id,
        category=Category.ACADEMIC,
        title="Urgent Concern",
        description="Urgent priority.",
        urgency=Urgency.URGENT,
    )
    c_urgent.created_at = utc_now() - timedelta(hours=1)

    # Create High concern 2 hours ago
    c_high = create_concern(
        student_id=student_user.id,
        category=Category.ACADEMIC,
        title="High Concern",
        description="High priority.",
        urgency=Urgency.HIGH,
    )
    c_high.created_at = utc_now() - timedelta(hours=2)

    db.session.commit()

    queue = get_staff_queue(staff_user=mentor_user)

    # Order must be Urgent -> High -> Low
    assert queue[0].id == c_urgent.id
    assert queue[1].id == c_high.id
    assert queue[2].id == c_low.id
