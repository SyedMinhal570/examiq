"""
src/api/routes/auth.py
──────────────────────
Authentication endpoints.

POST /api/v1/auth/register  → Create new student/faculty account
POST /api/v1/auth/login     → Get JWT access token
GET  /api/v1/auth/me        → Get current user profile
PUT  /api/v1/auth/me        → Update profile
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middleware.auth import CurrentUser
from src.core.security import create_access_token, hash_password, verify_password
from src.db.models import User, get_db_session

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=200)
    role: str = Field(default="student")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"student", "faculty"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {allowed}")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    is_active: bool


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    password: str | None = Field(default=None, min_length=8, max_length=100)


# ── Routes ────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Register a new student or faculty account.
    Returns a JWT token immediately (no email verification needed for MVP).
    """
    # Check email not already taken
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account with email '{body.email}' already exists.",
        )

    # Create user
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
    )
    db.add(user)
    await db.flush()  # Get the ID

    # Generate token
    token = create_access_token({"sub": str(user.id), "role": user.role})

    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT token",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Login with email + password. Returns JWT access token.
    Use this token in Authorization: Bearer <token> header for all protected routes.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Same error for wrong email OR wrong password (prevents user enumeration)
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )

    if not user:
        raise auth_error
    if not verify_password(body.password, user.hashed_password):
        raise auth_error
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact admin.",
        )

    token = create_access_token({"sub": str(user.id), "role": user.role})

    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """Returns the profile of the currently authenticated user."""
    return UserResponse(
        user_id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update profile",
)
async def update_me(
    body: UpdateProfileRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Update full name or password."""
    if body.full_name:
        current_user.full_name = body.full_name
    if body.password:
        current_user.hashed_password = hash_password(body.password)

    return UserResponse(
        user_id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
    )