from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
import sqlite3
import uuid
from datetime import datetime, timezone

from database import get_db
from auth import get_current_user, require_admin, hash_password
from models import UserResponse, UserCreateRequest, UserUpdateRequest

router = APIRouter(prefix="/api/users", tags=["users"])

# Allowed values for the constrained columns, validated server-side.
VALID_ROLES = ("admin", "analyst")
VALID_STATUSES = ("active", "inactive")


# GET /api/users — list all users (admin only).
# require_admin ensures only admins reach this — a non-admin gets 403 before any DB query runs.
# UserResponse never carries hashed_password, so credentials cannot leak in the response.
@router.get("", response_model=list[UserResponse])
def list_users(
    admin: Annotated[dict, Depends(require_admin)],
    db: Annotated[sqlite3.Connection, Depends(get_db)],
):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    return [UserResponse(**dict(row)) for row in rows]


# POST /api/users — create a new user (admin only).
# We validate the role on the server even though the frontend likely offers only
# valid options: the frontend is untrusted and can be bypassed (curl, scripts),
# so the server is the only place authorization rules can actually be enforced.
@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    body: UserCreateRequest,
    admin: Annotated[dict, Depends(require_admin)],
    db: Annotated[sqlite3.Connection, Depends(get_db)],
):
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Role must be admin or analyst")

    cursor = db.cursor()
    # Parameterized query — email is bound as a value, never interpolated.
    cursor.execute("SELECT id FROM users WHERE email = ?", (body.email,))
    if cursor.fetchone() is not None:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        """
        INSERT INTO users (id, email, hashed_password, role, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, body.email, hash_password(body.password), body.role, "active", created_at),
    )
    db.commit()

    return UserResponse(id=user_id, email=body.email, role=body.role, status="active")


# PATCH /api/users/{user_id} — update a user's role and/or status (admin only).
@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    body: UserUpdateRequest,
    admin: Annotated[dict, Depends(require_admin)],
    db: Annotated[sqlite3.Connection, Depends(get_db)],
):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if body.role is not None and body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Role must be admin or analyst")
    if body.status is not None and body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Status must be active or inactive")

    # Build the UPDATE dynamically from only the fields the caller provided.
    # This is still injection-safe: the column NAMES come from our own code
    # (hardcoded strings below), never from user input, while every VALUE is
    # passed as a bound ? parameter. We never format values into the SQL string.
    updates = []
    values = []
    if body.role is not None:
        updates.append("role = ?")
        values.append(body.role)
    if body.status is not None:
        updates.append("status = ?")
        values.append(body.status)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    values.append(user_id)  # for the WHERE clause
    cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", tuple(values))
    db.commit()

    # Re-read so the response reflects the persisted state.
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    updated = cursor.fetchone()
    return UserResponse(**dict(updated))


# DELETE /api/users/{user_id} — remove a user (admin only).
# Self-deletion is blocked so an admin cannot accidentally lock themselves (or
# the last admin) out of the system mid-session, leaving no one able to manage it.
@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    admin: Annotated[dict, Depends(require_admin)],
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[sqlite3.Connection, Depends(get_db)],
):
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()

    return {"message": "User deleted"}
