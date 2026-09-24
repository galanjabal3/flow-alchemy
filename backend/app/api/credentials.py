"""Credentials management endpoints."""

import re
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.core.encryption import encrypt_value, decrypt_value
from app.models.workflow import User, Credential

router = APIRouter()


class CredentialType(str, Enum):
    API_KEY = "api_key"
    TOKEN = "token"
    PASSWORD = "password"
    OAUTH = "oauth"
    BASIC_AUTH = "basic_auth"
    CUSTOM = "custom"


class CredentialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    credential_type: CredentialType
    value: str = Field(..., min_length=1, max_length=10000)


class CredentialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    value: Optional[str] = Field(None, min_length=1, max_length=10000)


class CredentialResponse(BaseModel):
    id: int
    name: str
    credential_type: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


def get_credential_value(credential_id: int, user_id: int, db: Session) -> Optional[str]:
    """Get decrypted credential value by ID. Returns None if not found."""
    credential = db.query(Credential).filter(
        Credential.id == credential_id,
        Credential.user_id == user_id,
    ).first()
    if not credential:
        return None
    return decrypt_value(credential.encrypted_value)


def redact_credential_value(value: str, credential_value: str) -> str:
    """Replace credential value with redacted version for logging/storage."""
    if not credential_value or len(credential_value) < 4:
        return "***"
    # Show first 2 and last 2 characters
    masked = credential_value[:2] + "*" * (len(credential_value) - 4) + credential_value[-2:]
    return value.replace(credential_value, masked)


def redact_config_credentials(config: dict, user_id: int, db: Session) -> dict:
    """Redact credential values in config for safe storage in execution history."""
    import re
    pattern = re.compile(r"\{\{cred:(\d+)\}\}")

    def redact_value(val: Any) -> Any:
        if isinstance(val, str):
            def replace_match(match: re.Match) -> str:
                cred_id = int(match.group(1))
                cred = db.query(Credential).filter(
                    Credential.id == cred_id,
                    Credential.user_id == user_id,
                ).first()
                if cred:
                    decrypted = decrypt_value(cred.encrypted_value)
                    return redact_credential_value(decrypted, decrypted)
                return match.group(0)
            return pattern.sub(replace_match, val)
        elif isinstance(val, dict):
            return {k: redact_value(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [redact_value(item) for item in val]
        return val

    return redact_value(config)


def redact_output_values(output: Any, credential_map: Dict[str, str]) -> Any:
    """Redact credential plaintext values from execution output before persistence/event publication.

    Recursively traverses strings, dicts, and lists to replace any occurrence
    of known credential plaintext values (keys of credential_map) with their
    masked equivalents, preventing plaintext secrets from being stored in
    execution history or pushed via WebSocket/Redis events.

    This operates on the *output* from the executor, not the resolved config used
    during execution. The credential_map is built during _resolve_credentials from
    the actual values that were injected, making it both efficient and accurate.

    Args:
        output: The output data from a node executor (may be dict, list, or str).
        credential_map: Dict mapping actual plaintext credential values to their
                        masked equivalents (e.g., {"sk-ant-key-123": "sk-***123"}).

    Returns:
        The output structure with credential values replaced by masked versions.
    """
    if isinstance(output, str):
        # Sort by length descending to avoid partial replacements of shorter values
        # within longer credential strings
        for actual, masked in sorted(credential_map.items(), key=lambda x: len(x[0]), reverse=True):
            if actual in output:
                output = output.replace(actual, masked)
        return output
    elif isinstance(output, dict):
        return {k: redact_output_values(v, credential_map) for k, v in output.items()}
    elif isinstance(output, list):
        return [redact_output_values(item, credential_map) for item in output]
    return output


@router.post("/credentials", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
def create_credential(
    credential_data: CredentialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new credential."""
    encrypted_value = encrypt_value(credential_data.value)

    credential = Credential(
        user_id=current_user.id,
        name=credential_data.name,
        credential_type=credential_data.credential_type.value,
        encrypted_value=encrypted_value,
        encryption_version=1,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)

    return CredentialResponse(
        id=credential.id,
        name=credential.name,
        credential_type=credential.credential_type,
        created_at=credential.created_at.isoformat() if credential.created_at else "",
        updated_at=credential.updated_at.isoformat() if credential.updated_at else "",
    )


@router.get("/credentials", response_model=List[CredentialResponse])
def list_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all credentials for the current user."""
    credentials = db.query(Credential).filter(Credential.user_id == current_user.id).all()

    return [
        CredentialResponse(
            id=cred.id,
            name=cred.name,
            credential_type=cred.credential_type,
            created_at=cred.created_at.isoformat() if cred.created_at else "",
            updated_at=cred.updated_at.isoformat() if cred.updated_at else "",
        )
        for cred in credentials
    ]


@router.get("/credentials/{credential_id}", response_model=CredentialResponse)
def get_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific credential."""
    credential = db.query(Credential).filter(
        Credential.id == credential_id,
        Credential.user_id == current_user.id,
    ).first()
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    return CredentialResponse(
        id=credential.id,
        name=credential.name,
        credential_type=credential.credential_type,
        created_at=credential.created_at.isoformat() if credential.created_at else "",
        updated_at=credential.updated_at.isoformat() if credential.updated_at else "",
    )


@router.put("/credentials/{credential_id}", response_model=CredentialResponse)
def update_credential(
    credential_id: int,
    credential_data: CredentialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a credential."""
    credential = db.query(Credential).filter(
        Credential.id == credential_id,
        Credential.user_id == current_user.id,
    ).first()
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    if credential_data.name is not None:
        credential.name = credential_data.name
    if credential_data.value is not None:
        credential.encrypted_value = encrypt_value(credential_data.value)

    credential.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(credential)

    return CredentialResponse(
        id=credential.id,
        name=credential.name,
        credential_type=credential.credential_type,
        created_at=credential.created_at.isoformat() if credential.created_at else "",
        updated_at=credential.updated_at.isoformat() if credential.updated_at else "",
    )


@router.delete("/credentials/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a credential."""
    credential = db.query(Credential).filter(
        Credential.id == credential_id,
        Credential.user_id == current_user.id,
    ).first()
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    db.delete(credential)
    db.commit()
    return None


@router.get("/credentials/{credential_id}/decrypt")
def decrypt_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Decrypt and return credential value (use with caution)."""
    # Rate limit check
    rate_key = f"{current_user.id}:credential_decrypt"
    if not rate_limiter.is_allowed(rate_key, limit=10, window=3600):
        retry_after = rate_limiter.get_retry_after(rate_key, window=3600)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
        )

    credential = db.query(Credential).filter(
        Credential.id == credential_id,
        Credential.user_id == current_user.id,
    ).first()
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    decrypted_value = decrypt_value(credential.encrypted_value)

    return Response(
        content=json.dumps({
            "id": credential.id,
            "name": credential.name,
            "credential_type": credential.credential_type,
            "value": decrypted_value,
        }),
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )
