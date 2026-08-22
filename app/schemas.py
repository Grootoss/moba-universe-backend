from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ValidationInfo, field_validator, model_validator
import re


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


_USERNAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁё]+$")


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=10)
    password: str = Field(min_length=6, max_length=20)
    password_confirm: str = Field(min_length=6, max_length=20)
    privacy_consent: bool

    @field_validator("username")
    @classmethod
    def username_ok(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 3 or len(s) > 10:
            raise ValueError("username must be 3–10 characters")
        if not _USERNAME_RE.fullmatch(s):
            raise ValueError("username must contain letters only")
        return s

    @field_validator("email")
    @classmethod
    def email_lower(cls, v: EmailStr) -> str:
        return str(v).lower()

    @field_validator("password")
    @classmethod
    def password_len(cls, v: str) -> str:
        if len(v) < 6 or len(v) > 20:
            raise ValueError("password must be 6–20 characters")
        return v

    @model_validator(mode="after")
    def confirm_and_consent(self) -> "RegisterIn":
        if self.password != self.password_confirm:
            raise ValueError("passwords do not match")
        if not self.privacy_consent:
            raise ValueError("privacy consent is required")
        return self


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    role: str
    profile_edit_unlocked: bool

    model_config = {"from_attributes": True}


from app.game_options import GAME_SLUGS, RANKS, ROLE_SLUGS

_SOCIAL_LABEL_RE = re.compile(r"^[A-Za-zА-Яа-яЁё0-9 ._-]{1,40}$")
_SAFE_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_MAX_CONTACTS = 1
_MAX_ROLES = 5


class GameRankIn(BaseModel):
    game: str
    rank: str = Field(min_length=1, max_length=80)
    roles: list[str] = Field(default_factory=list)
    sort_order: int = 0

    @field_validator("game")
    @classmethod
    def game_ok(cls, v: str) -> str:
        s = v.strip().lower()
        if s not in GAME_SLUGS:
            raise ValueError(f"unsupported game: {s}")
        return s

    @field_validator("rank")
    @classmethod
    def rank_ok(cls, v: str, info: ValidationInfo) -> str:
        rank = v.strip()
        game = info.data.get("game")
        if isinstance(game, str) and game in RANKS and rank not in RANKS[game]:
            raise ValueError(f"invalid rank for {game}")
        return rank

    @field_validator("roles")
    @classmethod
    def roles_ok(cls, v: list[str], info: ValidationInfo) -> list[str]:
        game = info.data.get("game")
        allowed = ROLE_SLUGS.get(game, frozenset()) if isinstance(game, str) else frozenset()
        seen: list[str] = []
        for raw in v:
            slug = str(raw).strip()
            if not slug:
                continue
            if slug not in allowed:
                raise ValueError(f"invalid role for {game}: {slug}")
            if slug in seen:
                continue
            seen.append(slug)
        if len(seen) > _MAX_ROLES:
            raise ValueError("at most 5 roles per game")
        return seen


class GameRankOut(BaseModel):
    game: str
    rank: str
    roles: list[str] = Field(default_factory=list)
    sort_order: int = 0


class SocialLinkIn(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    url: str = Field(min_length=1, max_length=255)
    is_public: bool = False

    @field_validator("label")
    @classmethod
    def label_ok(cls, v: str) -> str:
        s = v.strip()
        if not _SOCIAL_LABEL_RE.fullmatch(s):
            raise ValueError("invalid social label")
        return s

    @field_validator("url")
    @classmethod
    def url_ok(cls, v: str) -> str:
        s = v.strip()
        if not _SAFE_URL_RE.match(s):
            raise ValueError("url must start with http:// or https://")
        return s


class SocialLinkOut(BaseModel):
    label: str
    url: str
    is_public: bool = False


class PublicProfileOut(BaseModel):
    id: int
    user_id: int
    nickname: str
    bio: str
    telegram_url: str | None = None
    social_links: dict = Field(default_factory=dict)
    contacts: list[SocialLinkOut] = Field(default_factory=list)
    games: list[GameRankOut] = Field(default_factory=list)
    moderation_status: str | None = None
    is_public: bool | None = None
    contact_status: str | None = None


class OwnProfileOut(PublicProfileOut):
    moderation_status: str
    moderation_note: str
    is_public: bool
    profile_edit_unlocked: bool
    can_edit: bool


class ProfileUpdateIn(BaseModel):
    """Nickname / bio — go through moderation when submitted."""

    nickname: str = Field(min_length=1, max_length=80)
    bio: str = Field(default="", max_length=4000)
    telegram_url: str | None = Field(default=None, max_length=255)

    @field_validator("telegram_url")
    @classmethod
    def telegram_url_ok(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if not s:
            return None
        if not _SAFE_URL_RE.match(s):
            raise ValueError("telegram_url must start with http:// or https://")
        return s


class ProfileGamesUpdateIn(BaseModel):
    """Games / ranks — saved immediately, no moderation."""

    games: list[GameRankIn] = Field(default_factory=list)

    @field_validator("games")
    @classmethod
    def unique_games(cls, v: list[GameRankIn]) -> list[GameRankIn]:
        seen: set[str] = set()
        for g in v:
            if g.game in seen:
                raise ValueError("duplicate game in list")
            seen.add(g.game)
        return v


class ProfileContactsUpdateIn(BaseModel):
    """Telegram link — saved immediately. Shown on the public profile only if marked public."""

    contacts: list[SocialLinkIn] = Field(default_factory=list)

    @field_validator("contacts")
    @classmethod
    def contacts_ok(cls, v: list[SocialLinkIn]) -> list[SocialLinkIn]:
        if len(v) > _MAX_CONTACTS:
            raise ValueError("at most 1 contact link")
        return v


class ContactUserOut(BaseModel):
    request_id: int
    user_id: int
    nickname: str
    direction: str
    status: str
    contacts: list[SocialLinkOut] | None = None


class ContactsListOut(BaseModel):
    incoming: list[ContactUserOut] = Field(default_factory=list)
    outgoing: list[ContactUserOut] = Field(default_factory=list)


class AdminProfileOut(PublicProfileOut):
    email: str | None = None
    username: str | None = None
    moderation_status: str
    moderation_note: str = ""
    is_public: bool
    profile_edit_unlocked: bool = False


class ProfileModerateIn(BaseModel):
    moderation_status: str
    is_public: bool | None = None
    moderation_note: str | None = None

    @field_validator("moderation_status")
    @classmethod
    def status_ok(cls, v: str) -> str:
        if v not in ("pending", "approved", "rejected", "draft"):
            raise ValueError("invalid moderation_status")
        return v


class TranslationIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    excerpt: str = Field(default="", max_length=500)
    content: str = Field(min_length=1)
    mlbb_example: str = Field(default="")


class TranslationOut(BaseModel):
    title: str
    excerpt: str
    content: str
    mlbb_example: str = ""


class ArticleCreateIn(BaseModel):
    slug: str = Field(min_length=1, max_length=160)
    category_slug: str | None = None
    status: str = "published"
    cover_image: str | None = None
    cover_thumb: str | None = None
    translations: dict[str, TranslationIn]

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        s = v.strip().lower()
        if not s or " " in s:
            raise ValueError("slug must be non-empty without spaces")
        return s

    @field_validator("status")
    @classmethod
    def status_ok(cls, v: str) -> str:
        if v not in ("draft", "published"):
            raise ValueError("status must be draft or published")
        return v

    @field_validator("translations")
    @classmethod
    def need_langs(cls, v: dict[str, TranslationIn]) -> dict[str, TranslationIn]:
        if "ru" not in v and "en" not in v:
            raise ValueError("at least one of ru/en translations required")
        return v


class ArticleUpdateIn(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=160)
    category_slug: str | None = None
    status: str | None = None
    cover_image: str | None = None
    cover_thumb: str | None = None
    translations: dict[str, TranslationIn] | None = None

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        s = v.strip().lower()
        if not s or " " in s:
            raise ValueError("slug must be non-empty without spaces")
        return s

    @field_validator("status")
    @classmethod
    def status_ok(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in ("draft", "published"):
            raise ValueError("status must be draft or published")
        return v


class ArticleAdminOut(BaseModel):
    id: int
    slug: str
    status: str
    category: str | None = None
    cover_image: str | None = None
    cover_thumb: str | None = None
    title_ru: str | None = None
    title_en: str | None = None
    excerpt_ru: str | None = None
    excerpt_en: str | None = None
    content_ru: str | None = None
    content_en: str | None = None
    mlbb_example_ru: str | None = None
    mlbb_example_en: str | None = None


class ArticleListItemOut(BaseModel):
    id_article: int
    slug: str
    category: str | None = None
    cover_image: str | None = None
    cover_thumb: str | None = None
    title: str | None = None
    excerpt: str | None = None
    text: str | None = None
    translations: dict[str, dict] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ArticleListOut(BaseModel):
    items: list[ArticleListItemOut]
    total: int
    page: int
    page_size: int


class CategoryOut(BaseModel):
    slug: str
    name_ru: str
    name_en: str


class RoleOptionOut(BaseModel):
    slug: str
    number: int
    name_ru: str
    name_en: str


class GameOptionsOut(BaseModel):
    games: list[dict[str, str]]
    ranks: dict[str, list[str]]
    roles: dict[str, list[RoleOptionOut]] = Field(default_factory=dict)


class ErrorOut(BaseModel):
    detail: str
