"""Phase caps — hard stops on brief debate, prep, and review loops."""

from __future__ import annotations

import re
from pathlib import Path

from .matter import Matter
from .runtime import parse_verdict

LEG_NUM = re.compile(r"leg-(\d+)")


def _leg_sort_key(p: Path) -> tuple[int, str]:
    m = LEG_NUM.search(p.name)
    return (int(m.group(1)) if m else 0, p.name)


def _cap(matter: Matter, key: str, default: int) -> int:
    raw = matter.config.get(key, default)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return default


def brief_cap(matter: Matter) -> int:
    return _cap(matter, "brief_cap", 3)


def prep_cap(matter: Matter) -> int:
    return _cap(matter, "prep_cap", 2)


def round_cap(matter: Matter) -> int:
    return _cap(matter, "round_cap", 3)


def _debate_dir(matter: Matter) -> Path:
    return matter.path / "brief-debate"


def _prep_dir(matter: Matter) -> Path:
    return matter.path / "draft-prep"


def _round_dir(matter: Matter) -> Path | None:
    rounds = matter.round_dirs()
    return rounds[-1] if rounds else None


def tyagi_challenge_count(matter: Matter) -> int:
    d = _debate_dir(matter)
    if not d.is_dir():
        return 0
    return len(list(d.glob("leg-*-tyagi-challenge.md")))


def mike_prep_count(matter: Matter) -> int:
    d = _prep_dir(matter)
    if not d.is_dir():
        return 0
    return len(list(d.glob("leg-*-mike-prep.md")))


def mike_draft_count(matter: Matter) -> int:
    rd = _round_dir(matter)
    if not rd:
        return 0
    return len(list(rd.glob("leg-*-mike-draft.md")))


def brief_cap_reached(matter: Matter) -> bool:
    if matter.config.get("brief_debate") == "closed":
        return False
    return tyagi_challenge_count(matter) >= brief_cap(matter)


def prep_cap_reached(matter: Matter) -> bool:
    if matter.config.get("pre_draft") == "closed":
        return False
    return mike_prep_count(matter) >= prep_cap(matter)


def review_cap_reached(matter: Matter) -> bool:
    if matter.config.get("pre_draft") != "closed":
        return False
    rd = _round_dir(matter)
    if not rd or not list(rd.glob("leg-*-mike-draft.md")):
        return False
    return mike_draft_count(matter) >= round_cap(matter)


def _uncleared_tyagi(matter: Matter) -> Path | None:
    d = _debate_dir(matter)
    legs = sorted(d.glob("leg-*-tyagi-challenge.md"), key=_leg_sort_key)
    if not legs:
        return None
    leg = legs[-1]
    if parse_verdict(leg.read_text(encoding="utf-8")).cleared:
        return None
    return leg


def _uncleared_reviewer_legs(matter: Matter) -> list[tuple[str, Path]]:
    rd = _round_dir(matter)
    if not rd:
        return []
    out: list[tuple[str, Path]] = []
    for persona in ("jessica", "tyagi"):
        legs = sorted(rd.glob(f"leg-*-{persona}-*.md"), key=_leg_sort_key)
        if not legs:
            continue
        leg = legs[-1]
        if not parse_verdict(leg.read_text(encoding="utf-8")).cleared:
            out.append((persona, leg))
    return out


def open_objections_blurb(matter: Matter) -> str:
    items = _uncleared_reviewer_legs(matter)
    if not items:
        return "No formal uncleared VERDICT on file — log any live [VERIFY] cites and client risk anyway."
    parts = []
    for persona, leg in items:
        v = parse_verdict(leg.read_text(encoding="utf-8"))
        parts.append(f"{persona.title()} ({v.label}) in {leg.name}")
    return "; ".join(parts)


def brief_lock_cap_forced(matter: Matter) -> bool:
    return brief_cap_reached(matter) and _uncleared_tyagi(matter) is not None


def prep_lock_cap_forced(matter: Matter) -> bool:
    return prep_cap_reached(matter)


def brief_cap_blurb(matter: Matter) -> str:
    leg = _uncleared_tyagi(matter)
    if not leg:
        return "Brief cap reached — log any open procedure items as residual risk."
    v = parse_verdict(leg.read_text(encoding="utf-8"))
    return f"Tyagi ({v.label}) in {leg.name} — partner accepts residual procedure risk and locks brief."
