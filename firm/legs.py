"""Brief lock, adopt, and matter helpers — legs run in-session via subagents."""

from __future__ import annotations

from pathlib import Path

from .cast import log_hop, model_for_leg
from .matter import Matter
from .office import append_speech, seed_office


def _debate_dir(matter: Matter) -> Path:
    d = matter.path / "brief-debate"
    d.mkdir(exist_ok=True)
    return d


def lock_brief(matter: Matter, *, cap_forced: bool = False) -> Path:
    debate = _debate_dir(matter)
    dest = debate / "final-brief.md"
    dest.write_text(matter.brief.read_text(encoding="utf-8"), encoding="utf-8")
    matter.update_config(brief_debate="closed")
    seed_office(matter)
    msg = "Brief locked (cap — residual procedure accepted)." if cap_forced else "Brief locked."
    append_speech(matter, "engine", msg, action="lock-brief", dispatch="mike")
    log_hop(
        matter,
        actor="harvey",
        model=model_for_leg("harvey", "dispatch", matter),
        action="lock-brief",
        artifact="brief-debate/final-brief.md",
    )
    return dest


def lock_pre_draft(matter: Matter, *, cap_forced: bool = False) -> Path:
    prep = matter.path / "draft-prep"
    prep.mkdir(exist_ok=True)
    dest = prep / "prep-cleared.md"
    note = "Pre-draft cleared under cap — residual prep gaps accepted.\n" if cap_forced else "Pre-draft cleared — Mike may draft final work product.\n"
    dest.write_text(note, encoding="utf-8")
    matter.update_config(pre_draft="closed")
    seed_office(matter)
    msg = "Prep cleared (cap)." if cap_forced else "Prep cleared. Mike drafts."
    append_speech(matter, "engine", msg, action="lock-pre-draft", dispatch="mike")
    log_hop(
        matter,
        actor="harvey",
        model=model_for_leg("harvey", "dispatch", matter),
        action="lock-pre-draft",
        artifact="draft-prep/prep-cleared.md",
    )
    return dest


def adopt_work_product(matter: Matter, draft: Path, *, residual_risk: bool = False) -> Path:
    matter.final_dir.mkdir(exist_ok=True)
    matter.work_product.write_text(draft.read_text(encoding="utf-8"), encoding="utf-8")
    matter.update_config(status="closed")
    seed_office(matter)
    msg = "Signed off with residual risk. Work product adopted." if residual_risk else "Signed off. Work product adopted."
    append_speech(matter, "harvey", msg, action="sign-off", dispatch="closed")
    if residual_risk:
        _append_residual_decision_log(matter)
    return matter.work_product


def _append_residual_decision_log(matter: Matter) -> None:
    from datetime import datetime, timezone

    from .home import templates_dir

    matter.final_dir.mkdir(exist_ok=True)
    log = matter.decision_log
    if not log.is_file():
        tpl = templates_dir() / "decision-log.md"
        log.write_text(
            tpl.read_text(encoding="utf-8") if tpl.is_file() else "# Decision Log\n\n",
            encoding="utf-8",
        )
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = (
        f"\n## {stamp} — Partner sign-off with residual risk\n\n"
        "Engine round cap reached or partner accepted open items.\n"
    )
    log.write_text(log.read_text(encoding="utf-8").rstrip() + entry + "\n", encoding="utf-8")
