def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "FlowAlchemy API"
    assert data["version"] == "0.1.0"
    assert data["status"] in ("ok", "degraded")
    assert "redis" in data
    assert "database" in data


def test_register_success(client, test_user):
    response = client.post("/api/auth/register", json=test_user)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user["email"]
    assert "id" in data
    assert "password" not in data


def test_register_duplicate_email(client, test_user):
    client.post("/api/auth/register", json=test_user)
    response = client.post("/api/auth/register", json=test_user)
    assert response.status_code == 400


def test_login_success(client, test_user):
    client.post("/api/auth/register", json=test_user)
    response = client.post("/api/auth/login", json=test_user)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, test_user):
    client.post("/api/auth/register", json=test_user)
    response = client.post(
        "/api/auth/login",
        json={"email": test_user["email"], "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "password"},
    )
    assert response.status_code == 401
