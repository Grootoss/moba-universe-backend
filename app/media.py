"""Cover URL helpers for list thumbnails."""

from pathlib import PurePosixPath


def _local_cover_stem(path: str) -> str | None:
    """Stem of a file that lives directly in /images, not in a subdirectory."""
    if not path.startswith("/images/"):
        return None
    pure = PurePosixPath(path)
    if pure.parent.as_posix() != "/images":
        return None
    return pure.stem or None


def derive_cover_thumb(cover_image: str | None, cover_thumb: str | None = None) -> str | None:
    """Prefer a real small thumb.

    An explicit thumb under /images/thumbs/ or a remote URL is kept.
    A thumb that points at the full /images file is rewritten to
    /images/thumbs/{stem}.jpg, which the frontend build generates.
    """
    explicit = (cover_thumb or "").strip()
    raw = (cover_image or "").strip()
    if explicit.startswith("/images/thumbs/"):
        return explicit
    if explicit and _local_cover_stem(explicit) is None:
        return explicit
    stem = _local_cover_stem(raw) or _local_cover_stem(explicit)
    if stem:
        return f"/images/thumbs/{stem}.jpg"
    return explicit or raw or None
