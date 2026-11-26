from sqlalchemy import select

from app.models import User

PASSWORD = "TestPass123!"

def get_token(client, email, password=PASSWORD):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

def test_login_success(test_context):
    client, _, _ = test_context

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "resident1@test.local",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]

def test_login_wrong_password_returns_401(test_context):
    client, _, _ = test_context

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "resident1@test.local",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith(
        "application/problem+json"
    )

def test_current_user_without_token_returns_401(test_context):
    client, _, _ = test_context

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["status"] == 401

def test_current_user_returns_role(test_context):
    client, _, _ = test_context
    token = get_token(client, "resident1@test.local")

    response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["email"] == "resident1@test.local"
    assert response.json()["role"] == "resident"

def test_request_list_requires_authentication(test_context):
    client, _, _ = test_context

    response = client.get("/api/v1/requests")

    assert response.status_code == 401

def test_resident_sees_only_own_requests_and_pagination(test_context):
    client, _, _ = test_context
    token = get_token(client, "resident1@test.local")

    response = client.get(
        "/api/v1/requests?page=1&page_size=1",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["page_size"] == 1
    assert len(body["items"]) == 1

def test_dispatcher_sees_all_requests(test_context):
    client, _, _ = test_context
    token = get_token(client, "dispatcher@test.local")

    response = client.get(
        "/api/v1/requests",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3

def test_create_request_returns_201_and_location(test_context):
    client, _, _ = test_context
    token = get_token(client, "resident1@test.local")

    response = client.post(
        "/api/v1/requests",
        headers=auth_headers(token),
        json={
            "request_type": "Электрика",
            "description": "Не работает выключатель в комнате",
            "priority": "high",
        },
    )

    assert response.status_code == 201
    assert response.headers["location"].startswith("/api/v1/requests/")
    assert response.json()["status"] == "new"

def test_invalid_request_returns_422_problem_details(test_context):
    client, _, _ = test_context
    token = get_token(client, "resident1@test.local")

    response = client.post(
        "/api/v1/requests",
        headers=auth_headers(token),
        json={
            "request_type": "X",
            "description": "Коротко",
            "priority": "urgent",
        },
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith(
        "application/problem+json"
    )
    assert response.json()["status"] == 422

def test_get_missing_request_returns_404(test_context):
    client, _, _ = test_context
    token = get_token(client, "dispatcher@test.local")

    response = client.get("/api/v1/requests/999999",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
    assert response.json()["status"] == 404

def test_resident_cannot_read_another_residents_request(test_context):
    client, _, ids = test_context
    token = get_token(client, "resident1@test.local")

    response = client.get(
        f"/api/v1/requests/{ids['request2']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 403

def test_resident_cannot_change_request_status(test_context):
    client, _, ids = test_context
    token = get_token(client, "resident1@test.local")

    response = client.patch(
        f"/api/v1/requests/{ids['request1']}",
        headers=auth_headers(token),
        json={"status": "completed"},
    )

    assert response.status_code == 403

def test_master_sees_only_assigned_requests(test_context):
    client, _, _ = test_context
    token = get_token(client, "master@test.local")

    response = client.get(
        "/api/v1/requests",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "assigned"

def test_resident_cannot_access_analytics(test_context):
    client, _, _ = test_context
    token = get_token(client, "resident1@test.local")

    response = client.get(
        "/api/v1/analytics/dashboard",
        headers=auth_headers(token),
    )

    assert response.status_code == 403

def test_duplicate_registration_returns_409(test_context):
    client, _, ids = test_context
    token = get_token(client, "dispatcher@test.local")

    response = client.post(
        "/api/v1/auth/register",
        headers=auth_headers(token),
        json={
            "full_name": "Повторный пользователь",
            "email": "resident1@test.local",
            "password": "AnotherPass123!",
            "apartment_id": ids["apartment1"],
        },
    )

    assert response.status_code == 409
    assert response.headers["content-type"].startswith(
        "application/problem+json"
    )

def test_registration_stores_password_hash(test_context):
    client, session_factory, ids = test_context
    email = "newresident@test.local"
    raw_password = "FreshPass123!"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Новый Жилец",
            "email": email,
            "password": raw_password,
            "apartment_id": ids["apartment1"],
        },
    )

    assert response.status_code == 201

    with session_factory() as db:
        user = db.scalar(select(User).where(User.email == email))

    assert user is not None
    assert user.password_hash != raw_password
    assert user.password_hash.startswith("$argon2")

def test_openapi_contains_api_routes(test_context):
    client, _, _ = test_context

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]

    assert "/api/v1/auth/login" in paths
    assert "/api/v1/requests" in paths
    assert "/api/v1/analytics/dashboard" in paths
    assert "/api/v1/reports/house-month.xlsx" in paths
    assert "/api/v1/reports/overdue.pdf" in paths
