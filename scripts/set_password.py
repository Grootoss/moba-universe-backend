"""Replace a user's password. The new password is read from the environment, never from argv.

EMAIL=person@example.com NEW_PASSWORD='choose-a-long-one' python scripts/set_password.py

Also bumps token_version, so existing access and refresh tokens for that user stop working.
JWT_SECRET in .env is separate: change it and restart the API to invalidate every session.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password


def main() -> None:
    email = os.environ.get("EMAIL", "").strip().lower()
    password = os.environ.get("NEW_PASSWORD", "")
    if not email or not password:
        raise SystemExit("Set EMAIL and NEW_PASSWORD in the environment.")
    if len(password) < 12 or len(password) > 72:
        raise SystemExit("NEW_PASSWORD must be 12–72 characters.")

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            raise SystemExit(f"No user with email {email}")
        user.password_hash = hash_password(password)
        user.token_version = (user.token_version or 0) + 1
        db.commit()
        print(f"Password updated for {email}. Existing sessions for this user are revoked.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
