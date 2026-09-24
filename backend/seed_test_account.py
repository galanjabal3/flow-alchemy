"""Seed script to create a hardcoded test account for E2E testing.

Usage:
    cd backend
    python seed_test_account.py

Creates:
    Email: test@flowalchemy.dev
    Password: Test1234
"""

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.workflow import User

TEST_EMAIL = "test@flowalchemy.dev"
TEST_PASSWORD = "Test1234"


def seed():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == TEST_EMAIL).first()
        if existing:
            print(f"Test account already exists: {TEST_EMAIL}")
            return

        user = User(
            email=TEST_EMAIL,
            password_hash=hash_password(TEST_PASSWORD),
            api_key_hash="",
            api_key_prefix="sk_test",
        )
        db.add(user)
        db.commit()
        print(f"Test account created: {TEST_EMAIL} / {TEST_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
