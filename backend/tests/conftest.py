import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.core.rate_limiter import rate_limiter

# Use SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test_flowalchemy.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_flowalchemy.db"):
        os.remove("./test_flowalchemy.db")


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state between tests (memory + best-effort Redis)."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_user(request):
    """Return a test user with a deterministic-but-unique email per test node."""
    email = f"user_{uuid.uuid5(uuid.NAMESPACE_DNS, request.node.name).hex[:8]}@test.com"
    return {"email": email, "password": "TestPass123"}


@pytest.fixture
def auth_headers(client, test_user):
    # Register
    client.post("/api/auth/register", json=test_user)
    # Login
    response = client.post("/api/auth/login", json=test_user)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_session():
    """Provide a clean database session for each test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
