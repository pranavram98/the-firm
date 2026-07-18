"""Next-leg briefing for orchestrator subagent handoffs."""

from __future__ import annotations

import json
from pathlib import Path

from .cast import model_for_leg, surface_for_matter
from .matter import Matter
from .prompts import (
    delegated_task,
    harvey_conduct,
    harvey_dispatch,
    harvey_proposal,
    harvey_signoff,
    harvey_synthesize,
    jessica_review,
    mike_draft,
    mike_prep,
    mike_pack,
    tyagi_brief_debate,
    tyagi_viability,
)
from .pack import CLIENT_DOCS, DOCS, scaffold_pack
from .room import (
    RoomAssignment,
    active_movement,
    preallocate_room_paths,
    pre_draft_folder,
    recall_folder_for,
    synthesize_folder_for,
)
from .state import LegSpec, Step, brief_locked, compute_phase, next_step, pre_draft_locked


def _debate_dir(matter: Matter) -> Path:
    d = matter.path / "brief-debate"
    d.mkdir(exist_ok=True)
    return d


def _round_dir(matter: Matter) -> Path:
    dirs = matter.round_dirs()
    if dirs:
        return dirs[-1]
    return matter.next_round_dir()


def _leg_suffix(kind: str) -> str:
    return {
        "brief-debate": "challenge",
        "viability": "viability",
        "procedure": "viability",
        "review": "review",
        "sign-off": "signoff",
        "pack": "pack",
    }.get(kind, kind)


def _harvey_work_folder(matter: Matter) -> Path:
    if not brief_locked(matter):
        return _debate_dir(matter)
    if not pre_draft_locked(matter):
        return pre_draft_folder(matter)
    return _round_dir(matter)


def _folder_for_spec(matter: Matter, spec: LegSpec) -> Path | None:
    if spec.persona == "__engine__":
        return None
    if spec.persona == "harvey" and spec.kind == "proposal":
        return _debate_dir(matter)
    if spec.persona == "harvey" and spec.kind in ("conduct", "synthesize", "sign-off"):
        if spec.kind == "synthesize" and spec.reason.endswith(("-recall-close", "dispatch-assess")):
            return synthesize_folder_for(matter)
        return _harvey_work_folder(matter)
    if spec.persona == "tyagi":
        return recall_folder_for(matter, "tyagi", spec.kind)
    if spec.persona == "mike" and spec.kind == "prep":
        return recall_folder_for(matter, "mike", "prep")
    if spec.persona == "mike" and spec.kind == "draft":
        return recall_folder_for(matter, "mike", "draft")
    if spec.persona == "jessica" and spec.kind == "review":
        return recall_folder_for(matter, "jessica", "review")
    return None


def _phase_for_folder(matter: Matter, folder: Path) -> str:
    pos = folder.as_posix()
    if "brief-debate" in pos:
        return "debate"
    if "draft-prep" in pos:
        return "pre_draft"
    return "review"


def _step_artifact_paths(matter: Matter, step: Step) -> list[Path | None]:
    if (
        len(step.legs) > 1
        and step.legs[0].reason == "room-orchestra"
        and (folder := _folder_for_spec(matter, step.legs[0]))
    ):
        assigns = [RoomAssignment(s.persona, s.kind, s.task) for s in step.legs]
        return preallocate_room_paths(folder, assigns)

    folder_next: dict[str, int] = {}
    paths: list[Path | None] = []
    for spec in step.legs:
        if spec.persona == "__engine__":
            paths.append(None)
            continue
        if spec.persona == "harvey" and spec.kind == "proposal":
            paths.append(_debate_dir(matter) / "leg-01-harvey-proposal.md")
            continue
        if spec.persona == "mike" and spec.kind == "pack":
            pack = scaffold_pack(matter, CLIENT_DOCS)
            paths.append(pack / "_mike-pack-notes.md")
            continue
        folder = _folder_for_spec(matter, spec)
        if not folder:
            paths.append(None)
            continue
        fk = folder.as_posix()
        if fk not in folder_next:
            folder_next[fk] = len(list(folder.glob("leg-*.md")))
        folder_next[fk] += 1
        n = folder_next[fk]
        paths.append(folder / f"leg-{n:02d}-{spec.persona}-{_leg_suffix(spec.kind)}.md")
    return paths


def artifact_path(matter: Matter, spec: LegSpec) -> Path | None:
    return _step_artifact_paths(matter, Step([spec]))[0]


def prompt_for_leg(matter: Matter, spec: LegSpec) -> str:
    task = spec.task
    folder = _folder_for_spec(matter, spec) or _debate_dir(matter)
    phase = _phase_for_folder(matter, folder)

    if spec.persona == "harvey":
        if spec.kind == "proposal":
            return harvey_proposal(matter)
        if spec.kind == "conduct":
            return harvey_conduct(matter, folder, phase=phase)
        if spec.kind == "synthesize":
            return harvey_synthesize(matter, folder, phase=phase, reason=spec.reason)
        if spec.kind == "dispatch":
            last = sorted(matter.path.glob("**/leg-*.md"))[-1]
            return harvey_dispatch(matter, last)
        if spec.kind == "sign-off":
            rd = _round_dir(matter)
            draft = sorted(rd.glob("leg-*-mike-draft.md"))[-1]
            cap_forced = spec.reason.startswith("round-cap")
            return harvey_signoff(matter, rd, draft, cap_forced=cap_forced)

    if spec.kind == "task":
        return delegated_task(matter, spec.persona, task, folder)

    if spec.persona == "tyagi" and spec.kind == "brief-debate":
        return tyagi_brief_debate(matter, _debate_dir(matter), task=task)
    if spec.persona == "tyagi" and spec.kind == "viability":
        vf = recall_folder_for(matter, "tyagi", "viability")
        draft = sorted(vf.glob("leg-*-mike-draft.md"))
        return tyagi_viability(matter, vf, draft[-1] if draft else None, task=task)
    if spec.persona == "mike" and spec.kind == "prep":
        return mike_prep(matter, recall_folder_for(matter, "mike", "prep"), task=task)
    if spec.persona == "mike" and spec.kind == "draft":
        rd = recall_folder_for(matter, "mike", "draft")
        prior = sorted(rd.glob("leg-*-mike-draft.md"))
        return mike_draft(matter, rd, prior[-1] if prior else None)
    if spec.persona == "jessica" and spec.kind == "review":
        rd = recall_folder_for(matter, "jessica", "review")
        drafts = sorted(rd.glob("leg-*-mike-draft.md"))
        if not drafts:
            raise SystemExit("no mike draft — jessica review cannot run yet")
        return jessica_review(matter, rd, drafts[-1], task=task)

    if spec.persona == "mike" and spec.kind == "pack":
        pack = scaffold_pack(matter, CLIENT_DOCS)
        doc_list = "\n".join(f"- final/pack/{DOCS[d]}.html ({d})" for d in CLIENT_DOCS)
        return mike_pack(matter, doc_list)

    raise SystemExit(f"no prompt for {spec.persona}/{spec.kind}")


def _batch_meta(matter: Matter, step: Step, artifact_paths: list[Path | None]) -> dict:
    orchestra = len(step.legs) > 1 and step.legs[0].reason == "room-orchestra"
    if step.pause or not orchestra:
        return {"parallel": False, "require_all": False, "artifacts": [], "recorded": [], "pending": []}
    arts: list[str] = []
    recorded: list[str] = []
    for out in artifact_paths:
        if not out:
            continue
        rel = str(out.relative_to(matter.path))
        arts.append(rel)
        if out.is_file():
            recorded.append(rel)
    pending = [a for a in arts if a not in recorded]
    return {
        "parallel": True,
        "require_all": True,
        "artifacts": arts,
        "recorded": recorded,
        "pending": pending,
        "instruction": (
            "Orchestra movement: spawn EVERY subagent in legs[] at once. "
            "Each has a different task from Harvey's Room assignments. "
            "Wait for all; firm record-leg each; do NOT firm next until pending is empty."
        ),
    }


def next_handoff(matter: Matter) -> dict:
    step: Step = next_step(matter)
    surface = surface_for_matter(matter)
    if step.pause:
        return {
            "pause": True,
            "reason": step.reason,
            "do": step.do,
            "matter": str(matter.path),
            "surface": surface,
            "office": str(matter.path / "office.md"),
        }
    legs = []
    artifact_paths = _step_artifact_paths(matter, step)
    for spec, out in zip(step.legs, artifact_paths, strict=True):
        model = model_for_leg(spec.persona, spec.kind, matter) if spec.persona != "__engine__" else ""
        entry = {
            "persona": spec.persona,
            "kind": spec.kind,
            "reason": spec.reason,
            "task": spec.task,
            "model": model,
            "mode": (
                "engine"
                if spec.persona == "__engine__"
                else "harvey"
                if spec.persona == "harvey"
                else "subagent"
            ),
            "subagent": spec.persona if spec.persona not in ("harvey", "__engine__") else None,
            "orchestrator": spec.persona in ("harvey", "__engine__"),
            "artifact": str(out.relative_to(matter.path)) if out else None,
        }
        if spec.persona == "__engine__":
            entry["engine"] = spec.kind
            if spec.kind == "export":
                entry["do"] = (
                    "Run firm engine export — builds work-product.docx/.pdf and "
                    "final/pack/*.pdf (Briefing Memo, Argument Notes, Client Briefing 2pp, Reference Table)"
                )
        elif spec.persona != "__engine__":
            entry["prompt"] = prompt_for_leg(matter, spec)
        legs.append(entry)
    batch = _batch_meta(matter, step, artifact_paths)
    phase = compute_phase(matter).value
    movement: dict = {"round": matter.current_round()}
    if matter.round_dirs():
        rd = matter.round_dirs()[-1]
        _, pending, needs_synth = active_movement(rd, phase="review")
        movement.update(
            {
                "pending": len(pending),
                "needs_synthesize": needs_synth,
                "cycle": "orchestra" if pending else "assess" if needs_synth else "partner",
            }
        )
    out = {
        "pause": False,
        "matter": str(matter.path),
        "surface": surface,
        "phase": phase,
        "movement": movement,
        "office": str(matter.path / "office.md"),
        "legs": legs,
        "batch": batch,
    }
    if batch["parallel"] and batch["pending"]:
        out["do"] = (
            f"Orchestra in progress — {len(batch['pending'])} leg(s) unrecorded: "
            + ", ".join(batch["pending"])
        )
    return out


def next_handoff_json(matter: Matter) -> str:
    return json.dumps(next_handoff(matter), indent=2)
