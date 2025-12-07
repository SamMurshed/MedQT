"""Test suite for API endpoints and authentication flows."""

import pytest
from bson import ObjectId


@pytest.mark.asyncio
async def test_middleware_redirects_unauthenticated(client):
    """
    Ensure that accessing protected endpoints without authentication
    redirects the user to the login page.
    """
    ac, _ = client
    response = await ac.get("/patient/dashboard", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert "/login" in response.headers["location"]


@pytest.mark.asyncio
async def test_login_page_loads(client):
    """
    Verify that the login page can be loaded successfully.
    """
    ac, _ = client
    response = await ac.get("/login")
    assert response.status_code == 200
    assert "Login" in response.text


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    """
    Check that submitting invalid login credentials redirects
    back to the login page with an error parameter.
    """
    ac, mock_db = client

    # simulate no user found
    mock_db["patients"].find_one.return_value = None

    response = await ac.post(
        "/login",
        data={
            "email": "doesnotexist@example.com",
            "password": "wrongpassword",
            "role": "patient",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login?error=invalid" in response.headers["location"]


@pytest.mark.asyncio
async def test_register_patient(client):
    """
    Test that a new patient can register successfully and receives
    the appropriate cookies and redirect.
    """
    ac, mock_db = client

    # simulate email not found
    mock_db["patients"].find_one.return_value = None

    new_id = ObjectId()
    mock_db["patients"].insert_one.return_value.inserted_id = new_id

    response = await ac.post(
        "/register/patient",
        data={
            "name": "John Test",
            "email": "testuser@example.com",
            "password": "secret123",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "/onboarding/symptoms"
    assert response.cookies.get("user_id") == str(new_id)
    assert response.cookies.get("role") == "patient"


@pytest.mark.asyncio
async def test_register_patient_duplicate_email(client):
    """
    Test that attempting to register with an existing email
    returns an error.
    """
    ac, mock_db = client

    mock_db["patients"].find_one.return_value = {"email": "dupe@example.com"}

    response = await ac.post(
        "/register/patient",
        data={"name": "Dupe", "email": "dupe@example.com", "password": "pass"},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "already registered" in response.text


@pytest.mark.asyncio
async def test_root_redirects_to_login(client):
    """
    Ensure that visiting the root URL redirects to the login page.
    """
    ac, _ = client
    res = await ac.get("/", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert res.headers["location"] == "/login"


@pytest.mark.asyncio
async def test_register_doctor_success(client):
    """
    Test that a new doctor can register successfully.
    """
    ac, mock_db = client

    mock_db["doctors"].find_one.return_value = None
    new_id = ObjectId()
    mock_db["doctors"].insert_one.return_value.inserted_id = new_id

    res = await ac.post(
        "/register/doctor",
        data={"name": "Doc", "email": "doc@example.com", "password": "abc123"},
        follow_redirects=False,
    )

    assert res.status_code == 302
    assert res.headers["location"] == "/doctor/dashboard"
    assert res.cookies.get("role") == "doctor"
    assert res.cookies.get("user_id") == str(new_id)


@pytest.mark.asyncio
async def test_register_doctor_duplicate(client):
    """
    Test that registering a doctor with an existing email returns an error.
    """
    ac, mock_db = client

    mock_db["doctors"].find_one.return_value = {"email": "doc@example.com"}

    res = await ac.post(
        "/register/doctor",
        data={"name": "Doc", "email": "doc@example.com", "password": "pass"},
    )

    assert res.status_code == 400
    assert "already registered" in res.text
