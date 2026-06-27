"""
src/api/middleware/auth.py
──────────────────────────
FastAPI dependencies for JWT authentication and role-based access.

Usage in any route:
    @router.get("/protected")
    async def my_route(user = Depends(get_current_user)):
        return {"user": user.email}

    @router.get("/admin-only")
    async def admin_route(user = Depends(require_faculty)):
        ...
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decode_token
from src.db.models import User, get_db_session

# Extracts "Bearer <token>" from Authorization header
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Dependency: validates JWT and returns the current User object.
    Raises 401 if token is missing, invalid, or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please login again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    try:
        payload = decode_token(credentials.credentials)
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Fetch user from database
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise credentials_exception

    user = await db.get(User, uid)
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )
    return user


async def require_faculty(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency: requires faculty or admin role."""
    if current_user.role not in ("faculty", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faculty or admin access required.",
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency: requires admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


# Convenient type aliases for route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
FacultyUser = Annotated[User, Depends(require_faculty)]
AdminUser   = Annotated[User, Depends(require_admin)]