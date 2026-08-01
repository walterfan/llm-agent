from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        # bcrypt expects bytes, so encode the password
        password_bytes = plain_password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt with cost factor 12."""
    # bcrypt expects bytes
    password_bytes = password.encode("utf-8")
    # Generate salt and hash (cost factor 12 = 2^12 = 4096 rounds)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string for storage
    return hashed.decode("utf-8")


def create_access_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: str | Any, expires_delta: timedelta | None = None
) -> str:
    """Create a JWT refresh token with a longer expiration."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a JWT access token."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        logger.debug(f"🔓 [JWT] Attempting to decode token (length: {len(token)})")
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        logger.debug(f"✅ [JWT] Token decoded successfully: {payload}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("❌ [JWT] Token has expired")
        return None
    except jwt.JWTClaimsError as e:
        logger.warning(f"❌ [JWT] Invalid claims: {e}")
        return None
    except JWTError as e:
        logger.warning(f"❌ [JWT] Token decode error: {type(e).__name__}: {e}")
        return None
