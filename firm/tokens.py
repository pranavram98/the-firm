"""Token budget helpers — matter config with sane defaults."""

from __future__ import annotations

from .matter import Matter

DEFAULT_OFFICE_MAX = 4000
DEFAULT_INDEX_PREVIEW = 280
DEFAULT_HANDOFF_COMPACT = True


def office_max_chars(matter: Matter | None = None) -> int:
    if matter:
        raw = (matter.config.get("token") or {}).get("office_max_chars")
        if raw is not None:
            try:
                return max(500, int(raw))
            except (TypeError, ValueError):
                pass
    return DEFAULT_OFFICE_MAX


def index_preview_chars(matter: Matter | None = None) -> int:
    if matter:
        raw = (matter.config.get("token") or {}).get("index_preview_chars")
        if raw is not None:
            try:
                return max(80, int(raw))
            except (TypeError, ValueError):
                pass
    return DEFAULT_INDEX_PREVIEW


def handoff_compact(matter: Matter | None = None, *, embed: bool = False) -> bool:
    if embed:
        return False
    if matter:
        tok = matter.config.get("token") or {}
        if "handoff_compact" in tok:
            return bool(tok["handoff_compact"])
    return DEFAULT_HANDOFF_COMPACT
