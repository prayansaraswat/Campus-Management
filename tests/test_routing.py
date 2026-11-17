import pytest
from app.models.concern import Category, Concern, Urgency
from app.models.routing import RoutingRule
from app.models.user import Role
from app.services.concern_service import create_concern
from tests.conftest import login


def test_database_driven_routing(db, student_user, mentor_user, warden_user):
    """Test concerns auto-route to correct roles using the database routing table."""
    # 1. Academic concern -> routed to Mentor according to RoutingRule in DB
    c_acad = create_concern(
        student_id=student_user.id,
        category=Category.ACADEMIC,
        title="Elective Registration Problem",
        description="Cannot register for elective course CS401.",
        urgency=Urgency.HIGH,
    )
    assert c_acad.assigned_role == Role.MENTOR
    assert c_acad.is_confidential is False

    # 2. Mess concern -> routed to Warden
    c_mess = create_concern(
        student_id=student_user.id,
        category=Category.MESS,
        title="Mess food quality feedback",
        description="Hostel dining hall runs out of food early.",
        urgency=Urgency.MEDIUM,
    )
    assert c_mess.assigned_role == Role.WARDEN


def test_admin_can_modify_routing_in_database(db, student_user, coordinator_user):
    """
    CRITICAL REQUIREMENT: Routes must NOT be hardcoded.
    Prove that updating the database routing table changes where new concerns route.
    """
    # Find Academic routing rule and change target_role to Program Coordinator
    rule = RoutingRule.query.filter_by(category=Category.ACADEMIC).first()
    rule.target_role = Role.PROGRAM_COORDINATOR
    db.session.commit()

    # Now create a new academic concern -> MUST route to Program Coordinator!
    c_new = create_concern(
        student_id=student_user.id,
        category=Category.ACADEMIC,
        title="Academic Syllabus Change",
        description="Query about syllabus revision.",
    )
    assert c_new.assigned_role == Role.PROGRAM_COORDINATOR


def test_maintenance_category_blocked_from_ticket_creation(db, student_user, client):
    """
    CRITICAL REQUIREMENT:
    The campus has a separate maintenance portal; this portal must NOT duplicate it.
    It should only link out.
    """
    # 1. Service layer blocks creation
    with pytest.raises(ValueError) as excinfo:
        create_concern(
            student_id=student_user.id,
            category=Category.MAINTENANCE,
            title="Broken hostel door handle",
            description="Room door handle is broken.",
        )
    assert "maintenance" in str(excinfo.value).lower()

    # Verify no concern was created
    assert Concern.query.count() == 0

    # 2. UI submission redirects to maintenance portal
    login(client, student_user.email)
    resp = client.post(
        "/student/concerns/new",
        data={
            "category": Category.MAINTENANCE,
            "title": "Broken window hinge",
            "description": "Hostel room window latch broken.",
            "urgency": "Low",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Maintenance and housekeeping issues are managed through our dedicated campus facility portal" in resp.data
    assert b"Campus Maintenance & Housekeeping" in resp.data
    assert Concern.query.count() == 0


def test_invalid_category_rejected(student_user):
    """Test unknown category raises validation error."""
    with pytest.raises(ValueError):
        create_concern(
            student_id=student_user.id,
            category="NonExistentCategory",
            title="Test Title",
            description="Test Description",
        )
