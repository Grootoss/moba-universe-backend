from fastapi import APIRouter, Depends, HTTPException, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import ModerationStatus, User, UserProfile, UserRole
from app.schemas import LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _tokens_for(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=email,
        username=body.username,
        password_hash=hash_password(body.password),
        role=UserRole.user.value,
        # New users fill the profile right after register; admin only publishes.
        profile_edit_unlocked=True,
    )
    db.add(user)
    db.flush()
    db.add(
        UserProfile(
            user_id=user.id,
            nickname=body.username,
            bio="",
            moderation_status=ModerationStatus.draft.value,
            moderation_note="",
            is_public=False,
        )
    )
    db.commit()
    db.refresh(user)
    return _tokens_for(user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return _tokens_for(user)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Refresh token required")
        user_id = int(payload["sub"])
    except HTTPException:
        raise
    except (InvalidTokenError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid refresh token") from None

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return _tokens_for(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/admin-check")
def admin_check(_: User = Depends(require_admin)):
    return {"ok": True}
