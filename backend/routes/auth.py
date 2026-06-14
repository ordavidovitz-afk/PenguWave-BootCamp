from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
import sqlite3

from database import get_db
from auth import verify_password, create_token, get_current_user
from models import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


# POST /api/auth/login — exchange email + password for a signed JWT.
# Security note: we return the SAME "Invalid email or password" message whether
# the email is unknown or the password is wrong. If the errors differed, an
# attacker could probe which emails are registered (account enumeration).
@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    db: Annotated[sqlite3.Connection, Depends(get_db)],
):
    cursor = db.cursor()
    # Parameterized query — the email is bound as a value, never interpolated.
    cursor.execute("SELECT * FROM users WHERE email = ?", (body.email,))
    user = cursor.fetchone()

    # Combine the "no such user" and "wrong password" cases into one check so
    # both fail identically and reveal nothing about which emails exist.
    if user is None or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user["status"] != "active":
        raise HTTPException(status_code=401, detail="Account is disabled")

    token = create_token(user["id"], user["email"], user["role"])
    return TokenResponse(
        token=token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            role=user["role"],
            status=user["status"],
        ),
    )


# POST /api/auth/logout — no auth required.
# JWTs are stateless: the server holds no session, so "logging out" simply means
# the client discards its stored token. A production system that needs immediate
# server-side revocation would add a token blacklist (e.g. store revoked token
# ids in Redis until they expire) and check it on every request.
@router.post("/logout")
def logout():
    return {"message": "Logged out"}


# GET /api/auth/me — return the currently authenticated user.
# The frontend calls this on page load to confirm a stored token is still valid
# (signature ok, not expired, account still active) and to refresh the user's
# role/status; get_current_user performs all of those checks.
@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[dict, Depends(get_current_user)]):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
        status=current_user["status"],
    )
