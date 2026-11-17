from datetime import datetime, timezone
from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Notification(db.Model):
    """In-app notifications for status transitions, comments, and appointments."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utc_now, index=True)

    def __repr__(self) -> str:
        return f"<Notification {self.id} for user {self.user_id} - read={self.is_read}>"
