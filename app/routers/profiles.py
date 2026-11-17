from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.deps import get_current_user, get_optional_user
from app.game_options import GAMES, RANKS, ROLES
from app.models import (
    ContactRequest,
    ContactRequestStatus,
    ModerationStatus,
    User,
    UserGameRank,
    UserProfile,
    UserRole,
)
from app.schemas import (
    ContactUserOut,
    ContactsListOut,
    GameOptionsOut,
    GameRankOut,
    OwnProfileOut,
    ProfileContactsUpdateIn,
    ProfileGamesUpdateIn,
    ProfileUpdateIn,
    PublicProfileOut,
    RoleOptionOut,
    SocialLinkOut,
)

router = APIRouter(prefix="/api", tags=["profiles"])

_TELEGRAM_LABELS = frozenset({"telegram", "tg"})


def _parse_contacts(profile: UserProfile) -> list[SocialLinkOut]:
    raw = profile.social_links or {}
    out: list[SocialLinkOut] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            url = str(item.get("url") or "").strip()
            if not label or not url:
                continue
            out.append(SocialLinkOut(label=label, url=url, is_public=bool(item.get("is_public"))))
    elif isinstance(raw, dict):
        for key, value in raw.items():
            url = str(value or "").strip()
            if url:
                out.append(SocialLinkOut(label=str(key), url=url, is_public=True))
    has_tg = any(c.label.lower() in _TELEGRAM_LABELS for c in out)
    if profile.telegram_url and not has_tg:
        out.insert(0, SocialLinkOut(label="Telegram", url=profile.telegram_url, is_public=False))
    return out


def _game_outs(profile: UserProfile) -> list[GameRankOut]:
    return [
        GameRankOut(
            game=g.game,
            rank=g.rank,
            roles=[str(r) for r in (g.roles or [])],
            sort_order=g.sort_order,
        )
        for g in profile.game_ranks
    ]


def _to_public(
    profile: UserProfile,
    *,
    include_private: bool = False,
    contact_status: str | None = None,
) -> PublicProfileOut:
    contacts = _parse_contacts(profile)
    visible = contacts if include_private else [c for c in contacts if c.is_public]
    telegram = next((c.url for c in visible if c.label.lower() in _TELEGRAM_LABELS), None)
    social_dict = {c.label: c.url for c in visible}
    return PublicProfileOut(
        id=profile.user_id,
        user_id=profile.user_id,
        nickname=profile.nickname,
        bio=profile.bio,
        telegram_url=telegram,
        social_links=social_dict,
        contacts=visible,
        games=_game_outs(profile),
        moderation_status=profile.moderation_status,
        is_public=profile.is_public,
        contact_status=contact_status,
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
    public = _to_public(profile, include_private=True)
    data = public.model_dump()
    data.update(
        {
            "moderation_status": profile.moderation_status,
            "moderation_note": profile.moderation_note or "",
            "is_public": profile.is_public,
            "profile_edit_unlocked": user.profile_edit_unlocked,
            "can_edit": _can_edit(user, profile),
        }
    )
    return OwnProfileOut(**data)


def _get_own_profile(db: Session, user_id: int) -> UserProfile | None:
    return db.scalar(
        select(UserProfile)
        .where(UserProfile.user_id == user_id)
        .options(selectinload(UserProfile.game_ranks))
    )


@router.get("/profile/options", response_model=GameOptionsOut)
def profile_options():
    roles = {
        game: [RoleOptionOut.model_validate(item) for item in items] for game, items in ROLES.items()
    }
    return GameOptionsOut(games=GAMES, ranks=RANKS, roles=roles)


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
    """Games/ranks/roles from dropdowns — save anytime, no moderation."""
    profile = _ensure_own_profile(db, user)
    profile.game_ranks.clear()
    db.flush()
    for i, g in enumerate(body.games):
        profile.game_ranks.append(
            UserGameRank(
                game=g.game,
                rank=g.rank.strip(),
                roles=list(str(r) for r in g.roles),
                sort_order=g.sort_order or i,
            )
        )
    db.commit()
    profile = _get_own_profile(db, user.id)
    return _to_own(user, profile)  # type: ignore[arg-type]


@router.put("/me/profile/contacts", response_model=OwnProfileOut)
def update_my_contacts(
    body: ProfileContactsUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _ensure_own_profile(db, user)
    dumped = [c.model_dump() for c in body.contacts]
    profile.social_links = dumped
    telegram = next((c for c in body.contacts if c.label.lower() in _TELEGRAM_LABELS), None)
    profile.telegram_url = telegram.url if telegram else None
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
def list_public_profiles(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "public, max-age=30"
    filters = [
        UserProfile.moderation_status == ModerationStatus.approved.value,
        UserProfile.is_public.is_(True),
        User.role.not_in((UserRole.admin.value, UserRole.moderator.value)),
    ]

    rows = db.scalars(
        select(UserProfile)
        .join(User, UserProfile.user_id == User.id)
        .where(*filters)
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

    if viewer is not None and (
        viewer.id == user_id or viewer.role in (UserRole.admin.value, UserRole.moderator.value)
    ):
        return _to_public(profile, include_private=True)

    if not (
        profile.moderation_status == ModerationStatus.approved.value
        and profile.is_public
    ):
        raise HTTPException(status_code=404, detail="Profile not found")

    contact_status = None
    include_private = False
    if viewer is not None:
        row = db.scalar(
            select(ContactRequest).where(
                ContactRequest.requester_id == viewer.id,
                ContactRequest.target_id == user_id,
            )
        )
        if row is not None:
            contact_status = row.status
            include_private = row.status == ContactRequestStatus.accepted.value
    return _to_public(profile, include_private=include_private, contact_status=contact_status)


def _nickname(db: Session, user_id: int) -> str:
    profile = db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile and profile.nickname:
        return profile.nickname
    user = db.get(User, user_id)
    return user.username if user else ""


def _contact_out(db: Session, row: ContactRequest, viewer_id: int) -> ContactUserOut:
    outgoing = row.requester_id == viewer_id
    other_id = row.target_id if outgoing else row.requester_id
    contacts = None
    if outgoing and row.status == ContactRequestStatus.accepted.value:
        profile = db.scalar(select(UserProfile).where(UserProfile.user_id == row.target_id))
        contacts = _parse_contacts(profile) if profile else []
    return ContactUserOut(
        request_id=row.id,
        user_id=other_id,
        nickname=_nickname(db, other_id),
        direction="outgoing" if outgoing else "incoming",
        status=row.status,
        contacts=contacts,
    )


@router.post("/users/{user_id}/contact-request", response_model=ContactUserOut)
def request_contacts(
    user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot request your own contacts")
    if not db.get(User, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    row = db.scalar(
        select(ContactRequest).where(
            ContactRequest.requester_id == user.id,
            ContactRequest.target_id == user_id,
        )
    )
    if row is None:
        row = ContactRequest(
            requester_id=user.id,
            target_id=user_id,
            status=ContactRequestStatus.pending.value,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    elif row.status == ContactRequestStatus.declined.value:
        row.status = ContactRequestStatus.pending.value
        db.commit()
        db.refresh(row)
    return _contact_out(db, row, user.id)


@router.get("/me/contacts", response_model=ContactsListOut)
def my_contacts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ContactRequest)
        .where(or_(ContactRequest.requester_id == user.id, ContactRequest.target_id == user.id))
        .order_by(ContactRequest.id)
    ).all()
    incoming: list[ContactUserOut] = []
    outgoing: list[ContactUserOut] = []
    for row in rows:
        item = _contact_out(db, row, user.id)
        if row.target_id == user.id:
            incoming.append(item)
        else:
            outgoing.append(item)
    return ContactsListOut(incoming=incoming, outgoing=outgoing)


@router.post("/me/contacts/{request_id}/accept", response_model=ContactUserOut)
def accept_contact_request(
    request_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(ContactRequest, request_id)
    if row is None or row.target_id != user.id:
        raise HTTPException(status_code=404, detail="Request not found")
    row.status = ContactRequestStatus.accepted.value
    db.commit()
    db.refresh(row)
    return _contact_out(db, row, user.id)


@router.post("/me/contacts/{request_id}/decline", response_model=ContactUserOut)
def decline_contact_request(
    request_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(ContactRequest, request_id)
    if row is None or row.target_id != user.id:
        raise HTTPException(status_code=404, detail="Request not found")
    row.status = ContactRequestStatus.declined.value
    db.commit()
    db.refresh(row)
    return _contact_out(db, row, user.id)
