"""Cover URL helpers for list thumbnails."""

from pathlib import PurePosixPath


def derive_cover_thumb(cover_image: str | None, cover_thumb: str | None = None) -> str | None:
    """Prefer an explicit small thumb; otherwise map /images/x → /images/thumbs/x."""
    explicit = (cover_thumb or "").strip()
    if explicit:
        return explicit
    raw = (cover_image or "").strip()
    if not raw:
        return None
    if raw.startswith("/images/thumbs/"):
        return raw
    if raw.startswith("/images/"):
        name = PurePosixPath(raw).name
        if name:
            stem = PurePosixPath(name).stem
            return f"/images/thumbs/{stem}.jpg"
    return None
