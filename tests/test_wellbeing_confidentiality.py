import pytest

from app.models.concern import Category, Concern, Urgency
from app.models.user import Role
from app.services.concern_service import (
    check_concern_access,
    create_concern,
    get_admin_dashboard_metrics,
    get_concern_by_id,
    get_staff_queue,
)
from tests.conftest import login, logout


def test_wellbeing_confidentiality_server_enforcement(
    db,
    student_user,
    student_user_2,
    wellbeing_user,
    mentor_user,
    warden_user,
    dean_user,
    admin_user,
    client,
):
    """
    CRITICAL REQUIREMENT 7:
    Wellbeing concerns are visible ONLY to the student who raised them and authorised Wellbeing Staff.
    They must be hidden from all other staff, general listings, dashboards and admin counts.
    Enforce this on the server side, store minimal data, and add tests proving other roles cannot access them.
    """
    # 1. Student raises a confidential wellbeing concern
    wellbeing_concern = create_concern(
        student_id=student_user.id,
        category=Category.WELLBEING,
        title="Personal Health and Counseling Request",
        description="Confidential counseling inquiry regarding sleep and stress.",
        urgency=Urgency.HIGH,
    )
    assert wellbeing_concern.is_confidential is True
    assert wellbeing_concern.assigned_role == Role.WELLBEING_STAFF

    # 2. Student who raised it CAN access
    check_concern_access(wellbeing_concern, student_user)
    c_fetched = get_concern_by_id(wellbeing_concern.id, student_user)
    assert c_fetched.id == wellbeing_concern.id

    # 3. Authorised Wellbeing Staff CAN access
    check_concern_access(wellbeing_concern, wellbeing_user)
    c_fetched_wb = get_concern_by_id(wellbeing_concern.id, wellbeing_user)
    assert c_fetched_wb.id == wellbeing_concern.id

    # 4. Another student CANNOT access (Forbidden)
    with pytest.raises(PermissionError):
        check_concern_access(wellbeing_concern, student_user_2)

    # 5. Mentor CANNOT access (Forbidden)
    with pytest.raises(PermissionError):
        check_concern_access(wellbeing_concern, mentor_user)

    # 6. Warden CANNOT access (Forbidden)
    with pytest.raises(PermissionError):
        check_concern_access(wellbeing_concern, warden_user)

    # 7. Dean CANNOT access (Forbidden)
    with pytest.raises(PermissionError):
        check_concern_access(wellbeing_concern, dean_user)

    # 8. Admin CANNOT access (Forbidden)
    with pytest.raises(PermissionError):
        check_concern_access(wellbeing_concern, admin_user)

    # 9. HTTP Client route access verification:
    # 9a. Another student via HTTP -> 403 Forbidden
    login(client, student_user_2.email)
    resp = client.get(f"/student/concerns/{wellbeing_concern.id}")
    assert resp.status_code == 403
    logout(client)

    # 9b. Mentor via HTTP -> 403 Forbidden
    login(client, mentor_user.email)
    resp = client.get(f"/staff/concerns/{wellbeing_concern.id}")
    assert resp.status_code == 403
    logout(client)

    # 9c. Warden via HTTP -> 403 Forbidden
    login(client, warden_user.email)
    resp = client.get(f"/staff/concerns/{wellbeing_concern.id}")
    assert resp.status_code == 403
    logout(client)

    # 9d. Admin via HTTP -> 403 Forbidden
    login(client, admin_user.email)
    resp = client.get(f"/staff/concerns/{wellbeing_concern.id}")
    assert resp.status_code == 403
    logout(client)

    # 9e. Wellbeing Staff via HTTP -> 200 OK
    login(client, wellbeing_user.email)
    resp = client.get(f"/staff/concerns/{wellbeing_concern.id}")
    assert resp.status_code == 200
    assert b"Personal Health and Counseling Request" in resp.data
    logout(client)


def test_wellbeing_hidden_from_staff_queues_and_admin_counts(
    db, student_user, wellbeing_user, mentor_user, warden_user
):
    """
    Verify wellbeing concerns are completely hidden from non-wellbeing staff queues
    and excluded from admin content analytics.
    """
    # Create one Academic concern and one Wellbeing concern
    c_acad = create_concern(
        student_id=student_user.id,
        category=Category.ACADEMIC,
        title="Math Syllabus Question",
        description="Query about linear algebra.",
    )
    c_wellbeing = create_concern(
        student_id=student_user.id,
        category=Category.WELLBEING,
        title="Private Counseling",
        description="Private medical matter.",
    )

    # 1. Mentor's queue MUST NOT contain the wellbeing concern
    mentor_queue = get_staff_queue(staff_user=mentor_user)
    mentor_concern_ids = [c.id for c in mentor_queue]
    assert c_acad.id in mentor_concern_ids
    assert c_wellbeing.id not in mentor_concern_ids

    # 2. Warden's queue MUST NOT contain the wellbeing concern
    warden_queue = get_staff_queue(staff_user=warden_user)
    warden_concern_ids = [c.id for c in warden_queue]
    assert c_wellbeing.id not in warden_concern_ids

    # 3. Wellbeing staff's queue DOES contain the wellbeing concern
    wellbeing_queue = get_staff_queue(staff_user=wellbeing_user)
    wellbeing_concern_ids = [c.id for c in wellbeing_queue]
    assert c_wellbeing.id in wellbeing_concern_ids

    # 4. Admin dashboard metrics: Wellbeing concerns are excluded from content counts
    admin_metrics = get_admin_dashboard_metrics()
    assert admin_metrics["total_concerns"] == 1  # Only the non-confidential Academic concern!
    assert admin_metrics["category_counts"][Category.WELLBEING] == "Hidden (Confidential)"
    assert admin_metrics["category_counts"][Category.ACADEMIC] == 1
