import re
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, generate_api_key, get_current_user
from app.core.rate_limiter import rate_limiter
from app.models.workflow import User
from app.schemas.workflow import UserCreate, UserLogin, UserResponse, TokenResponse, ApiKeyResponse, ProfileUpdate, PasswordChange

router = APIRouter()


def validate_password_strength(password: str) -> list[str]:
    """Validate password meets security requirements."""
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number")
    return errors


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_profile(data: ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.email:
        existing = db.query(User).filter(User.email == data.email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")
        current_user.email = data.email
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
def change_password(data: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/regenerate-api-key", response_model=ApiKeyResponse)
def regenerate_api_key(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    raw_key, key_hash, key_prefix = generate_api_key()
    current_user.api_key_hash = key_hash
    current_user.api_key_prefix = key_prefix
    db.commit()
    db.refresh(current_user)
    return ApiKeyResponse(
        id=current_user.id,
        email=current_user.email,
        plan=current_user.plan,
        api_key=raw_key,
        created_at=current_user.created_at,
        message="New API key generated. The old key is now invalid.",
    )


@router.post("/register", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    # Rate limit: 5 registrations per minute per IP
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"register:{client_ip}"
    if not rate_limiter.is_allowed(rate_key, limit=5, window=60):
        retry_after = rate_limiter.get_retry_after(rate_key, window=60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. Try again in {retry_after} seconds.",
        )

    # Validate password strength
    password_errors = validate_password_strength(user_data.password)
    if password_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Password does not meet security requirements",
                "errors": password_errors,
                "hint": "Use a mix of uppercase, lowercase, and numbers with at least 8 characters",
            },
        )

    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    raw_key, key_hash, key_prefix = generate_api_key()

    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        api_key_hash=key_hash,
        api_key_prefix=key_prefix,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Return the raw API key ONLY ONCE - user must save it
    return ApiKeyResponse(
        id=user.id,
        email=user.email,
        plan=user.plan,
        api_key=raw_key,
        created_at=user.created_at,
        message="Save this API key securely. It will not be shown again.",
    )


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    # Rate limit: 10 login attempts per minute per IP
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"login:{client_ip}"
    if not rate_limiter.is_allowed(rate_key, limit=10, window=60):
        retry_after = rate_limiter.get_retry_after(rate_key, window=60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Try again in {retry_after} seconds.",
        )

    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    access_token = create_access_token(data={"sub": user.email})
    return TokenResponse(access_token=access_token)
