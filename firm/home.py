"""Where the firm lives: resolve personas/, templates/, and matters/ regardless of
whether firm runs from a source checkout or an installed wheel."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

_PKG = Path(__file__).resolve().parent
_DATA = _PKG / "data"  # personas/templates shipped inside the wheel
DEFAULT_MATTERS = Path.home() / "Documents" / "firm-matters"


def config_path() -> Path:
    return Path.home() / ".config" / "the-firm" / "config.yaml"


def load_config() -> dict:
    p = config_path()
    if not p.is_file():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def save_config(cfg: dict) -> None:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")


def ensure_matters_root(path: Path | None = None) -> Path:
    root = (path or matters_root()).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root


def firm_home() -> Path | None:
    """The repo checkout, if one can be found: FIRM_HOME env, the source tree this
    module sits in, or the default clone location."""
    env = os.environ.get("FIRM_HOME")
    if env:
        return Path(env).expanduser()
    for cand in (_PKG.parent, Path.home() / "Documents" / "the-firm"):
        if (cand / "personas").is_dir() and (cand / "templates").is_dir():
            return cand
    return None


def personas_dir() -> Path:
    home = firm_home()
    return (home / "personas") if home else (_DATA / "personas")


def templates_dir() -> Path:
    home = firm_home()
    return (home / "templates") if home else (_DATA / "templates")


def skills_dir() -> Path:
    home = firm_home()
    return (home / ".claude" / "skills") if home else (_DATA / "skills")


def claude_skill_dir(home: Path | None = None) -> Path:
    root = home or firm_home()
    if root:
        return root / ".claude" / "skills" / "the-firm"
    return _DATA / "skills" / "the-firm"


def claude_skill_agents_dir(home: Path | None = None) -> Path:
    return claude_skill_dir(home) / "agents"


def codex_skills_dir(home: Path | None = None) -> Path:
    root = home or firm_home()
    if root:
        return root / ".agents" / "skills"
    return _DATA / "codex-skills"


def codex_skill_dir(home: Path | None = None) -> Path:
    return codex_skills_dir(home) / "the-firm"


def codex_skill_agents_dir(home: Path | None = None) -> Path:
    return codex_skill_dir(home) / "agents"


def codex_agents_dir(home: Path | None = None) -> Path:
    root = home or firm_home()
    if root:
        return root / ".agents" / "agents"
    return _DATA / "codex-agents"


def codex_skill_delegates_dir(home: Path | None = None) -> Path:
    """Deprecated — use codex_skill_agents_dir."""
    return codex_skill_agents_dir(home)


def matters_root() -> Path:
    env = os.environ.get("FIRM_MATTERS")
    if env:
        return Path(env).expanduser()
    cfg = load_config().get("matters")
    if cfg:
        return Path(cfg).expanduser()
    return DEFAULT_MATTERS
