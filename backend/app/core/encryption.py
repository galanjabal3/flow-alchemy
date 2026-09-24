"""Shared encryption utilities for the application."""

import os
import base64
from cryptography.fernet import Fernet
from app.core.config import settings


_fernet_instance = None


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
        if key:
            _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
        else:
            salt = b"flowalchemy-credential-salt-v1"
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            derived_key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
            _fernet_instance = Fernet(derived_key)
    return _fernet_instance


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value using Fernet."""
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string value."""
    fernet = _get_fernet()
    return fernet.decrypt(ciphertext.encode()).decode()
