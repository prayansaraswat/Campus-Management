import pytest
from app import create_app
from app.extensions import db as _db
from app.models.routing import EscalationRule, RoutingRule, SystemSetting
from app.models.user import Role, User


@pytest.fixture
def app():
    """Create and configure a clean Flask test application."""
    test_app = create_app("testing")
    with test_app.app_context():
        _db.create_all()

        # Seed base settings
        SystemSetting.set_value("overdue_threshold_hours", "24")
        SystemSetting.set_value(
            "maintenance_portal_url", "https://maintenance.campus.edu"
        )
        SystemSetting.set_value("campus_name", "Test University")

        # Seed standard routing rules
        routes = [
            RoutingRule(category="Academic", target_role=Role.MENTOR),
            RoutingRule(category="Examination/Results", target_role=Role.PROGRAM_COORDINATOR),
            RoutingRule(category="Mess", target_role=Role.WARDEN),
            RoutingRule(category="Residential", target_role=Role.WARDEN),
            RoutingRule(category="Wellbeing", target_role=Role.WELLBEING_STAFF),
            RoutingRule(category="Other", target_role=Role.DEAN_STUDENT_AFFAIRS),
        ]
        _db.session.add_all(routes)

        # Seed escalation rules
        escalations = [
            EscalationRule(
                current_role=Role.MENTOR,
                next_role=Role.PROGRAM_COORDINATOR,
                category="Academic",
                order_level=1,
            ),
            EscalationRule(
                current_role=Role.PROGRAM_COORDINATOR,
                next_role=Role.DEAN,
                category=None,
                order_level=2,
            ),
            EscalationRule(
                current_role=Role.WARDEN,
                next_role=Role.HEAD_WARDEN,
                category=None,
                order_level=1,
            ),
            EscalationRule(
                current_role=Role.HEAD_WARDEN,
                next_role=Role.DEAN_STUDENT_AFFAIRS,
                category=None,
                order_level=2,
            ),
        ]
        _db.session.add_all(escalations)
        _db.session.commit()

        yield test_app

        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def db(app):
    """Database instance."""
    return _db


@pytest.fixture
def student_user(db):
    """Student test user."""
    user = User(
        name="Test Student",
        email="test_student@campus.edu",
        role=Role.STUDENT,
        department="Computer Science",
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def student_user_2(db):
    """Second student test user for cross-user isolation verification."""
    user = User(
        name="Other Student",
        email="other_student@campus.edu",
        role=Role.STUDENT,
        department="Physics",
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def mentor_user(db):
    """Mentor test user."""
    user = User(
        name="Prof. Mentor",
        email="mentor_test@campus.edu",
        role=Role.MENTOR,
        department="Computer Science",
        cabin_location="Cabin 101",
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def coordinator_user(db):
    """Program Coordinator test user."""
    user = User(
        name="Dr. Coordinator",
        email="coordinator_test@campus.edu",
        role=Role.PROGRAM_COORDINATOR,
        cabin_location="Cabin 202",
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def warden_user(db):
    """Warden test user."""
    user = User(
        name="Warden Smith",
        email="warden_test@campus.edu",
        role=Role.WARDEN,
        cabin_location="Hostel Office",
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def dean_user(db):
    """Dean test user."""
    user = User(
        name="Dean Evans",
        email="dean_test@campus.edu",
        role=Role.DEAN,
        cabin_location="Dean Suite",
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def wellbeing_user(db):
    """Wellbeing & Health Staff test user."""
    user = User(
        name="Dr. Counselor",
        email="wellbeing_test@campus.edu",
        role=Role.WELLBEING_STAFF,
        cabin_location="Health Center Suite 3",
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def admin_user(db):
    """Administrator test user."""
    user = User(
        name="Admin User",
        email="admin_test@campus.edu",
        role=Role.ADMIN,
    )
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


def login(client, email, password="Password123!"):
    """Helper to log in a user."""
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def logout(client):
    """Helper to log out current user."""
    return client.get("/auth/logout", follow_redirects=True)
