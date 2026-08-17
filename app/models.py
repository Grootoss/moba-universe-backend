import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    moderator = "moderator"
    user = "user"


class ArticleStatus(str, enum.Enum):
    draft = "draft"
    published = "published"


class ModerationStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class GameType(str, enum.Enum):
    mlbb = "mlbb"
    lol = "lol"
    wildrift = "wildrift"
    dota2 = "dota2"
    aov = "aov"
    hok = "hok"
    smite = "smite"


class ContactRequestStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.user.value)
    profile_edit_unlocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    profile: Mapped["UserProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    articles: Mapped[list["Article"]] = relationship(back_populates="author")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    nickname: Mapped[str] = mapped_column(String(80), nullable=False)
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    telegram_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    social_links: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    moderation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ModerationStatus.draft.value
    )
    moderation_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="profile")
    game_ranks: Mapped[list["UserGameRank"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="UserGameRank.sort_order"
    )


class ContactRequest(Base):
    __tablename__ = "contact_requests"
    __table_args__ = (UniqueConstraint("requester_id", "target_id", name="uq_contact_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ContactRequestStatus.pending.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    requester: Mapped[User] = relationship(foreign_keys=[requester_id])
    target: Mapped[User] = relationship(foreign_keys=[target_id])


class UserGameRank(Base):
    __tablename__ = "user_game_ranks"
    __table_args__ = (UniqueConstraint("profile_id", "game", name="uq_profile_game"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id", ondelete="CASCADE"))
    game: Mapped[str] = mapped_column(String(20), nullable=False)
    rank: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    roles: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    profile: Mapped[UserProfile] = relationship(back_populates="game_ranks")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_ru: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)

    articles: Mapped[list["Article"]] = relationship(back_populates="category")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ArticleStatus.published.value)
    cover_image: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cover_thumb: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category: Mapped[Category | None] = relationship(back_populates="articles")
    author: Mapped[User | None] = relationship(back_populates="articles")
    translations: Mapped[list["ArticleTranslation"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )


class ArticleTranslation(Base):
    __tablename__ = "article_translations"
    __table_args__ = (UniqueConstraint("article_id", "lang", name="uq_article_lang"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"))
    lang: Mapped[str] = mapped_column(String(5), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    excerpt: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mlbb_example: Mapped[str] = mapped_column(Text, nullable=False, default="")

    article: Mapped[Article] = relationship(back_populates="translations")
