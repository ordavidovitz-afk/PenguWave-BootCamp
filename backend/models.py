# Pydantic models defining the API's request bodies and response shapes.
#
# Response model pattern: the shapes returned to clients are defined separately
# from how data is stored internally. The database `users` row carries a
# hashed_password column, but UserResponse — the only user model we ever return
# — has no such field. By serializing through these explicit response models,
# sensitive fields can never leak into an HTTP response, even by accident.

from pydantic import BaseModel, EmailStr
from typing import Optional


# --- AUTH MODELS ---


# Body of a login request: the credentials a user submits to obtain a token.
class LoginRequest(BaseModel):
    # we use str not EmailStr here so we can return a clean 401 instead of a 422 validation error on bad email format
    email: str
    password: str


# Successful login response: the signed JWT plus the public view of the user.
class TokenResponse(BaseModel):
    token: str
    user: "UserResponse"  # forward reference; UserResponse is defined below


# --- USER MODELS ---


# Public representation of a user, safe to send to clients.
class UserResponse(BaseModel):
    # this is the ONLY user model returned to clients — hashed_password is deliberately absent
    id: str
    email: str
    role: str
    status: str


# Body for creating a new user account.
class UserCreateRequest(BaseModel):
    email: EmailStr  # validates format
    password: str
    # role defaults to analyst — admin must explicitly grant elevated access
    role: str = "analyst"


# Body for updating an existing user's role and/or status.
class UserUpdateRequest(BaseModel):
    # both fields optional — caller can update role, status, or both in one request
    role: Optional[str] = None
    status: Optional[str] = None


# --- EVENT MODELS ---


# Public representation of a security event returned to clients.
class EventResponse(BaseModel):
    # most fields are Optional to handle messy real-world data gracefully
    id: str
    timestamp: str
    severity: str
    title: str
    description: Optional[str] = None
    assetHostname: Optional[str] = None
    assetIp: Optional[str] = None
    sourceIp: Optional[str] = None
    tags: list[str] = []
    userId: Optional[str] = None


# --- AI ANALYSIS MODEL ---


# Result of an AI triage request for a single event.
class EventAnalysis(BaseModel):
    # returned by the AI triage endpoint — contains Claude's assessment of the event
    event_id: str
    analysis: str
