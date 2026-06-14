from datetime import datetime, timedelta, timezone
from typing import Annotated

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
import os
import sqlite3

from database import get_db

# Load variables from backend/.env so secrets stay out of the source code.
load_dotenv()

# The JWT signing secret comes only from the environment. If it is missing we
# refuse to start rather than fall back to a hardcoded default — a predictable
# secret would let anyone forge valid tokens.
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable is not set — refusing to start")

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

# bcrypt password hashing context. "deprecated=auto" lets passlib transparently
# upgrade hashes if we ever change the scheme.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Extracts the "Authorization: Bearer <token>" header on protected routes.
security = HTTPBearer()


# Hashes a plaintext password for storage. We only ever persist the hash, never
# the password itself, so a database leak does not expose user credentials.
def hash_password(plain: str) -> str:
    # bcrypt is intentionally slow, making brute-force attacks expensive even if the database is stolen
    return pwd_context.hash(plain)


# Checks a login attempt's password against the stored hash.
def verify_password(plain: str, hashed: str) -> bool:
    # passlib uses constant-time comparison to prevent timing attacks
    return pwd_context.verify(plain, hashed)


# Creates a signed JWT identifying the user for the next TOKEN_EXPIRE_HOURS.
# We embed role in the token as a convenience hint for the client, but the
# server still re-reads the user's role and status from the database on every
# request (see get_current_user) — the token is never the source of truth for
# authorization, only for identity.
def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,  # subject — the id of the user this token belongs to
        "email": email,  # included so the client can display the logged-in user
        "role": role,    # convenience hint only; authoritative role lives in the DB
        # exp — absolute expiry. jose enforces this on decode, so stale tokens
        # are automatically rejected even if the signature is valid.
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


# Verifies a token's signature AND expiry, returning its decoded payload.
# jwt.decode checks both: a bad signature or an expired "exp" both raise JWTError.
def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        # any tampering with the token breaks the cryptographic signature and lands here
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is invalid or expired")


# Resolves the authenticated user for a request. We decode the token for
# identity, then fetch the live user record from the database. We deliberately
# do NOT trust the token alone: re-reading status on every request means that
# disabling an account takes effect immediately, even for tokens issued before
# the account was disabled and not yet expired.
def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[sqlite3.Connection, Depends(get_db)],
) -> dict:
    payload = decode_token(credentials.credentials)

    cursor = db.cursor()
    # Parameterized query — the user id is bound as a value, never interpolated
    # into the SQL string, so it cannot alter the query (no SQL injection).
    cursor.execute("SELECT * FROM users WHERE id = ?", (payload["sub"],))
    user = cursor.fetchone()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if user["status"] != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is disabled")

    return dict(user)


# Guards admin-only routes. Authorization is enforced here on the server —
# never trust the frontend to hide admin features.
def require_admin(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
