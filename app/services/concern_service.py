from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from flask import abort
from sqlalchemy import case

from app.extensions import db
from app.models.concern import (
    Category,
    Concern,
    ConcernComment,
    ConcernStatus,
    ConcernTimeline,
    Urgency,
)
from app.models.routing import EscalationRule, RoutingRule, SystemSetting
from app.models.user import Role, User
from app.services.notification_service import create_notification, notify_role
from app.utils.helpers import generate_tracking_number


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_concern(
    student_id: int,
    category: str,
    title: str,
    description: str,
    urgency: str = Urgency.MEDIUM,
) -> Concern:
    """Validate and create a new student concern using database-driven routing."""
    # Enforce non-duplication of maintenance/housekeeping portal
    if category == Category.MAINTENANCE or "maintenance" in category.lower() or "housekeeping" in category.lower():
        raise ValueError(
            "Maintenance and housekeeping issues must be submitted via the dedicated Campus Maintenance Portal."
        )

    if category not in Category.SUBMITTABLE_CATEGORIES:
        raise ValueError(f"Invalid category: {category}")

    if urgency not in Urgency.ALL_URGENCIES:
        urgency = Urgency.MEDIUM

    # Determine initial route from database routing rules
    routing_rule = RoutingRule.query.filter_by(
        category=category, is_active=True
    ).first()
    if routing_rule:
        assigned_role = routing_rule.target_role
    else:
        # Dynamic fallback if not configured
        if category == Category.WELLBEING:
            assigned_role = Role.WELLBEING_STAFF
        elif category in [Category.MESS, Category.RESIDENTIAL]:
            assigned_role = Role.WARDEN
        elif category == Category.EXAMINATION:
            assigned_role = Role.PROGRAM_COORDINATOR
        else:
            assigned_role = Role.MENTOR

    # Confidentiality enforcement for wellbeing
    is_confidential = category == Category.WELLBEING

    # Attempt to assign to a specific active staff member with this role if available
    assigned_staff = User.query.filter_by(
        role=assigned_role, is_active=True
    ).first()
    assigned_to_user_id = assigned_staff.id if assigned_staff else None

    tracking_number = generate_tracking_number()

    concern = Concern(
        tracking_number=tracking_number,
        student_id=student_id,
        category=category,
        title=title.strip(),
        description=description.strip(),
        urgency=urgency,
        status=ConcernStatus.SUBMITTED,
        assigned_role=assigned_role,
        assigned_to_user_id=assigned_to_user_id,
        is_confidential=is_confidential,
    )
    db.session.add(concern)
    db.session.flush()

    # Create initial audit log entry
    timeline_entry = ConcernTimeline(
        concern_id=concern.id,
        action="Concern Submitted",
        details=f"Concern submitted and auto-routed to {assigned_role}.",
        performed_by_id=student_id,
    )
    db.session.add(timeline_entry)
    db.session.commit()

    # Notify staff responsible
    notify_role(
        role=assigned_role,
        title=f"New {urgency} Concern: {tracking_number}",
        message=f"A new concern '{title}' in {category} has been routed to your role.",
        link=f"/staff/concerns/{concern.id}",
    )

    return concern


def check_concern_access(concern: Concern, user: User) -> None:
    """Enforce strict server-side access controls, especially for confidential wellbeing concerns."""
    if concern.is_confidential:
        # Strictly visible ONLY to the student who raised it and Wellbeing Staff
        if user.id != concern.student_id and user.role != Role.WELLBEING_STAFF:
            raise PermissionError(
                "Access denied: Confidential wellbeing concern."
            )

    if user.is_student and concern.student_id != user.id:
        raise PermissionError(
            "Access denied: You can only access your own concerns."
        )


def get_concern_by_id(concern_id: int, user: User) -> Concern:
    """Retrieve concern by ID with authorization verification."""
    concern = db.session.get(Concern, concern_id)
    if not concern:
        abort(404)
    check_concern_access(concern, user)
    return concern


def update_concern_status(
    concern: Concern,
    new_status: str,
    user: User,
    comment_text: Optional[str] = None,
) -> Concern:
    """Transition concern status and append audit trail and notification."""
    if new_status not in ConcernStatus.ALL_STATUSES:
        raise ValueError(f"Invalid status: {new_status}")

    old_status = concern.status
    concern.status = new_status

    now = utc_now()
    if new_status == ConcernStatus.ACKNOWLEDGED and not concern.acknowledged_at:
        concern.acknowledged_at = now
    elif new_status == ConcernStatus.RESOLVED:
        concern.resolved_at = now
    elif new_status == ConcernStatus.CLOSED:
        concern.closed_at = now

    timeline = ConcernTimeline(
        concern_id=concern.id,
        action=f"Status changed to {new_status}",
        details=f"Changed from '{old_status}' to '{new_status}' by {user.name} ({user.role}).",
        performed_by_id=user.id,
    )
    db.session.add(timeline)

    if comment_text and comment_text.strip():
        comment = ConcernComment(
            concern_id=concern.id,
            author_id=user.id,
            message=comment_text.strip(),
            is_internal=False,
        )
        db.session.add(comment)

    db.session.commit()

    # Notify student
    create_notification(
        user_id=concern.student_id,
        title=f"Concern {concern.tracking_number} Status: {new_status}",
        message=f"Your concern '{concern.title}' status is now '{new_status}'.",
        link=f"/student/concerns/{concern.id}",
    )

    return concern


def escalate_concern(
    concern: Concern, user: User, escalation_reason: str
) -> Tuple[Concern, str]:
    """Escalate concern to the next role in the configured escalation chain."""
    if not escalation_reason or not escalation_reason.strip():
        raise ValueError("An escalation reason must be provided.")

    current_role = concern.assigned_role

    # Look up escalation rule in database
    rule = EscalationRule.query.filter_by(
        current_role=current_role, category=concern.category, is_active=True
    ).first()

    if not rule:
        rule = EscalationRule.query.filter_by(
            current_role=current_role, category=None, is_active=True
        ).first()

    if rule:
        next_role = rule.next_role
    else:
        # Fallback hierarchy if rule is missing
        fallback_chains = {
            Role.MENTOR: Role.PROGRAM_COORDINATOR,
            Role.PROGRAM_COORDINATOR: Role.DEAN,
            Role.WARDEN: Role.HEAD_WARDEN,
            Role.HEAD_WARDEN: Role.DEAN_STUDENT_AFFAIRS,
            Role.DEAN_STUDENT_AFFAIRS: Role.DEAN,
            Role.WELLBEING_STAFF: Role.DEAN_STUDENT_AFFAIRS,
        }
        next_role = fallback_chains.get(current_role, Role.DEAN)

    old_role = concern.assigned_role
    concern.assigned_role = next_role
    concern.status = ConcernStatus.ESCALATED

    # Re-assign to an active staff member in the new role if one exists
    new_staff = User.query.filter_by(role=next_role, is_active=True).first()
    concern.assigned_to_user_id = new_staff.id if new_staff else None

    # Log in timeline
    timeline = ConcernTimeline(
        concern_id=concern.id,
        action=f"Escalated to {next_role}",
        details=f"Escalated from {old_role} to {next_role}. Reason: {escalation_reason.strip()}",
        performed_by_id=user.id,
    )
    db.session.add(timeline)

    # Add comment for visibility
    comment = ConcernComment(
        concern_id=concern.id,
        author_id=user.id,
        message=f"[Escalation Note] Escalated to {next_role}: {escalation_reason.strip()}",
        is_internal=False,
    )
    db.session.add(comment)
    db.session.commit()

    # Notify student
    create_notification(
        user_id=concern.student_id,
        title=f"Concern {concern.tracking_number} Escalated",
        message=f"Your concern has been escalated to {next_role}. Reason: {escalation_reason.strip()}",
        link=f"/student/concerns/{concern.id}",
    )

    # Notify staff of the new role
    notify_role(
        role=next_role,
        title=f"Escalated Concern: {concern.tracking_number}",
        message=f"A concern has been escalated to {next_role}: {concern.title}",
        link=f"/staff/concerns/{concern.id}",
    )

    return concern, next_role


def add_concern_comment(
    concern: Concern, user: User, message: str, is_internal: bool = False
) -> ConcernComment:
    """Add a new comment to a concern and send notifications."""
    if not message or not message.strip():
        raise ValueError("Comment message cannot be blank.")

    comment = ConcernComment(
        concern_id=concern.id,
        author_id=user.id,
        message=message.strip(),
        is_internal=is_internal,
    )
    db.session.add(comment)

    timeline = ConcernTimeline(
        concern_id=concern.id,
        action="Comment Added",
        details=f"Comment added by {user.name} ({user.role}).",
        performed_by_id=user.id,
    )
    db.session.add(timeline)
    db.session.commit()

    # Notifications
    if user.id == concern.student_id:
        # Notify assigned staff or role
        if concern.assigned_to_user_id:
            create_notification(
                user_id=concern.assigned_to_user_id,
                title=f"New Comment on {concern.tracking_number}",
                message=f"Student {user.name} added a comment.",
                link=f"/staff/concerns/{concern.id}",
            )
        else:
            notify_role(
                role=concern.assigned_role,
                title=f"New Comment on {concern.tracking_number}",
                message=f"Student {user.name} added a comment on {concern.title}.",
                link=f"/staff/concerns/{concern.id}",
            )
    else:
        # Staff commented -> notify student
        create_notification(
            user_id=concern.student_id,
            title=f"Staff Response on {concern.tracking_number}",
            message=f"{user.name} ({user.role}) added a comment on your concern.",
            link=f"/student/concerns/{concern.id}",
        )

    return comment


def get_student_concerns(student_id: int) -> List[Concern]:
    """Retrieve all concerns submitted by a specific student."""
    return (
        Concern.query.filter_by(student_id=student_id)
        .order_by(Concern.created_at.desc())
        .all()
    )


def get_staff_queue(
    staff_user: User,
    category: Optional[str] = None,
    urgency: Optional[str] = None,
    status: Optional[str] = None,
    overdue_only: bool = False,
) -> List[Concern]:
    """
    Retrieve queue for staff member sorted by urgency and age.
    Enforces that non-wellbeing staff CANNOT see confidential wellbeing concerns.
    """
    query = Concern.query

    # Confidentiality filter: non-wellbeing staff MUST NOT see confidential concerns
    if staff_user.role != Role.WELLBEING_STAFF:
        query = query.filter(Concern.is_confidential == False)
    else:
        # Wellbeing staff sees wellbeing concerns
        query = query.filter(Concern.category == Category.WELLBEING)

    # Role filter: match assigned role or direct assignment
    if staff_user.role != Role.ADMIN:
        query = query.filter(
            (Concern.assigned_role == staff_user.role)
            | (Concern.assigned_to_user_id == staff_user.id)
        )

    # Optional filters
    if category:
        query = query.filter(Concern.category == category)
    if urgency:
        query = query.filter(Concern.urgency == urgency)
    if status:
        query = query.filter(Concern.status == status)

    # Urgency custom order: Urgent (1), High (2), Medium (3), Low (4)
    urgency_case = case(
        (Concern.urgency == Urgency.URGENT, 1),
        (Concern.urgency == Urgency.HIGH, 2),
        (Concern.urgency == Urgency.MEDIUM, 3),
        (Concern.urgency == Urgency.LOW, 4),
        else_=5,
    )

    # Sort by urgency first, then oldest age (created_at asc)
    concerns = query.order_by(urgency_case.asc(), Concern.created_at.asc()).all()

    if overdue_only:
        threshold = SystemSetting.get_int("overdue_threshold_hours", 24)
        concerns = [c for c in concerns if c.is_overdue(threshold)]

    return concerns


def get_admin_dashboard_metrics() -> Dict:
    """
    Compute aggregate counts for the Admin dashboard.
    CRITICAL: Excludes confidential wellbeing concerns completely from content counts.
    """
    # Exclude confidential concerns
    base_query = Concern.query.filter(Concern.is_confidential == False)

    total_concerns = base_query.count()
    active_concerns = base_query.filter(
        Concern.status.in_(ConcernStatus.ACTIVE_STATUSES)
    ).count()
    resolved_concerns = base_query.filter_by(
        status=ConcernStatus.RESOLVED
    ).count()
    closed_concerns = base_query.filter_by(
        status=ConcernStatus.CLOSED
    ).count()

    # Category breakdown (excluding confidential)
    category_counts = {}
    for cat in Category.SUBMITTABLE_CATEGORIES:
        if cat == Category.WELLBEING:
            # Explicitly omitted or marked zero/confidential for privacy
            category_counts[cat] = "Hidden (Confidential)"
        else:
            category_counts[cat] = base_query.filter_by(category=cat).count()

    # Status breakdown
    status_counts = {}
    for st in ConcernStatus.ALL_STATUSES:
        status_counts[st] = base_query.filter_by(status=st).count()

    # Overdue count
    threshold = SystemSetting.get_int("overdue_threshold_hours", 24)
    submitted = base_query.filter_by(status=ConcernStatus.SUBMITTED).all()
    overdue_count = sum(1 for c in submitted if c.is_overdue(threshold))

    total_users = User.query.count()
    total_students = User.query.filter_by(role=Role.STUDENT).count()
    total_staff = User.query.filter(User.role.in_(Role.STAFF_ROLES)).count()

    return {
        "total_concerns": total_concerns,
        "active_concerns": active_concerns,
        "resolved_concerns": resolved_concerns,
        "closed_concerns": closed_concerns,
        "overdue_count": overdue_count,
        "category_counts": category_counts,
        "status_counts": status_counts,
        "total_users": total_users,
        "total_students": total_students,
        "total_staff": total_staff,
        "overdue_threshold": threshold,
    }
