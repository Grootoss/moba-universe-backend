from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user, get_optional_user
from app.game_options import GAMES, RANKS
from app.models import ModerationStatus, User, UserGameRank, UserProfile, UserRole
from app.schemas import (
    GameOptionsOut,
    GameRankOut,
    OwnProfileOut,
    ProfileGamesUpdateIn,
    ProfileUpdateIn,
    PublicProfileOut,
)

router = APIRouter(prefix="/api", tags=["profiles"])


def _to_public(profile: UserProfile) -> PublicProfileOut:
    return PublicProfileOut(
        id=profile.user_id,
        user_id=profile.user_id,
        nickname=profile.nickname,
        bio=profile.bio,
        telegram_url=profile.telegram_url,
        social_links=profile.social_links or {},
        games=[
            GameRankOut(game=g.game, rank=g.rank, sort_order=g.sort_order) for g in profile.game_ranks
        ],
        moderation_status=profile.moderation_status,
        is_public=profile.is_public,
    )


def _ensure_own_profile(db: Session, user: User) -> UserProfile:
    profile = _get_own_profile(db, user.id)
    if profile:
        return profile
    profile = UserProfile(
        user_id=user.id,
        nickname=user.username or user.email.split("@")[0],
        bio="",
        moderation_status=ModerationStatus.draft.value,
        moderation_note="",
        is_public=False,
    )
    db.add(profile)
    db.commit()
    ensured = _get_own_profile(db, user.id)
    if not ensured:
        raise HTTPException(status_code=500, detail="Failed to create profile")
    return ensured


def _can_edit(_user: User, profile: UserProfile) -> bool:
    """Editable until submitted; while pending, fields stay visible but locked."""
    return profile.moderation_status in (
        ModerationStatus.draft.value,
        ModerationStatus.rejected.value,
        ModerationStatus.approved.value,
    )


def _to_own(user: User, profile: UserProfile) -> OwnProfileOut:
    return OwnProfileOut(
        id=profile.user_id,
        user_id=profile.user_id,
        nickname=profile.nickname,
        bio=profile.bio,
        telegram_url=profile.telegram_url,
        social_links=profile.social_links or {},
        games=[
            GameRankOut(game=g.game, rank=g.rank, sort_order=g.sort_order) for g in profile.game_ranks
        ],
        moderation_status=profile.moderation_status,
        moderation_note=profile.moderation_note or "",
        is_public=profile.is_public,
        profile_edit_unlocked=user.profile_edit_unlocked,
        can_edit=_can_edit(user, profile),
    )


def _get_own_profile(db: Session, user_id: int) -> UserProfile | None:
    return db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .options(selectinload(UserProfile.game_ranks))
    )


@router.get("/profile/options", response_model=GameOptionsOut)
def profile_options():
    return GameOptionsOut(games=GAMES, ranks=RANKS)


@router.get("/me/profile", response_model=OwnProfileOut)
def get_my_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = _ensure_own_profile(db, user)
    return _to_own(user, profile)


@router.put("/me/profile", response_model=OwnProfileOut)
def update_my_profile(
    body: ProfileUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _ensure_own_profile(db, user)
    if not _can_edit(user, profile):
        raise HTTPException(
            status_code=403,
            detail="Profile is under review — cancel submission to edit again",
        )

    profile.nickname = body.nickname.strip()
    profile.bio = body.bio.strip()
    profile.telegram_url = (body.telegram_url or "").strip() or None
    # Text edits must leave the public site until re-approved
    if profile.moderation_status == ModerationStatus.approved.value:
        profile.moderation_status = ModerationStatus.pending.value
        profile.is_public = False
        profile.moderation_note = ""
    db.commit()
    profile = _get_own_profile(db, user.id)
    return _to_own(user, profile)  # type: ignore[arg-type]


@router.put("/me/profile/games", response_model=OwnProfileOut)
def update_my_games(
    body: ProfileGamesUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Games/ranks from dropdowns — save anytime, no moderation."""
    profile = _ensure_own_profile(db, user)
    profile.game_ranks.clear()
    db.flush()
    for i, g in enumerate(body.games):
        profile.game_ranks.append(
            UserGameRank(game=g.game, rank=g.rank.strip(), sort_order=g.sort_order or i)
        )
    db.commit()
    profile = _get_own_profile(db, user.id)
    return _to_own(user, profile)  # type: ignore[arg-type]


@router.post("/me/profile/submit", response_model=OwnProfileOut)
def submit_my_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = _ensure_own_profile(db, user)
    if profile.moderation_status == ModerationStatus.pending.value:
        raise HTTPException(status_code=400, detail="Already submitted for review")
    if not profile.nickname.strip():
        raise HTTPException(status_code=400, detail="Nickname is required")

    profile.moderation_status = ModerationStatus.pending.value
    profile.moderation_note = ""
    profile.is_public = False
    db.commit()
    profile = _get_own_profile(db, user.id)
    return _to_own(user, profile)  # type: ignore[arg-type]


@router.post("/me/profile/cancel", response_model=OwnProfileOut)
def cancel_my_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = _get_own_profile(db, user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.moderation_status != ModerationStatus.pending.value:
        raise HTTPException(status_code=400, detail="Nothing to cancel")
    profile.moderation_status = ModerationStatus.draft.value
    profile.is_public = False
    db.commit()
    profile = _get_own_profile(db, user.id)
    return _to_own(user, profile)  # type: ignore[arg-type]


@router.get("/users", response_model=list[PublicProfileOut])
def list_public_profiles(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(UserProfile)
        .join(User, UserProfile.user_id == User.id)
        .where(
            UserProfile.moderation_status == ModerationStatus.approved.value,
            UserProfile.is_public.is_(True),
            User.role.not_in((UserRole.admin.value, UserRole.moderator.value)),
        )
        .options(selectinload(UserProfile.game_ranks))
        .order_by(UserProfile.user_id)
    ).all()
    return [_to_public(p) for p in rows]


@router.get("/users/{user_id}", response_model=PublicProfileOut)
def get_public_profile(
    user_id: int,
    db: Session = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    profile = db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .options(selectinload(UserProfile.game_ranks))
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if viewer is not None:
        # Owner preview (draft / pending / rejected / approved)
        if viewer.id == user_id:
            return _to_public(profile)
        # Staff can open any profile while moderating
        if viewer.role in (UserRole.admin.value, UserRole.moderator.value):
            return _to_public(profile)

    # Public visitors: approved and published profiles are visible
    if (
        profile.moderation_status == ModerationStatus.approved.value
        and profile.is_public
    ):
        return _to_public(profile)

    raise HTTPException(status_code=404, detail="Profile not found")
