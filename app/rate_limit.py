"""Registration quota and failed-login lockouts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import LoginAttempt, RegistrationSlot

MSK = ZoneInfo("Europe/Moscow")

LOGIN_WINDOW = timedelta(minutes=15)
LOGIN_MAX_PER_EMAIL = 5
LOGIN_MAX_PER_IP = 30


def seconds_until_moscow_midnight() -> int:
    now = datetime.now(MSK)
    nxt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((nxt - now).total_seconds()))


def reserve_registration_slot(db: Session, ip: str) -> None:
    """Take today's slot for this IP. A second registration the same day is 429."""
    db.add(RegistrationSlot(ip=ip, day=datetime.now(MSK).date()))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=429,
            detail="Only one account per day from this IP",
            headers={"Retry-After": str(seconds_until_moscow_midnight())},
        ) from None


def _prune_login_attempts(db: Session, now: datetime) -> None:
    db.execute(delete(LoginAttempt).where(LoginAttempt.created_at < now - LOGIN_WINDOW))


def assert_login_allowed(db: Session, ip: str, email: str) -> None:
    now = datetime.now(UTC)
    _prune_login_attempts(db, now)
    since = now - LOGIN_WINDOW
    by_email = db.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(LoginAttempt.email == email, LoginAttempt.created_at >= since)
    )
    by_ip = db.scalar(
        select(func.count()).select_from(LoginAttempt).where(LoginAttempt.ip == ip, LoginAttempt.created_at >= since)
    )
    if (by_email or 0) >= LOGIN_MAX_PER_EMAIL or (by_ip or 0) >= LOGIN_MAX_PER_IP:
        db.commit()
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts",
            headers={"Retry-After": str(int(LOGIN_WINDOW.total_seconds()))},
        )


def record_login_failure(db: Session, ip: str, email: str) -> None:
    db.add(LoginAttempt(ip=ip, email=email, created_at=datetime.now(UTC)))
    db.commit()


def clear_login_failures(db: Session, email: str) -> None:
    db.execute(delete(LoginAttempt).where(LoginAttempt.email == email))
    db.commit()
