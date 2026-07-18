"""Surface casts — benchmark-grounded, one family per session."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .personas import Persona, get_personas

if TYPE_CHECKING:
    from .matter import Matter

VALID_SURFACES = frozenset({"claude", "codex"})

# Benchmark refs (Jul 2026 GA):
#   Claude — Harvey Legal Agent Benchmark all-pass: Fable 13.3%, Opus 10.4%, Sonnet 8.92%
#            LegalBench: Fable 88.56%. BigLaw Bench drafting: Fable 93.4%
#   Codex  — AA Coding Index: Sol 80, Terra 77.4, Luna 74.6
#            Terminal-Bench 2.1: Sol 88.8%, Terra 87.4%, Luna 84.7%
#            SWE-bench Pro: Sol 64.6%, Terra 63.4%, Luna 62.7%
#
# Sol → Harvey only (both surfaces' top partner tier).
# Fable → Harvey only on Claude.

SURFACES: dict[str, dict] = {
    "claude": {
        "family": "claude",
        "label": "Claude Code",
        "orchestrator": "harvey",
        "harvey": {"model": "claude-fable-5", "alias": "fable"},
        "tyagi": {"model": "claude-opus-4-8", "alias": "opus"},
        "mike": {"model": "claude-sonnet-5", "alias": "sonnet"},
        "jessica": {"model": "claude-opus-4-8", "alias": "opus"},
        "leg_models": {
            ("harvey", "proposal"): "claude-fable-5",
            ("harvey", "conduct"): "claude-fable-5",
            ("harvey", "synthesize"): "claude-fable-5",
            ("harvey", "rebuttal"): "claude-fable-5",
            ("harvey", "dispatch"): "claude-fable-5",
            ("harvey", "sign-off"): "claude-fable-5",
            ("tyagi", "brief-debate"): "claude-opus-4-8",
            ("tyagi", "viability"): "claude-opus-4-8",
            ("mike", "draft"): "claude-sonnet-5",
            ("mike", "pack"): "claude-sonnet-5",
            ("jessica", "review"): "claude-opus-4-8",
            ("jessica", "office-take"): "claude-opus-4-8",
            ("mike", "office-take"): "claude-sonnet-5",
            ("mike", "task"): "claude-sonnet-5",
        },
    },
    "codex": {
        "family": "codex",
        "label": "Codex",
        "orchestrator": "harvey",
        "harvey": {"model": "gpt-5.6-sol", "alias": "sol"},
        "tyagi": {"model": "gpt-5.6-terra", "alias": "terra"},
        "mike": {"model": "gpt-5.6-terra", "alias": "terra"},
        "jessica": {"model": "gpt-5.6-terra", "alias": "terra"},
        "leg_models": {
            ("harvey", "proposal"): "gpt-5.6-sol",
            ("harvey", "conduct"): "gpt-5.6-sol",
            ("harvey", "synthesize"): "gpt-5.6-sol",
            ("harvey", "rebuttal"): "gpt-5.6-sol",
            ("harvey", "dispatch"): "gpt-5.6-sol",
            ("harvey", "sign-off"): "gpt-5.6-sol",
            ("tyagi", "brief-debate"): "gpt-5.6-terra",
            ("tyagi", "viability"): "gpt-5.6-terra",
            ("mike", "draft"): "gpt-5.6-terra",
            ("mike", "pack"): "gpt-5.6-luna",
            ("jessica", "review"): "gpt-5.6-terra",
            ("jessica", "office-take"): "gpt-5.6-terra",
            ("mike", "office-take"): "gpt-5.6-terra",
            ("mike", "task"): "gpt-5.6-terra",
        },
    },
}

HARVEY_LIVE = {
    **SURFACES["claude"]["harvey"],
    "mode": "live",
    "surface": "claude-code",
    "hops": ("plan", "brief-rebuttal", "dispatch", "sign-off"),
}


def subagent_model(surface: str, persona: str) -> str:
    sc = SURFACES[surface][persona]
    return sc.get("alias") or sc["model"]


@dataclass
class ResolvedLeg:
    persona: Persona
    model: str
    hop: int


def surface_for_matter(matter: Matter | None = None) -> str:
    if matter:
        s = matter.config.get("surface")
        if s in VALID_SURFACES:
            return s
    env = os.environ.get("FIRM_SURFACE", "").lower()
    if env in VALID_SURFACES:
        return env
    return "claude"


def surface_cast(surface: str | None = None, matter: Matter | None = None) -> dict:
    s = surface or surface_for_matter(matter)
    if s not in SURFACES:
        raise SystemExit(f"unknown surface {s!r} — use: claude, codex")
    return SURFACES[s]


def family_for(surface: str | None = None, matter: Matter | None = None) -> str:
    return surface_cast(surface, matter)["family"]


def default_matter_cast(surface: str = "claude") -> dict:
    sc = SURFACES[surface]
    out: dict = {"surface": surface, "harvey": dict(sc["harvey"])}
    for name in ("tyagi", "mike", "jessica"):
        out[name] = {"model": sc[name]["model"]}
    return out


def cast_for_matter(matter: Matter) -> dict:
    surface = surface_for_matter(matter)
    sc = surface_cast(surface)
    cfg = matter.config.get("cast") or {}
    return {
        "surface": surface,
        "family": sc["family"],
        "harvey": {**sc["harvey"], **cfg.get("harvey", {})},
        "delegated": {
            name: {**sc[name], **cfg.get(name, {})} for name in ("tyagi", "mike", "jessica")
        },
    }


def model_for_leg(
    persona_name: str, kind: str, matter: Matter | None = None, *, surface: str | None = None
) -> str:
    sc = surface_cast(surface, matter)
    key = (persona_name, kind)
    if matter:
        cfg = matter.config.get("cast", {}).get(persona_name, {})
        if cfg.get("model"):
            return cfg["model"]
    return sc["leg_models"].get(key, sc.get(persona_name, {}).get("model", "default"))


def resolve_leg_persona(matter: Matter, persona_name: str, kind: str) -> Persona:
    local = matter.path / "personas"
    persona = get_personas([persona_name], extra_dir=local)[0]
    model = model_for_leg(persona_name, kind, matter)
    backend = family_for(matter=matter)
    persona = replace(persona, model=model, backend=backend)
    persona.validate()
    return persona


def current_hop(matter: Matter) -> int:
    log = matter.path / "hop-log.md"
    if not log.exists():
        return 0
    import re

    nums = [int(n) for n in re.findall(r"^## Hop (\d+)", log.read_text(encoding="utf-8"), re.M)]
    return max(nums) if nums else 0


def log_hop(
    matter: Matter,
    *,
    actor: str,
    model: str,
    action: str,
    artifact: str = "",
    verdict: str = "",
    dispatch: str = "",
) -> int:
    log = matter.path / "hop-log.md"
    hop = current_hop(matter) + 1
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = "" if log.exists() else "# Hop Log\n\n"
    lines = [
        header,
        f"## Hop {hop} — {ts}\n",
        f"- **actor**: {actor} ({model})\n",
        f"- **action**: {action}\n",
    ]
    if artifact:
        lines.append(f"- **artifact**: {artifact}\n")
    if verdict:
        lines.append(f"- **verdict**: {verdict}\n")
    if dispatch:
        lines.append(f"- **dispatch**: {dispatch}\n")
    lines.append("\n")
    with log.open("a", encoding="utf-8") as f:
        f.write("".join(lines))
    return hop
