# utils/auth.py
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pwdlib import PasswordHash  # newer library
from pwdlib.hashers.argon2 import Argon2Hasher

import config

logger = logging.getLogger(__name__)

# create password-hash helper
password_hash = PasswordHash((Argon2Hasher(),))


def hash_password(plain_password: str) -> str:
    if not plain_password:
        raise ValueError("Password must be provided")
    hashed = password_hash.hash(plain_password)
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        valid, new_hash = password_hash.verify_and_update(
            plain_password, hashed_password
        )
        # optionally handle new_hash if you want to update stored hash
        return valid
    except Exception as e:
        logger.exception("Password verification failed")
        return False


# JWT functions
JWT_SECRET = config.JWT_SECRET
JWT_ALGORITHM = config.JWT_ALGORITHM
JWT_EXPIRES_MINUTES = config.JWT_EXPIRES_MINUTES


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    if subject is None or subject == "":
        raise ValueError("Subject must be a non-empty string")
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or JWT_EXPIRES_MINUTES
    )
    payload = {"sub": subject, "exp": expire}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request, creds: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )
        return email
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
