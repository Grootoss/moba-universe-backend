from fastapi import APIRouter, Depends, HTTPException, Request, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.client_ip import client_ip
from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import ModerationStatus, User, UserProfile, UserRole
from app.rate_limit import (
    assert_login_allowed,
    clear_login_failures,
    record_login_failure,
    reserve_registration_slot,
)
from app.schemas import LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    dummy_password_hash,
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
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.scalar(select(User).where(func.lower(User.username) == body.username.lower())):
        raise HTTPException(status_code=400, detail="Username already taken")

    ip = client_ip(request)
    reserve_registration_slot(db, ip)
    user = User(
        email=email,
        username=body.username,
        password_hash=hash_password(body.password),
        role=UserRole.user.value,
        registration_ip=ip,
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
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = body.email.lower()
    ip = client_ip(request)
    assert_login_allowed(db, ip, email)
    user = db.scalar(select(User).where(User.email == email))
    password_ok = (
        verify_password(body.password, user.password_hash)
        if user
        else verify_password(body.password, dummy_password_hash())
    )
    if not user or not password_ok:
        record_login_failure(db, ip, email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    clear_login_failures(db, email)
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
