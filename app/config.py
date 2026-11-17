import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base application configuration."""

    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "dev-campus-support-portal-secret-key-2026"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # Application settings
    DEFAULT_OVERDUE_HOURS = int(os.environ.get("OVERDUE_THRESHOLD_HOURS", 24))
    DEFAULT_MAINTENANCE_URL = os.environ.get(
        "MAINTENANCE_PORTAL_URL", "https://maintenance.campus.edu"
    )
    CAMPUS_NAME = os.environ.get("CAMPUS_NAME", "Central University Campus")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'campus_portal.db'}"
    )


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False  # Allows streamlined automated test client requests


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
