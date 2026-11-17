from typing import List, Optional
from app.extensions import db
from app.models.notification import Notification
from app.models.user import User


def create_notification(
    user_id: int, title: str, message: str, link: Optional[str] = None
) -> Notification:
    """Create a new in-app notification for a specific user."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        link=link,
        is_read=False,
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def notify_role(
    role: str, title: str, message: str, link: Optional[str] = None
) -> int:
    """Send notifications to all active staff members with a given role."""
    users = User.query.filter_by(role=role, is_active=True).all()
    count = 0
    for u in users:
        notif = Notification(
            user_id=u.id,
            title=title,
            message=message,
            link=link,
            is_read=False,
        )
        db.session.add(notif)
        count += 1
    if count > 0:
        db.session.commit()
    return count


def get_user_notifications(user_id: int, limit: int = 20) -> List[Notification]:
    """Retrieve recent notifications for a user."""
    return (
        Notification.query.filter_by(user_id=user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def get_unread_count(user_id: int) -> int:
    """Count unread notifications for a user."""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def mark_notification_read(notification_id: int, user_id: int) -> bool:
    """Mark a specific notification as read."""
    notif = Notification.query.filter_by(
        id=notification_id, user_id=user_id
    ).first()
    if notif:
        notif.is_read = True
        db.session.commit()
        return True
    return False


def mark_all_notifications_read(user_id: int) -> int:
    """Mark all unread notifications for a user as read."""
    unread = Notification.query.filter_by(user_id=user_id, is_read=False).all()
    count = len(unread)
    for n in unread:
        n.is_read = True
    db.session.commit()
    return count
