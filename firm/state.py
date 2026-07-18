"""Office state machine — sequential gates: Tyagi brief, Mike prep, Jessica OC review."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .matter import Matter
from .room import (
    active_movement,
    debate_folder,
    latest_synthesize,
    leg_sort_key,
    matter_dispatch_recall_step,
    parse_synthesize_decision,
    pre_draft_folder,
    dispatch_recall_open,
    review_movement_active,
    round_folder,
)
from .caps import brief_cap_reached, prep_cap_reached, review_cap_reached
from .pack import pack_ready
from .runtime import parse_dispatch, parse_signoff, parse_verdict, signoff_adopts


class Phase(str, Enum):
    BRIEF_OPEN = "brief_open"
    BRIEF_DEBATE = "brief_debate"
    PRE_DRAFT = "pre_draft"
    EXECUTION = "execution"
    REVIEW = "review"
    PARTNER = "partner"
    PACK = "pack"
    DELIVER = "deliver"
    COMPLETE = "complete"


@dataclass
class LegSpec:
    persona: str
    kind: str
    reason: str
    task: str = ""


@dataclass
class Step:
    legs: list[LegSpec]
    pause: bool = False
    reason: str = ""
    do: str = ""


def brief_locked(matter: Matter) -> bool:
    return matter.config.get("brief_debate") == "closed"


def pre_draft_locked(matter: Matter) -> bool:
    return matter.config.get("pre_draft") == "closed"


def latest_draft(matter: Matter) -> Path | None:
    rounds = matter.round_dirs()
    if not rounds:
        return None
    drafts = sorted(rounds[-1].glob("leg-*-mike-draft.md"), key=leg_sort_key)
    return drafts[-1] if drafts else None


def _round_dir(matter: Matter) -> Path | None:
    rounds = matter.round_dirs()
    return rounds[-1] if rounds else None


def _review_for_current_draft(matter: Matter, persona: str, kind: str) -> Path | None:
    draft = latest_draft(matter)
    rd = _round_dir(matter)
    if not draft or not rd:
        return None
    dk = leg_sort_key(draft)
    legs = [
        p for p in sorted(rd.glob(f"leg-*-{persona}-*.md"), key=leg_sort_key)
        if kind in p.name and leg_sort_key(p) >= dk
    ]
    return legs[-1] if legs else None


def _latest_tyagi_challenge(folder: Path) -> Path | None:
    legs = sorted(folder.glob("leg-*-tyagi-challenge.md"), key=leg_sort_key)
    return legs[-1] if legs else None


def _jessica_for_draft(matter: Matter) -> Path | None:
    return _review_for_current_draft(matter, "jessica", "review")


def _harvey_assessed_jessica(matter: Matter) -> bool:
    jessica = _jessica_for_draft(matter)
    rd = _round_dir(matter)
    if not jessica or not rd:
        return False
    synth = latest_synthesize(rd)
    return bool(synth and leg_sort_key(synth) >= leg_sort_key(jessica))


def _signoff_for_current_draft(matter: Matter) -> Path | None:
    draft = latest_draft(matter)
    rd = _round_dir(matter)
    if not draft or not rd:
        return None
    dk = leg_sort_key(draft)
    legs: list[Path] = []
    for pat in ("leg-*-harvey-sign-off.md", "leg-*-harvey-signoff.md"):
        legs.extend(rd.glob(pat))
    legs = [p for p in sorted(legs, key=leg_sort_key) if leg_sort_key(p) >= dk]
    return legs[-1] if legs else None


def _room_step(folder: Path, *, phase: str) -> Step | None:
    _opener, pending, needs_synth = active_movement(folder, phase=phase)
    if pending:
        return Step(
            [
                LegSpec(a.persona, a.kind, "room-orchestra", a.task)
                for a in pending
            ]
        )
    if needs_synth:
        return Step([LegSpec("harvey", "synthesize", "room-close")])
    return None


def _deliverables_summary(matter: Matter) -> str:
    final = matter.final_dir
    parts = [str(final / "work-product.md")]
    for name in ("work-product.docx", "work-product.pdf"):
        p = final / name
        if p.is_file():
            parts.append(str(p))
    pack = final / "pack"
    if pack.is_dir():
        parts.extend(str(p) for p in sorted(pack.glob("*.pdf")))
    return " · ".join(parts)


def compute_phase(matter: Matter) -> Phase:
    if matter.config.get("status") == "closed" and matter.work_product.is_file():
        if not pack_ready(matter):
            return Phase.PACK
        if not matter.config.get("export_done"):
            return Phase.DELIVER
        return Phase.COMPLETE
    if not brief_locked(matter):
        debate = matter.path / "brief-debate"
        if not list(debate.glob("leg-*-harvey-proposal.md")):
            return Phase.BRIEF_OPEN
        return Phase.BRIEF_DEBATE
    if not pre_draft_locked(matter):
        return Phase.PRE_DRAFT
    if not latest_draft(matter):
        return Phase.EXECUTION
    rd = _round_dir(matter)
    if rd and review_movement_active(rd):
        return Phase.REVIEW
    jessica = _jessica_for_draft(matter)
    if not jessica:
        return Phase.REVIEW
    if not _harvey_assessed_jessica(matter):
        return Phase.REVIEW
    if dispatch_recall_open(matter) and not review_cap_reached(matter):
        return Phase.REVIEW
    if parse_verdict(jessica.read_text(encoding="utf-8")).cleared:
        return Phase.PARTNER
    if review_cap_reached(matter):
        return Phase.PARTNER
    return Phase.REVIEW


def next_step(matter: Matter) -> Step:
    phase = compute_phase(matter)

    if phase == Phase.COMPLETE:
        return Step([], pause=True, reason="complete", do=_deliverables_summary(matter))

    if phase == Phase.PACK:
        return Step([LegSpec("mike", "pack", "client-pack")])

    if phase == Phase.DELIVER:
        return Step([LegSpec("__engine__", "export", "deliverables")])

    if recall := matter_dispatch_recall_step(matter):
        return recall

    if phase == Phase.BRIEF_OPEN:
        return Step([LegSpec("harvey", "proposal", "office-open")])

    if phase == Phase.BRIEF_DEBATE:
        folder = debate_folder(matter)
        tyagi = _latest_tyagi_challenge(folder)
        synth = latest_synthesize(folder)

        if not brief_cap_reached(matter):
            room = _room_step(folder, phase="debate")
            if room:
                return room

        if tyagi and synth and leg_sort_key(synth) >= leg_sort_key(tyagi):
            if parse_verdict(tyagi.read_text(encoding="utf-8")).cleared:
                return Step([LegSpec("__engine__", "lock-brief", "tyagi-cleared")])

        if brief_cap_reached(matter):
            if tyagi and (not synth or leg_sort_key(synth) < leg_sort_key(tyagi)):
                return Step([LegSpec("harvey", "synthesize", "brief-cap")])
            return Step([LegSpec("__engine__", "lock-brief", "brief-cap")])

        return Step([LegSpec("harvey", "conduct", "debate-reopen")])

    if phase == Phase.PRE_DRAFT:
        folder = pre_draft_folder(matter)
        preps = sorted(folder.glob("leg-*-mike-prep.md"), key=leg_sort_key)
        latest_prep = preps[-1] if preps else None
        synth = latest_synthesize(folder)

        if not prep_cap_reached(matter):
            room = _room_step(folder, phase="pre_draft")
            if room:
                return room

            synth = latest_synthesize(folder)
            if synth:
                d = parse_dispatch(synth.read_text(encoding="utf-8"))
                if d == "mike" or parse_synthesize_decision(synth.read_text(encoding="utf-8")) == "READY":
                    return Step([LegSpec("__engine__", "lock-pre-draft", "prep-cleared")])

        synth = latest_synthesize(folder)
        if prep_cap_reached(matter):
            if latest_prep and (not synth or leg_sort_key(synth) < leg_sort_key(latest_prep)):
                return Step([LegSpec("harvey", "synthesize", "prep-cap")])
            return Step([LegSpec("__engine__", "lock-pre-draft", "prep-cap")])

        return Step([LegSpec("harvey", "conduct", "prep-reopen")])

    if phase == Phase.EXECUTION:
        return Step([LegSpec("mike", "draft", "final-draft")])

    if phase == Phase.REVIEW:
        folder = round_folder(matter)
        room = _room_step(folder, phase="review")
        if room:
            return room

        jessica = _jessica_for_draft(matter)
        if not jessica:
            if review_cap_reached(matter):
                return Step([LegSpec("harvey", "sign-off", "round-cap")])
            return Step([LegSpec("jessica", "review", "oc-review")])

        if not _harvey_assessed_jessica(matter):
            return Step([LegSpec("harvey", "synthesize", "oc-assess")])

        if review_cap_reached(matter):
            return Step([LegSpec("harvey", "sign-off", "round-cap")])

        if parse_verdict(jessica.read_text(encoding="utf-8")).cleared:
            return Step([LegSpec("harvey", "sign-off", "jessica-cleared")])

        return Step([LegSpec("harvey", "conduct", "oc-reopen")])

    signoff = _signoff_for_current_draft(matter)
    cap = review_cap_reached(matter)
    if not signoff:
        reason = "round-cap" if cap else "jessica-cleared"
        return Step([LegSpec("harvey", "sign-off", reason)])
    decision = parse_signoff(signoff.read_text(encoding="utf-8"))
    if signoff_adopts(decision):
        return Step([LegSpec("__engine__", "adopt", "harvey-signed-off")])
    if decision == "REDRAFT":
        if cap:
            return Step([LegSpec("harvey", "sign-off", "round-cap-no-redraft")])
        return Step([LegSpec("mike", "draft", "harvey-redraft")])
    reason = "round-cap-no-redraft" if cap else "signoff-missing-line"
    return Step([LegSpec("harvey", "sign-off", reason)])
