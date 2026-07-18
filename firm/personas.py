"""Persona loading and validation.

A persona is one markdown file: YAML frontmatter (binding) + body (role prompt).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .home import personas_dir

PERSONAS_DIR = personas_dir()

VALID_BACKENDS = {"claude", "codex"}
VALID_ROLES = {"strategist", "drafter", "reviewer"}
VALID_TOOLS = {"read-only", "workspace-write"}

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.S)


@dataclass
class Persona:
    name: str
    role: str
    prompt: str
    backend: str = ""
    model: str = "default"
    tools: str = "read-only"
    fresh_context: bool = True
    verdict: bool = False
    path: Path | None = field(default=None, repr=False)

    def validate(self) -> None:
        problems = []
        if self.backend and self.backend not in VALID_BACKENDS:
            problems.append(f"backend must be one of {sorted(VALID_BACKENDS)}, got {self.backend!r}")
        if self.role not in VALID_ROLES:
            problems.append(f"role must be one of {sorted(VALID_ROLES)}, got {self.role!r}")
        if self.tools not in VALID_TOOLS:
            problems.append(f"tools must be one of {sorted(VALID_TOOLS)}, got {self.tools!r}")
        if not self.prompt.strip():
            problems.append("role prompt body is empty")
        if self.role == "reviewer" and not self.verdict:
            problems.append("reviewers must set verdict: true (runtime parses VERDICT lines)")
        if problems:
            raise ValueError(f"persona {self.name!r}: " + "; ".join(problems))


def parse_persona(path: Path) -> Persona:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path}: missing YAML frontmatter (--- ... ---)")
    meta = yaml.safe_load(m.group(1)) or {}
    persona = Persona(
        name=meta.get("name", path.stem),
        backend=meta.get("backend", ""),
        role=meta.get("role", "reviewer"),
        model=str(meta.get("model", "default")),
        tools=meta.get("tools", "read-only"),
        fresh_context=bool(meta.get("fresh_context", True)),
        verdict=bool(meta.get("verdict", False)),
        prompt=m.group(2).strip(),
        path=path,
    )
    persona.validate()
    return persona


def load_personas(extra_dir: Path | None = None) -> dict[str, Persona]:
    """Load repo personas, overlaid with any matter-local personas."""
    personas: dict[str, Persona] = {}
    dirs = [PERSONAS_DIR] + ([extra_dir] if extra_dir and extra_dir.is_dir() else [])
    for d in dirs:
        for f in sorted(d.glob("*.md")):
            p = parse_persona(f)
            personas[p.name] = p
    return personas


def get_personas(names: list[str], extra_dir: Path | None = None) -> list[Persona]:
    available = load_personas(extra_dir)
    missing = [n for n in names if n not in available]
    if missing:
        raise SystemExit(
            f"unknown persona(s): {', '.join(missing)} — available: {', '.join(sorted(available))}"
        )
    return [available[n] for n in names]


SCAFFOLD = """---
name: {name}
backend: {backend}
model: default
role: {role}
tools: read-only
fresh_context: true
verdict: {verdict}
---
You are {title}. Describe the lens this persona applies, what it hunts for,
and the shape of its output.
{verdict_note}"""


def scaffold_persona(name: str, backend: str, role: str) -> Path:
    path = PERSONAS_DIR / f"{name}.md"
    if path.exists():
        raise SystemExit(f"persona already exists: {path}")
    verdict = role == "reviewer"
    note = (
        "\nEnd with exactly one line:\nVERDICT: CLEARED\nor\nVERDICT: MATERIAL OBJECTIONS (n)\n"
        if verdict
        else ""
    )
    path.write_text(
        SCAFFOLD.format(
            name=name,
            backend=backend,
            role=role,
            verdict=str(verdict).lower(),
            title=name.title(),
            verdict_note=note,
        ),
        encoding="utf-8",
    )
    return path
