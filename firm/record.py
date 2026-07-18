"""Record legs written in-session (Harvey / visible subagents)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .cast import log_hop, model_for_leg
from .citations import audit_draft_file
from .courts import infer_court_id
from .matter import Matter
from .office import append_speech, append_leg_start, seed_office, speech_from_artifact
from .progress import clear_leg_status, write_leg_status
from .runtime import extract_revised_brief, parse_dispatch, parse_signoff, parse_verdict, signoff_adopts

LEG_FILE = re.compile(r"leg-\d+-([a-z]+)-([a-z-]+)\.md$", re.I)
PACK_NOTES = re.compile(r"_mike-pack-notes\.md$", re.I)
KIND_FROM_FILE = {"challenge": "brief-debate", "signoff": "sign-off", "sign-off": "sign-off"}

OFFICE_ACTIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("harvey", "proposal"): ("opens the matter", "proposal"),
    ("harvey", "rebuttal"): ("rules on Tyagi", "rebuttal"),
    ("harvey", "dispatch"): ("dispatches", "dispatch"),
    ("harvey", "sign-off"): ("signs off", "sign-off"),
    ("harvey", "conduct"): ("opens the room", "conduct"),
    ("harvey", "synthesize"): ("closes the room", "synthesize"),
    ("tyagi", "brief-debate"): ("interjects on the brief", "brief-debate"),
    ("tyagi", "viability"): ("gates the draft", "viability"),
    ("jessica", "office-take"): ("merit preview in the room", "office-take"),
    ("mike", "office-take"): ("drafting notes in the room", "office-take"),
    ("mike", "prep"): ("prep memo for Harvey", "prep"),
    ("mike", "task"): ("parallel task", "task"),
    ("mike", "draft"): ("hands up the draft", "draft"),
    ("jessica", "review"): ("Managing-partner read", "review"),
    ("mike", "pack"): ("deliverables", "pack"),
}


def parse_artifact_leg(path: Path) -> tuple[str, str]:
    if PACK_NOTES.search(path.name):
        return "mike", "pack"
    m = LEG_FILE.search(path.name)
    if not m:
        raise SystemExit(f"cannot parse leg artifact from {path.name!r}")
    persona = m.group(1).lower()
    kind = KIND_FROM_FILE.get(m.group(2).lower(), m.group(2).lower())
    return persona, kind


def _record_office(
    matter: Matter, actor: str, kind: str, path: Path, *, action: str, dispatch: str = ""
) -> None:
    rel = str(path.relative_to(matter.path))
    body = speech_from_artifact(actor, kind, path)
    if kind == "proposal" and "# Office" in body:
        body = body.split("# Brief", 1)[0].replace("# Office", "").strip()
    append_speech(matter, actor, body, action=action, dispatch=dispatch, artifact=rel)


def _artifact_dispatch(path: Path) -> str:
    if not path.is_file():
        return ""
    d = parse_dispatch(path.read_text(encoding="utf-8"))
    if not d:
        return ""
    return "jessica" if d == "donna" else d


def _apply_harvey_brief(matter: Matter, kind: str, out: Path) -> None:
    text = out.read_text(encoding="utf-8")
    if kind == "proposal":
        if "# Brief" in text:
            brief = text.split("# Brief", 1)[1].split("DISPATCH:", 1)[0].strip()
            matter.brief.write_text(brief + "\n", encoding="utf-8")
        else:
            matter.brief.write_text(text, encoding="utf-8")
    elif kind in ("rebuttal", "synthesize"):
        brief_body = (
            extract_revised_brief(text)
            if "Revised Brief" in text or "Objection Rulings" in text
            else text
        )
        if "Revised Brief" in text or "Objection Rulings" in text:
            matter.brief.write_text(brief_body.strip() + "\n", encoding="utf-8")


def finalize_recorded_leg(matter: Matter, persona: str, kind: str, out: Path) -> dict:
    """Post-write finalize — office soundboard, hop log, brief updates."""
    seed_office(matter)
    if not out.is_file():
        raise SystemExit(f"artifact missing: {out}")
    out = out.resolve()
    if matter.path not in out.parents and out != matter.path:
        raise SystemExit(f"artifact {out} is not under matter {matter.path}")

    model = model_for_leg(persona, kind, matter)
    dispatch = _artifact_dispatch(out)
    action_key = OFFICE_ACTIONS.get((persona, kind))
    if not action_key:
        raise SystemExit(f"no office action for {persona}/{kind}")
    action, hop_action = action_key

    result: dict = {
        "persona": persona,
        "kind": kind,
        "model": model,
        "artifact": str(out.relative_to(matter.path)),
        "dispatch": dispatch,
    }

    if persona == "harvey":
        _apply_harvey_brief(matter, kind, out)
        if kind == "sign-off":
            signoff = parse_signoff(out.read_text(encoding="utf-8")) or ""
            dispatch = "closed" if signoff_adopts(signoff) else "mike" if signoff == "REDRAFT" else dispatch
            if signoff == "APPROVED_WITH_RESIDUAL_RISK":
                action = "signs off with residual risk"
            elif signoff == "APPROVED":
                action = "signs off"
            elif signoff == "REDRAFT":
                action = "sends back to Mike"
            result["signoff"] = signoff
        if not dispatch:
            defaults = {"proposal": "tyagi", "rebuttal": "tyagi", "conduct": "tyagi", "synthesize": "tyagi", "dispatch": "mike"}
            dispatch = defaults.get(kind, dispatch)
        _record_office(matter, persona, kind, out, action=action, dispatch=dispatch)
        hop = log_hop(
            matter,
            actor="harvey",
            model=model,
            action=hop_action,
            artifact=str(out.relative_to(matter.path)),
            dispatch=dispatch,
        )
        result.update({"dispatch": dispatch, "hop": hop})
        return result

    verdict = parse_verdict(out.read_text(encoding="utf-8"))
    if kind in ("office-take", "task", "prep"):
        _record_office(matter, persona, kind, out, action=action, dispatch=dispatch)
        hop = log_hop(
            matter,
            actor=persona,
            model=model,
            action=hop_action,
            artifact=str(out.relative_to(matter.path)),
        )
        result.update({"hop": hop})
        return result
    if persona in ("tyagi", "jessica"):
        result["verdict"] = verdict.label
    _record_office(matter, persona, kind, out, action=action, dispatch=dispatch)
    hop = log_hop(
        matter,
        actor=persona,
        model=model,
        action=hop_action,
        artifact=str(out.relative_to(matter.path)),
        verdict=verdict.label if persona in ("tyagi", "jessica") else "",
        dispatch=dispatch,
    )
    if persona == "mike" and kind == "draft":
        audit_draft_file(matter, out)
    result.update({"hop": hop})
    return result


def record_leg(matter: Matter, artifact: str | Path, *, persona: str = "", kind: str = "") -> dict:
    out = Path(artifact)
    if not out.is_absolute():
        out = matter.path / out
    if not persona or not kind:
        p, k = parse_artifact_leg(out)
        persona = persona or p
        kind = kind or k
    return finalize_recorded_leg(matter, persona, kind, out)


def record_leg_json(matter: Matter, artifact: str | Path, **kw) -> str:
    return json.dumps(record_leg(matter, artifact, **kw), indent=2)


def leg_start(matter: Matter, persona: str, kind: str) -> None:
    seed_office(matter)
    write_leg_status(matter, persona, kind)
    append_leg_start(matter, persona, kind)


def leg_done(matter: Matter, persona: str | None = None, kind: str | None = None) -> None:
    clear_leg_status(matter, persona, kind)


def run_engine(matter: Matter, kind: str) -> dict:
    from .legs import adopt_work_product, lock_brief, lock_pre_draft

    seed_office(matter)
    if kind == "lock-brief":
        from .caps import brief_lock_cap_forced

        dest = lock_brief(matter, cap_forced=brief_lock_cap_forced(matter))
        return {"persona": "engine", "kind": "lock-brief", "artifact": str(dest.relative_to(matter.path))}
    if kind == "lock-pre-draft":
        from .caps import prep_lock_cap_forced

        dest = lock_pre_draft(matter, cap_forced=prep_lock_cap_forced(matter))
        return {"persona": "engine", "kind": "lock-pre-draft", "artifact": str(dest.relative_to(matter.path))}
    if kind == "adopt":
        from .runtime import parse_signoff
        from .state import _signoff_for_current_draft, latest_draft

        draft = latest_draft(matter)
        if not draft:
            raise SystemExit("no mike draft — cannot adopt")
        signoff = _signoff_for_current_draft(matter)
        residual = bool(signoff and parse_signoff(signoff.read_text(encoding="utf-8")) == "APPROVED_WITH_RESIDUAL_RISK")
        audit = audit_draft_file(matter, draft)
        dest = adopt_work_product(matter, draft, residual_risk=residual)
        matter.update_config(court=infer_court_id(matter), status="closed")
        return {
            "persona": "engine",
            "kind": "adopt",
            "artifact": str(dest.relative_to(matter.path)),
            "citation_audit": audit.get("notes", []),
        }
    if kind == "export":
        from .export import finish_deliverables

        out = finish_deliverables(matter)
        matter.update_config(export_done=True)
        seed_office(matter)
        append_speech(
            matter,
            "engine",
            "Deliverables built — DOCX, PDF, client pack.",
            action="export",
            dispatch="closed",
        )
        return {"persona": "engine", "kind": "export", **{k: v for k, v in out.items() if not k.endswith("_note")}}
    raise SystemExit(f"unknown engine action {kind!r} — use: lock-brief, lock-pre-draft, adopt, export")
