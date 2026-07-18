"""Live leg status — lawyers and Harvey poll this while subprocess legs run."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .matter import Matter

LEG_HINTS: dict[tuple[str, str], str] = {
    ("harvey", "proposal"): "opening brief — reading record, setting strategy",
    ("tyagi", "challenge"): "brief debate — maintainability",
    ("tyagi", "viability"): "viability gate on the draft",
    ("harvey", "rebuttal"): "ruling on Tyagi's objections",
    ("mike", "draft"): "drafting the work product",
    ("jessica", "review"): "merit review",
    ("jessica", "office-take"): "merit preview in the room",
    ("mike", "office-take"): "drafting notes in the room",
    ("mike", "prep"): "pre-draft plan with Harvey",
    ("harvey", "sign-off"): "final partner sign-off",
}


def status_path(matter: Matter) -> Path:
    return matter.path / "status.json"


def _load_status(matter: Matter) -> dict:
    p = status_path(matter)
    if not p.is_file():
        return {"running": []}
    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data.get("running"), list):
        return data
    # legacy single-leg shape
    if data.get("persona"):
        return {
            "running": [
                {
                    "persona": data["persona"],
                    "kind": data.get("kind", ""),
                    "hint": data.get("hint", ""),
                    "started_at": data.get("started_at", ""),
                }
            ]
        }
    return {"running": []}


def write_leg_status(matter: Matter, persona: str, kind: str) -> None:
    data = _load_status(matter)
    entry = {
        "persona": persona,
        "kind": kind,
        "hint": LEG_HINTS.get((persona, kind), kind),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    running = [r for r in data["running"] if not (r["persona"] == persona and r["kind"] == kind)]
    running.append(entry)
    status_path(matter).write_text(
        json.dumps({"phase": "running", "running": running}, indent=2) + "\n",
        encoding="utf-8",
    )


def clear_leg_status(matter: Matter, persona: str | None = None, kind: str | None = None) -> None:
    p = status_path(matter)
    if persona is None:
        if p.exists():
            p.unlink()
        return
    data = _load_status(matter)
    data["running"] = [
        r for r in data["running"]
        if not (r["persona"] == persona and (kind is None or r["kind"] == kind))
    ]
    if data["running"]:
        p.write_text(json.dumps({"phase": "running", "running": data["running"]}, indent=2) + "\n", encoding="utf-8")
    elif p.exists():
        p.unlink()
