"""Build subagent files from personas + surface cast."""

from __future__ import annotations

import re
from pathlib import Path

from .cast import SURFACES, subagent_model
from .home import claude_skill_agents_dir, codex_agents_dir, codex_skill_agents_dir, firm_home
from .personas import parse_persona

FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.S)

AGENT_HEADER = """---
name: {name}
description: {description}
tools: {tools}
model: {model}
---

Harvey delegated this leg — you are a **visible subagent** ({surface}).

Before writing:
- Read `sources/index.md`, then `brief.md` and `harvey-context.md`
- Read `office.md` — respond to the last speaker
- Read the leg prompt file Harvey points you at (`.firm/legs/*.prompt.md`) — it states **read depth** for this leg
- **Prep + brief-debate:** read substantive filings in full (index preview ≠ read); split large scans
- **Review legs:** draft + index first; open `sources/` when a pin or quote needs the original

Write your artifact to the **OUT** path exactly (under the matter folder).
Do **not** append `office.md` — Harvey runs `firm record-leg` after you return.

"""

DEFAULT_TOOLS = "Read, Grep, Glob, Write, Edit"
AGENT_TOOLS = {
    # Mike splits scanned records into page-range PDFs and renders/fetches during prep.
    "mike": "Read, Grep, Glob, Write, Edit, Bash",
}

DESCRIPTIONS = {
    "tyagi": "Procedure hunter — lapses in client's favour; brief debate and draft recall. Returns VERDICT and DISPATCH.",
    "mike": "Associate drafter — executes locked brief. Returns DISPATCH.",
    "jessica": "Merit reviewer — cold managing-partner read. Returns VERDICT and DISPATCH.",
}

DELEGATE_NAMES = ("tyagi", "mike", "jessica")


def _persona_body(home: Path, name: str) -> str:
    persona = parse_persona(home / "personas" / f"{name}.md")
    return persona.prompt.strip()


def _write_agent(home: Path, surface: str, name: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    body = _persona_body(home, name)
    sc = SURFACES[surface]
    text = AGENT_HEADER.format(
        name=name,
        description=DESCRIPTIONS[name],
        tools=AGENT_TOOLS.get(name, DEFAULT_TOOLS),
        model=subagent_model(surface, name),
        surface=sc["label"],
    ) + body + "\n"
    dest = dest_dir / f"{name}.md"
    dest.write_text(text, encoding="utf-8")
    return dest


def sync_claude_agents(surface: str = "claude", *, dest: Path | None = None) -> list[Path]:
    home = firm_home()
    if not home:
        raise SystemExit("FIRM_HOME / the-firm checkout not found")
    if surface not in SURFACES:
        raise SystemExit(f"unknown surface {surface!r}")
    agents_dir = dest or (home / ".claude" / "agents")
    return [_write_agent(home, surface, name, agents_dir) for name in DELEGATE_NAMES]


def sync_codex_agents(surface: str = "codex", *, dest: Path | None = None) -> list[Path]:
    home = firm_home()
    if not home:
        raise SystemExit("FIRM_HOME / the-firm checkout not found")
    if surface not in SURFACES:
        raise SystemExit(f"unknown surface {surface!r}")
    agents_dir = dest or codex_agents_dir(home)
    return [_write_agent(home, surface, name, agents_dir) for name in DELEGATE_NAMES]


# backward-compat alias
sync_codex_delegates = sync_codex_agents


def sync_skill_bundle(surface: str = "claude") -> list[Path]:
    home = firm_home()
    if not home:
        raise SystemExit("FIRM_HOME / the-firm checkout not found")
    if surface == "claude":
        return sync_claude_agents(surface, dest=claude_skill_agents_dir(home))
    if surface == "codex":
        return sync_codex_agents(surface, dest=codex_skill_agents_dir(home))
    raise SystemExit(f"unknown surface {surface!r}")
