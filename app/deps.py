from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type", "access") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token required")
        user_id = int(payload["sub"])
    except HTTPException:
        raise
    except (InvalidTokenError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if creds is None or not creds.credentials:
        return None
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type", "access") != "access":
            return None
        user_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError, TypeError):
        return None

    return db.get(User, user_id)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def require_moderator(user: User = Depends(get_current_user)) -> User:
    """Moderator stub: may review / approve profiles. Admin included."""
    if user.role not in (UserRole.admin.value, UserRole.moderator.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderator or admin only")
    return user
