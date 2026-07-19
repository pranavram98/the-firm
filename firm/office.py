"""The office — shared room transcript. Personas speak to each other here, not just to files."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path

from .tokens import office_max_chars

OFFICE_HEADER = """# The office

Everyone reads this room before they speak. Respond to what was just said — interject,
push back, rule, draft. Artifacts still land in `brief-debate/` and `round-*/`; this
file is the conversation.

---

"""

DISPLAY = {
    "harvey": "Harvey",
    "tyagi": "Tyagi",
    "mike": "Mike",
    "jessica": "Jessica",
    "engine": "Firm",
}

_office_lock = threading.Lock()


def office_path(matter: Matter) -> Path:
    return matter.path / "office.md"


def seed_office(matter: Matter) -> None:
    p = office_path(matter)
    if p.exists():
        return
    obj = matter.config.get("objective", "")
    p.write_text(
        OFFICE_HEADER
        + f"**Firm** · matter opened — {obj}\n\n",
        encoding="utf-8",
    )


def append_leg_start(matter: Matter, persona: str, kind: str) -> None:
    name = DISPLAY.get(persona, persona.title())
    from .progress import LEG_HINTS

    hint = LEG_HINTS.get((persona, kind), kind)
    append_speech(
        matter,
        "engine",
        f"**{name}** is working on *{hint}*. "
        "Large records can take several minutes — the room updates when this leg finishes.",
        action="leg running",
    )


def append_speech(
    matter: Matter,
    actor: str,
    body: str,
    *,
    action: str = "",
    dispatch: str = "",
    artifact: str = "",
) -> None:
    seed_office(matter)
    ts = datetime.now(timezone.utc).strftime("%H:%M")
    name = DISPLAY.get(actor, actor.title())
    meta = action or "speaks"
    tail = ""
    if dispatch:
        tail += f"\n\n→ *sends to {DISPLAY.get(dispatch, dispatch)}*"
    if artifact:
        tail += f"\n\n*(artifact: `{artifact}`)*"
    block = f"**{name}** · {meta} · {ts}\n\n{body.strip()}{tail}\n\n---\n\n"
    with _office_lock:
        with office_path(matter).open("a", encoding="utf-8") as f:
            f.write(block)


def recent_transcript(matter: Matter, *, max_chars: int | None = None) -> str:
    cap = max_chars if max_chars is not None else office_max_chars(matter)
    p = office_path(matter)
    if not p.exists():
        return "(office empty — you are first in the room)"
    text = p.read_text(encoding="utf-8")
    if len(text) <= cap:
        return text
    return "…(earlier conversation truncated)…\n\n" + text[-cap:]


def office_prompt_block(matter: Matter, *, inline: bool = True) -> str:
    if not inline:
        return "THE OFFICE: read `office.md` — respond to the last speaker.\n\n"
    return (
        "THE OFFICE (read this first — you are in the room; respond to the last speaker):\n"
        f"{recent_transcript(matter)}\n\n"
        "Speak directly: address the last objection, ruling, or draft. Then do your leg work.\n\n"
    )


def speech_from_artifact(persona: str, kind: str, path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if kind in ("office-take", "proposal", "rebuttal", "sign-off") and "# Office" in text:
        block = text.split("# Office", 1)[1].split("#", 1)[0].strip()
        if block:
            return block
    if kind == "draft":
        return "I've drafted the work product — full text in the artifact file."
    if kind == "pack":
        return "Client pack HTML updated — ready for PDF render."
    return text
