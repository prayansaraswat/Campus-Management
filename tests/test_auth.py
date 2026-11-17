from app.models.user import Role, User
from tests.conftest import login, logout


def test_student_registration(client, db):
    """Test student registration creates active user with hashed password."""
    resp = client.post(
        "/auth/register",
        data={
            "name": "New Student",
            "email": "new_student@campus.edu",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "department": "Electrical Engineering",
            "phone": "555-1111",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    user = User.query.filter_by(email="new_student@campus.edu").first()
    assert user is not None
    assert user.name == "New Student"
    assert user.role == Role.STUDENT
    assert user.check_password("Password123!") is True
    assert user.password_hash != "Password123!"  # Hashed
    assert user.is_active is True


def test_duplicate_registration_prevented(client, student_user):
    """Test duplicate email registration is rejected."""
    resp = client.post(
        "/auth/register",
        data={
            "name": "Duplicate Student",
            "email": student_user.email,
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"already exists" in resp.data


def test_login_success_and_logout(client, student_user):
    """Test login and logout flow."""
    resp = login(client, student_user.email, "Password123!")
    assert resp.status_code == 200
    assert b"Welcome back, Test Student!" in resp.data

    # Logout
    resp = logout(client)
    assert resp.status_code == 200
    assert b"signed out successfully" in resp.data


def test_login_invalid_password(client, student_user):
    """Test login with bad credentials."""
    resp = login(client, student_user.email, "WrongPassword!")
    assert resp.status_code == 200
    assert b"Invalid email or password" in resp.data


def test_deactivated_user_blocked(client, student_user, db):
    """Test deactivated account is denied login."""
    student_user.is_active = False
    db.session.commit()

    resp = login(client, student_user.email, "Password123!")
    assert resp.status_code == 200
    assert b"account has been deactivated" in resp.data


def test_role_based_access_controls(client, student_user, mentor_user, admin_user):
    """Test student cannot access staff or admin routes, and staff cannot access admin routes."""
    # 1. Student attempts staff & admin routes
    login(client, student_user.email)
    resp = client.get("/staff/dashboard")
    assert resp.status_code == 403
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 403
    logout(client)

    # 2. Staff attempts admin routes
    login(client, mentor_user.email)
    resp = client.get("/staff/dashboard")
    assert resp.status_code == 200
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 403
    logout(client)

    # 3. Admin can access admin routes
    login(client, admin_user.email)
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 200
    logout(client)
