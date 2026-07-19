"""firm — scaffold, handoff state, export."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .export import finish_deliverables
from .handoff import next_handoff_json
from .matter import Matter
from .pack import pack_next_json
from .record import leg_done, leg_start, record_leg_json, run_engine
from .scaffold import open_matter
from .setup import install_skill, matters_path, run_setup

HELP = """
the-firm — one firm, one matter, subagent handoffs

  firm open -o "objective" [-t title] [--surface claude|codex] <files>
  firm next <matter-path>              next leg JSON (prompts in .firm/legs/ by default)
  firm next --embed-prompts <matter>   inline full prompts in JSON (debug only) (prompts in .firm/legs/ by default)
  firm next --embed-prompts <matter>   inline full prompts in JSON (debug only)
  firm leg-start <matter> <persona> <kind>
  firm record-leg <matter> <artifact>
  firm engine <matter> lock-brief|lock-pre-draft|adopt|export
  firm pack-next <matter>              mike client-pack subagent leg
  firm export <matter-path>            docx, pdf, pack

Claude: /the-firm   Codex: $the-firm   → spawn subagents → firm record-leg

Setup:  firm setup | firm install-skill claude|codex
"""


def _resolve_matter_path(arg: str) -> Matter:
    return Matter.resolve(arg)


def _resolve_matter(
    objective: str,
    sources: list[Path],
    *,
    cause_title: str,
    slug: str | None,
    surface: str,
) -> Matter:
    paths = [p.expanduser().resolve() for p in sources]
    if len(paths) == 1 and (paths[0] / "matter.yaml").is_file():
        return Matter.resolve(str(paths[0]))
    return open_matter(objective, paths, cause_title=cause_title, slug=slug, surface=surface)


def main(argv: list[str] | None = None) -> None:
    argv = list(argv if argv is not None else sys.argv[1:])

    if argv and argv[0] == "setup":
        sys.exit(run_setup())

    if argv and argv[0] == "matters-path":
        print(matters_path())
        return

    if argv and argv[0] == "install-skill":
        rest = [a for a in argv[1:] if not a.startswith("-")]
        install_skill(rest[0] if rest else "claude")
        return

    if argv and argv[0] == "sync-agents":
        from .agents_sync import sync_claude_agents, sync_codex_agents, sync_skill_bundle

        surface = "codex" if "--surface" in argv and "codex" in argv else "claude"
        for p in sync_skill_bundle(surface):
            print(f"bundled {p}")
        if surface == "codex":
            for p in sync_codex_agents(surface):
                print(f"synced {p}")
        else:
            for p in sync_claude_agents(surface):
                print(f"synced {p}")
        return

    if argv and argv[0] == "next":
        embed = "--embed-prompts" in argv
        paths = [a for a in argv[1:] if a != "--embed-prompts"]
        if not paths:
            raise SystemExit("usage: firm next [--embed-prompts] <matter-path>")
        print(next_handoff_json(_resolve_matter_path(paths[0]), embed_prompts=embed))
        return

    if argv and argv[0] == "leg-start":
        if len(argv) < 4:
            raise SystemExit("usage: firm leg-start <matter-path> <persona> <kind>")
        matter = _resolve_matter_path(argv[1])
        leg_start(matter, argv[2], argv[3])
        print(json.dumps({"started": True, "persona": argv[2], "kind": argv[3]}))
        return

    if argv and argv[0] == "record-leg":
        if len(argv) < 3:
            raise SystemExit("usage: firm record-leg <matter-path> <artifact-rel-path>")
        matter = _resolve_matter_path(argv[1])
        result = json.loads(record_leg_json(matter, argv[2]))
        leg_done(matter, result.get("persona"), result.get("kind"))
        print(json.dumps(result, indent=2))
        return

    if argv and argv[0] == "engine":
        if len(argv) < 3:
            raise SystemExit("usage: firm engine <matter-path> lock-brief|lock-pre-draft|adopt|export")
        matter = _resolve_matter_path(argv[1])
        print(json.dumps(run_engine(matter, argv[2]), indent=2))
        return

    if argv and argv[0] == "pack-next":
        if len(argv) < 2:
            raise SystemExit("usage: firm pack-next <matter-path>")
        print(pack_next_json(_resolve_matter_path(argv[1])))
        return

    if argv and argv[0] == "export":
        if len(argv) < 2:
            raise SystemExit("usage: firm export <matter-path>")
        matter = _resolve_matter_path(argv[1])
        exports = finish_deliverables(matter)
        for k, v in exports.items():
            if v and not k.endswith("_note"):
                print(f"{k}: {v}")
        return

    if argv and argv[0] == "open":
        ap = argparse.ArgumentParser(prog="firm open")
        ap.add_argument("-o", "--objective", required=True)
        ap.add_argument("-t", "--cause-title", default="")
        ap.add_argument("--slug", default=None)
        ap.add_argument("--surface", choices=("claude", "codex"), default="claude")
        ap.add_argument("sources", nargs="+")
        args = ap.parse_args(argv[1:])
        matter = _resolve_matter(
            args.objective,
            [Path(p) for p in args.sources],
            cause_title=args.cause_title,
            slug=args.slug,
            surface=args.surface,
        )
        print(f"opened {matter.path}")
        print(f"surface {args.surface}")
        print(next_handoff_json(matter))
        return

    if not argv or argv[0] in ("-h", "--help", "help"):
        print(HELP.strip())
        return

    if argv[0] in ("--version", "-V"):
        print(f"firm {__version__}")
        return

    raise SystemExit(f"unknown command {argv[0]!r} — run firm --help")


if __name__ == "__main__":
    main()
