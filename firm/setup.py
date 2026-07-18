"""One-time IT setup — check deps, confirm install, print lawyer start line."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .agents_sync import sync_claude_agents, sync_codex_agents, sync_skill_bundle
from .home import (
    claude_skill_dir,
    codex_skill_dir,
    ensure_matters_root,
    firm_home,
    load_config,
    save_config,
)

REQUIRED = (
    ("claude", "Claude Code — Claude surface"),
)
OPTIONAL = (
    ("codex", "Codex — Codex surface"),
    ("pandoc", "Word export (.docx)"),
    ("node", "PDF export & client pack"),
)

LAWYER_START_CLAUDE = """
Lawyer (Claude Code):
  1. Open Claude Code — any folder on your machine
  2. /the-firm — describe the case; Harvey spawns Tyagi/Mike/Jessica as visible subagents

Harvey narrates from office.md; deliverables under ~/Documents/firm-matters/.
""".strip()

LAWYER_START_CODEX = """
Lawyer (Codex):
  1. Open Codex anywhere (after firm install-skill codex)
  2. $the-firm — describe the case; Harvey spawns Tyagi/Mike/Jessica as visible subagents

Same deliverables under ~/Documents/firm-matters/.
""".strip()

LAWYER_START = LAWYER_START_CLAUDE  # default setup banner


def matters_path() -> str:
    return str(ensure_matters_root())


def _link_tree(src: Path, dest: Path) -> None:
    src = src.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink():
        if dest.resolve() == src:
            print(f"linked {dest.name} → {src} (already)")
            return
        dest.unlink()
    elif dest.exists():
        shutil.rmtree(dest)
    dest.symlink_to(src)
    print(f"linked {dest} → {src}")


def install_skill(surface: str = "claude") -> None:
    home = firm_home()
    if not home:
        raise SystemExit("FIRM_HOME / the-firm checkout not found — clone ~/Documents/the-firm")

    surface = surface.lower()
    if surface == "claude":
        sync_skill_bundle("claude")
        skill_src = claude_skill_dir(home)
        _link_tree(skill_src, Path.home() / ".claude" / "skills" / "the-firm")
        for p in sync_claude_agents("claude", dest=Path.home() / ".claude" / "agents"):
            print(f"agent  {p.name} → ~/.claude/agents/")
    elif surface == "codex":
        sync_skill_bundle("codex")
        skill_src = codex_skill_dir(home)
        _link_tree(skill_src, Path.home() / ".agents" / "skills" / "the-firm")
        for p in sync_codex_agents("codex", dest=Path.home() / ".agents" / "agents"):
            print(f"agent  {p.name} → ~/.agents/agents/")
    else:
        raise SystemExit(f"unknown surface {surface!r} — use: claude, codex")


def _ok(name: str) -> bool:
    return shutil.which(name) is not None


def _firm_version() -> str | None:
    try:
        out = subprocess.run(
            ["firm", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        line = (out.stdout or out.stderr or "").strip().splitlines()
        return line[0] if line else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _skill_status(home: Path | None) -> tuple[str, str]:
    global_claude = Path.home() / ".claude" / "skills" / "the-firm" / "SKILL.md"
    global_codex = Path.home() / ".agents" / "skills" / "the-firm" / "SKILL.md"
    if global_claude.is_file():
        claude_line = "  /the-firm global — Claude works in any folder"
    elif home and (home / ".claude" / "skills" / "the-firm" / "SKILL.md").is_file():
        claude_line = "  /the-firm repo only — run: firm install-skill claude"
    else:
        claude_line = "  /the-firm missing — clone repo and run firm setup"
    if global_codex.is_file():
        codex_line = "  $the-firm global — Codex skill installed"
    elif home and (home / ".agents" / "skills" / "the-firm" / "SKILL.md").is_file():
        codex_line = "  $the-firm repo only — run: firm install-skill codex"
    else:
        codex_line = "  $the-firm missing — run: firm install-skill codex"
    return claude_line, codex_line


def run_setup(*, surface: str | None = None) -> int:
    home = firm_home()
    print("the-firm setup\n")

    if home:
        print(f"  repo     {home}")
    else:
        print("  repo     not found — clone to ~/Documents/the-firm or set FIRM_HOME")

    ver = _firm_version()
    if ver:
        print(f"  firm     {ver}")
    else:
        print("  firm     not on PATH — run: cd ~/Documents/the-firm && uv tool install .")

    missing_required = []
    for bin_name, label in REQUIRED:
        mark = "ok" if _ok(bin_name) else "MISSING"
        print(f"  {bin_name:8} {mark:8} {label}")
        if mark == "MISSING":
            missing_required.append(bin_name)

    for bin_name, label in OPTIONAL:
        mark = "ok" if _ok(bin_name) else "optional"
        print(f"  {bin_name:8} {mark:8} {label}")

    if home:
        print()
        if surface == "codex":
            install_skill("codex")
        elif surface == "both":
            install_skill("claude")
            install_skill("codex")
        else:
            install_skill("claude")

    claude_line, codex_line = _skill_status(home)
    print(claude_line)
    print(codex_line)

    work = ensure_matters_root()
    save_config({**load_config(), "matters": str(work)})
    print(f"  work     {work}  (matters & deliverables — outside the repo)")

    if home:
        try:
            for p in sync_skill_bundle("claude"):
                print(f"  bundle   claude/{p.name}")
            for p in sync_skill_bundle("codex"):
                print(f"  bundle   codex/{p.name}")
        except SystemExit:
            pass

    print(f"\n{LAWYER_START}\n")
    print(f"{LAWYER_START_CODEX}\n")

    if missing_required:
        print(f"Fix missing: {', '.join(missing_required)}")
        return 1
    if not ver:
        return 1
    return 0
