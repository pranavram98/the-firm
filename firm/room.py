"""Office room — Harvey conducts; colleagues take assigned tasks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .caps import review_cap_reached
from .matter import Matter
from .runtime import parse_dispatch

LEG_NUM = re.compile(r"leg-(\d+)")


def leg_sort_key(p: Path) -> tuple[int, str]:
    m = LEG_NUM.search(p.name)
    return (int(m.group(1)) if m else 0, p.as_posix())

ASSIGNMENT_RE = re.compile(
    r"^-\s*(tyagi|mike|jessica)\s*\|\s*([\w-]+)\s*\|\s*(.+?)\s*$",
    re.I | re.M,
)

ROOM_SECTION = re.compile(r"^#\s*Room assignments\s*$", re.I | re.M)


@dataclass(frozen=True)
class RoomAssignment:
    persona: str
    kind: str
    task: str


def parse_room_assignments(text: str) -> list[RoomAssignment]:
    m = ROOM_SECTION.search(text)
    if not m:
        return []
    block = text[m.end() :]
    out: list[RoomAssignment] = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            if out:
                break
            continue
        hit = ASSIGNMENT_RE.match(line)
        if hit:
            out.append(
                RoomAssignment(
                    hit.group(1).lower(),
                    hit.group(2).lower(),
                    hit.group(3).strip(),
                )
            )
    return out


def _latest_synthesize_after(folder: Path, anchor: Path) -> Path | None:
    ak = leg_sort_key(anchor)
    legs = [
        p for p in sorted(folder.glob("leg-*-harvey-synthesize.md"), key=leg_sort_key)
        if leg_sort_key(p) > ak
    ]
    return legs[-1] if legs else None


def _leg_suffix(kind: str) -> str:
    return {
        "brief-debate": "challenge",
        "viability": "viability",
        "procedure": "viability",
        "review": "review",
    }.get(kind, kind)


def _assignment_leg_path(folder: Path, assign: RoomAssignment, anchor: Path) -> Path:
    ak = leg_sort_key(anchor)
    existing = [
        p for p in folder.glob(f"leg-*-{assign.persona}-{_leg_suffix(assign.kind)}.md")
        if leg_sort_key(p) > ak
    ]
    if existing:
        return sorted(existing, key=leg_sort_key)[-1]
    n = max((leg_sort_key(p)[0] for p in folder.glob("leg-*.md")), default=0) + 1
    return folder / f"leg-{n:02d}-{assign.persona}-{_leg_suffix(assign.kind)}.md"


def assignment_recorded(folder: Path, assign: RoomAssignment, anchor: Path) -> bool:
    p = _assignment_leg_path(folder, assign, anchor)
    return p.is_file() and leg_sort_key(p) > leg_sort_key(anchor)


def _latest_draft_in_folder(folder: Path) -> Path | None:
    drafts = sorted(folder.glob("leg-*-mike-draft.md"), key=leg_sort_key)
    return drafts[-1] if drafts else None


def _latest_reviewer_leg(
    folder: Path, persona: str, kind: str, *, after: int
) -> Path | None:
    suffix = _leg_suffix(kind)
    legs = [
        p
        for p in sorted(folder.glob(f"leg-*-{persona}-{suffix}.md"), key=leg_sort_key)
        if leg_sort_key(p) >= after
    ]
    return legs[-1] if legs else None


def filter_assignments_for_phase(
    assignments: list[RoomAssignment],
    *,
    phase: str,
    folder: Path,
) -> list[RoomAssignment]:
    """Drop room lines that cannot run in this movement (e.g. Jessica review before a draft)."""
    has_draft = _latest_draft_in_folder(folder) is not None
    out: list[RoomAssignment] = []
    for a in assignments:
        if a.kind == "review" and (phase != "review" or not has_draft):
            continue
        if a.kind == "draft" and (phase != "review" or not has_draft):
            continue
        if a.kind == "prep" and phase != "pre_draft":
            continue
        if a.kind == "brief-debate" and phase != "debate":
            continue
        out.append(a)
    return out


def default_assignments(phase: str, folder: Path | None = None) -> list[RoomAssignment]:
    if phase == "debate":
        return [
            RoomAssignment(
                "tyagi",
                "brief-debate",
                "Maintainability — forum, limitation, posture",
            )
        ]
    if phase == "pre_draft":
        return [
            RoomAssignment(
                "mike",
                "prep",
                "Outline, record gaps, and drafting plan for the final work product",
            )
        ]
    if phase == "review":
        draft = _latest_draft_in_folder(folder) if folder else None
        if draft:
            dk = leg_sort_key(draft)
            jessica = _latest_reviewer_leg(folder, "jessica", "review", after=dk)
            if jessica:
                return []
        return [
            RoomAssignment(
                "jessica",
                "review",
                "Opposing counsel — third-party attack on the draft",
            )
        ]
    return []


def assignments_for_movement(folder: Path, opener: Path, *, phase: str) -> list[RoomAssignment]:
    parsed = parse_room_assignments(opener.read_text(encoding="utf-8"))
    if parsed:
        filtered = filter_assignments_for_phase(parsed, phase=phase, folder=folder)
        if filtered:
            return filtered
    return default_assignments(phase, folder)


def pending_room_work(
    folder: Path,
    opener: Path,
    *,
    phase: str,
) -> list[RoomAssignment]:
    pending: list[RoomAssignment] = []
    for a in assignments_for_movement(folder, opener, phase=phase):
        if not assignment_recorded(folder, a, opener):
            pending.append(a)
    return pending


def debate_folder(matter: Matter) -> Path:
    d = matter.path / "brief-debate"
    d.mkdir(exist_ok=True)
    return d


def pre_draft_folder(matter: Matter) -> Path:
    d = matter.path / "draft-prep"
    d.mkdir(exist_ok=True)
    return d


def _movement_opener(folder: Path) -> Path | None:
    harvey_legs = sorted(folder.glob("leg-*-harvey-*.md"), key=leg_sort_key)
    for p in reversed(harvey_legs):
        text = p.read_text(encoding="utf-8")
        if parse_room_assignments(text):
            return p
        if "proposal" in p.name or "conduct" in p.name:
            return p
    return None


def active_movement(
    folder: Path,
    *,
    phase: str,
) -> tuple[Path | None, list[RoomAssignment], bool]:
    """Return (opener, pending_work, needs_synthesize)."""
    opener = _movement_opener(folder)
    if not opener:
        return None, [], False

    synth = _latest_synthesize_after(folder, opener)
    if synth:
        if parse_room_assignments(synth.read_text(encoding="utf-8")):
            opener = synth
            synth = _latest_synthesize_after(folder, opener)
        else:
            return None, [], False

    pending = pending_room_work(folder, opener, phase=phase)
    if pending:
        return opener, pending, False
    if _latest_synthesize_after(folder, opener):
        return None, [], False
    return opener, [], True


def preallocate_room_paths(
    folder: Path,
    assignments: list[RoomAssignment],
) -> list[Path]:
    n = max((leg_sort_key(p)[0] for p in folder.glob("leg-*.md")), default=0)
    paths: list[Path] = []
    for assign in assignments:
        n += 1
        paths.append(folder / f"leg-{n:02d}-{assign.persona}-{_leg_suffix(assign.kind)}.md")
    return paths


NEXT_STEPS_SECTION = re.compile(r"^#\s*Next steps\s*$", re.I | re.M)
NEXT_STEP_LINE = re.compile(r"^-\s*(SIGNOFF|REDRAFT|ENCORE|READY)\s*:", re.I)


def parse_synthesize_decision(text: str) -> str | None:
    if parse_room_assignments(text):
        return "ENCORE"
    m = NEXT_STEPS_SECTION.search(text)
    if not m:
        return None
    for line in text[m.end() :].splitlines():
        line = line.strip()
        if not line.startswith("-"):
            if line.startswith("#"):
                break
            continue
        hit = NEXT_STEP_LINE.match(line)
        if hit:
            return hit.group(1).upper()
    return None


def review_movement_active(folder: Path) -> bool:
    _, pending, needs_synth = active_movement(folder, phase="review")
    return bool(pending or needs_synth)


def latest_synthesize(folder: Path) -> Path | None:
    legs = sorted(folder.glob("leg-*-harvey-synthesize.md"), key=leg_sort_key)
    return legs[-1] if legs else None


def round_folder(matter: Matter) -> Path:
    rounds = matter.round_dirs()
    if rounds:
        return rounds[-1]
    return matter.next_round_dir()


def all_work_folders(matter: Matter) -> list[Path]:
    folders: list[Path] = []
    if matter.config.get("brief_debate") != "closed":
        folders.append(debate_folder(matter))
    else:
        if matter.config.get("pre_draft") != "closed":
            folders.append(pre_draft_folder(matter))
        rounds = matter.round_dirs()
        folders.append(rounds[-1] if rounds else matter.next_round_dir())
    return folders


def _recall_kind(folder: Path, persona: str) -> str | None:
    if persona == "tyagi":
        return "brief-debate" if folder.name == "brief-debate" else "viability"
    if persona == "mike":
        return "prep" if folder.name == "draft-prep" else "draft"
    if persona == "jessica":
        return "review" if list(folder.glob("leg-*-mike-draft.md")) else None
    return None


def _persona_legs_after(folder: Path, persona: str, anchor: Path) -> list[Path]:
    ak = leg_sort_key(anchor)
    prefix = f"-{persona}-"
    legs = sorted(folder.glob("leg-*.md"), key=leg_sort_key)
    return [p for p in legs if prefix in p.name and leg_sort_key(p) > ak]


def dispatch_recall_step(folder: Path, matter: Matter) -> "Step | None":
    """Honor DISPATCH on any leg — specialist returns, then Harvey assesses."""
    from .state import LegSpec, Step

    if folder.name == "brief-debate":
        return None
    if review_cap_reached(matter) and folder.name.startswith("round-"):
        return None

    legs = sorted(folder.glob("leg-*.md"), key=leg_sort_key)
    for anchor in reversed(legs):
        is_synth = "-harvey-" in anchor.name and "synthesize" in anchor.name
        if "-harvey-" in anchor.name and not is_synth:
            continue
        target = parse_dispatch(anchor.read_text(encoding="utf-8"))
        if not target or target == "closed":
            continue
        if is_synth:
            # Partner prep close → lock prep (not another Mike prep leg).
            if folder.name == "draft-prep" and target == "mike":
                continue
            # DISPATCH: closed → sign-off handled in state PARTNER.
            if target == "closed":
                continue

        if target == "harvey" and not is_synth:
            for persona in ("tyagi", "mike", "jessica"):
                if f"-{persona}-" in anchor.name:
                    if not _latest_synthesize_after(folder, anchor):
                        return Step(
                            [LegSpec("harvey", "synthesize", f"{persona}-recall-close")]
                        )
                    break
            else:
                if not _latest_synthesize_after(folder, anchor):
                    return Step([LegSpec("harvey", "synthesize", "dispatch-assess")])
            continue

        kind = _recall_kind(folder, target)
        if target == "jessica" and not kind and matter.config.get("pre_draft") == "closed":
            rd = matter.round_dirs()
            if rd and list(rd[-1].glob("leg-*-mike-draft.md")):
                kind = "review"
        if not kind:
            continue
        if target == "mike" and kind == "draft" and review_cap_reached(matter):
            continue

        responses = _persona_legs_after(folder, target, anchor)
        if not responses:
            return Step([LegSpec(target, kind, f"{target}-recall")])

        rleg = responses[-1]
        if _latest_synthesize_after(folder, rleg):
            continue
        return Step([LegSpec("harvey", "synthesize", f"{target}-recall-close")])

    return None


def matter_dispatch_recall_step(matter: Matter) -> "Step | None":
    for folder in all_work_folders(matter):
        if step := dispatch_recall_step(folder, matter):
            return step
    return None


def dispatch_recall_open(matter: Matter) -> bool:
    return matter_dispatch_recall_step(matter) is not None


def recall_folder_for(matter: Matter, persona: str, kind: str) -> Path:
    """Folder for an in-flight dispatch recall leg."""
    for folder in all_work_folders(matter):
        legs = sorted(folder.glob("leg-*.md"), key=leg_sort_key)
        for anchor in reversed(legs):
            if f"-{persona}-" in anchor.name:
                continue
            if parse_dispatch(anchor.read_text(encoding="utf-8")) != persona:
                continue
            if _recall_kind(folder, persona) == kind or (
                persona == "jessica"
                and kind == "review"
                and list(folder.glob("leg-*-mike-draft.md"))
            ):
                return folder
    rounds = matter.round_dirs()
    if persona == "jessica" and rounds:
        return rounds[-1]
    if persona == "mike" and kind == "draft" and rounds:
        return rounds[-1]
    if persona == "mike" and kind == "prep":
        return pre_draft_folder(matter)
    if persona == "tyagi" and kind == "brief-debate":
        return debate_folder(matter)
    if rounds:
        return rounds[-1]
    if matter.config.get("pre_draft") != "closed":
        return pre_draft_folder(matter)
    return debate_folder(matter)


def synthesize_folder_for(matter: Matter) -> Path:
    for folder in all_work_folders(matter):
        legs = sorted(folder.glob("leg-*.md"), key=leg_sort_key)
        for anchor in reversed(legs):
            if "-harvey-" in anchor.name:
                continue
            target = parse_dispatch(anchor.read_text(encoding="utf-8"))
            if not target:
                continue
            if target == "harvey" and not _latest_synthesize_after(folder, anchor):
                return folder
            if target in ("tyagi", "mike", "jessica"):
                responses = _persona_legs_after(folder, target, anchor)
                if responses and not _latest_synthesize_after(folder, responses[-1]):
                    return folder
    folders = all_work_folders(matter)
    return folders[-1] if folders else round_folder(matter)


# Legacy aliases
tyagi_recall_folders = all_work_folders
matter_tyagi_recall_step = matter_dispatch_recall_step
tyagi_recall_open = dispatch_recall_open
tyagi_viability_folder = lambda m: recall_folder_for(m, "tyagi", "viability")
