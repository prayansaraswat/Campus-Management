from app.models.concern import Category, ConcernStatus, Urgency
from app.models.notification import Notification
from app.services.concern_service import (
    add_concern_comment,
    create_concern,
    update_concern_status,
)
from tests.conftest import login


def test_status_lifecycle_and_timestamps(db, student_user, mentor_user):
    """Test full status progression and timestamp recording."""
    concern = create_concern(
        student_id=student_user.id,
        category=Category.ACADEMIC,
        title="Schedule Clash",
        description="Exam dates conflict.",
        urgency=Urgency.HIGH,
    )
    assert concern.status == ConcernStatus.SUBMITTED
    assert concern.acknowledged_at is None
    assert len(concern.timeline) == 1
    assert concern.timeline[0].action == "Concern Submitted"

    # 1. Acknowledge
    update_concern_status(
        concern=concern,
        new_status=ConcernStatus.ACKNOWLEDGED,
        user=mentor_user,
        comment_text="I have noted this clash.",
    )
    assert concern.status == ConcernStatus.ACKNOWLEDGED
    assert concern.acknowledged_at is not None
    assert len(concern.timeline) == 2
    assert len(concern.comments) == 1
    assert concern.comments[0].message == "I have noted this clash."

    # Verify student received notification
    notif = Notification.query.filter_by(user_id=student_user.id).order_by(Notification.created_at.desc()).first()
    assert notif is not None
    assert "Acknowledged" in notif.title

    # 2. In Progress
    update_concern_status(
        concern=concern,
        new_status=ConcernStatus.IN_PROGRESS,
        user=mentor_user,
        comment_text="Coordinating with scheduler.",
    )
    assert concern.status == ConcernStatus.IN_PROGRESS

    # 3. Resolve
    update_concern_status(
        concern=concern,
        new_status=ConcernStatus.RESOLVED,
        user=mentor_user,
        comment_text="Exam rescheduled to Friday.",
    )
    assert concern.status == ConcernStatus.RESOLVED
    assert concern.resolved_at is not None

    # 4. Close
    update_concern_status(
        concern=concern,
        new_status=ConcernStatus.CLOSED,
        user=student_user,
        comment_text="Thank you, confirmed resolved.",
    )
    assert concern.status == ConcernStatus.CLOSED
    assert concern.closed_at is not None


def test_comments_dialogue_between_student_and_staff(db, student_user, mentor_user):
    """Test bi-directional communication between student and staff with audit trail."""
    concern = create_concern(
        student_id=student_user.id,
        category=Category.ACADEMIC,
        title="Grading Query",
        description="Question regarding Assignment 2 marks.",
    )

    # Mentor comments
    c1 = add_concern_comment(
        concern=concern,
        user=mentor_user,
        message="Please bring your submission rubric.",
    )
    assert c1.author_id == mentor_user.id
    assert not c1.is_internal

    # Student notified
    notif_student = Notification.query.filter_by(user_id=student_user.id).order_by(Notification.created_at.desc()).first()
    assert "Staff Response" in notif_student.title

    # Student replies
    c2 = add_concern_comment(
        concern=concern,
        user=student_user,
        message="I will bring the rubric at 2 PM.",
    )
    assert c2.author_id == student_user.id

    # Mentor notified
    notif_mentor = Notification.query.filter_by(user_id=mentor_user.id).order_by(Notification.created_at.desc()).first()
    assert "New Comment" in notif_mentor.title
