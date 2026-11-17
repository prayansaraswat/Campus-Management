from datetime import datetime, timezone
from app.extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class RoutingRule(db.Model):
    """Database routing table mapping concern categories to initial staff roles."""

    __tablename__ = "routing_rules"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), unique=True, nullable=False, index=True)
    target_role = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    def __repr__(self) -> str:
        return f"<RoutingRule {self.category} -> {self.target_role}>"


class EscalationRule(db.Model):
    """Configurable escalation paths specifying next-level roles."""

    __tablename__ = "escalation_rules"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=True, index=True)
    current_role = db.Column(db.String(50), nullable=False, index=True)
    next_role = db.Column(db.String(50), nullable=False)
    order_level = db.Column(db.Integer, default=1, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self) -> str:
        cat_str = f" [{self.category}]" if self.category else ""
        return f"<EscalationRule{cat_str} {self.current_role} -> {self.next_role}>"


class SystemSetting(db.Model):
    """Dynamic key-value system settings editable by Admin."""

    __tablename__ = "system_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False, index=True)
    value = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    @classmethod
    def get_value(cls, key: str, default: str = "") -> str:
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def get_int(cls, key: str, default: int = 0) -> int:
        val = cls.get_value(key)
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    @classmethod
    def set_value(cls, key: str, value: str, description: str = None) -> "SystemSetting":
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key, value=str(value), description=description)
            db.session.add(setting)
        else:
            setting.value = str(value)
            if description:
                setting.description = description
        db.session.commit()
        return setting

    def __repr__(self) -> str:
        return f"<SystemSetting {self.key}={self.value}>"
