"""Client pack — Mike subagent fills HTML; export renders PDFs."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .cast import model_for_leg
from .matter import TEMPLATES_DIR, Matter
from .prompts import mike_pack

PACK_TEMPLATES = TEMPLATES_DIR / "briefing-pack"

DOCS = {
    "memo": "Briefing Memo",
    "notes": "Argument Notes",
    "2pp": "Client Briefing (2pp)",
    "reftable": "Reference Table",
}
CLIENT_DOCS = ["memo", "notes", "2pp", "reftable"]
SKELETONS = {
    "memo": "briefing-memo.html",
    "notes": "argument-notes.html",
    "2pp": "client-briefing-2pp.html",
    "reftable": "reference-table.html",
}


def scaffold_pack(matter: Matter, docs: list[str]) -> Path:
    pack = matter.final_dir / "pack"
    pack.mkdir(exist_ok=True)
    shutil.copyfile(PACK_TEMPLATES / "styles.css", pack / "styles.css")
    render = (PACK_TEMPLATES / "render.js").read_text(encoding="utf-8")
    cfg = matter.config
    render = render.replace("{{CAUSE_TITLE}}", cfg.get("cause_title") or cfg.get("slug", ""))
    render = render.replace("{{FILES}}", ", ".join(f"'{DOCS[d]}'" for d in docs))
    (pack / "render.js").write_text(render, encoding="utf-8")
    for d in docs:
        target = pack / f"{DOCS[d]}.html"
        if not target.exists():
            shutil.copyfile(PACK_TEMPLATES / SKELETONS[d], target)
    return pack


def _pack_ready(pack: Path) -> bool:
    memo = pack / f"{DOCS['memo']}.html"
    skeleton = PACK_TEMPLATES / SKELETONS["memo"]
    if not memo.is_file() or not skeleton.is_file():
        return False
    return memo.stat().st_size > skeleton.stat().st_size + 200


def pack_ready(matter: Matter) -> bool:
    pack = matter.final_dir / "pack"
    return _pack_ready(pack) if pack.is_dir() else False


def pack_next(matter: Matter) -> dict:
    pack = scaffold_pack(matter, CLIENT_DOCS)
    doc_list = "\n".join(f"- final/pack/{DOCS[d]}.html ({d})" for d in CLIENT_DOCS)
    notes = pack / "_mike-pack-notes.md"
    return {
        "mode": "subagent",
        "persona": "mike",
        "subagent": "mike",
        "kind": "pack",
        "model": model_for_leg("mike", "pack", matter),
        "artifact": str(notes.relative_to(matter.path)),
        "pack_dir": str(pack.relative_to(matter.path)),
        "prompt": mike_pack(matter, doc_list),
        "matter": str(matter.path),
        "surface": matter.config.get("surface", "claude"),
    }


def pack_next_json(matter: Matter) -> str:
    return json.dumps(pack_next(matter), indent=2)


def _ensure_puppeteer(cwd: Path) -> None:
    if (cwd / "node_modules" / "puppeteer").exists():
        return
    probe = subprocess.run(
        ["node", "-e", "require('puppeteer')"], cwd=cwd, capture_output=True, text=True
    )
    if probe.returncode != 0:
        subprocess.run(["npm", "i", "puppeteer", "--no-audit", "--no-fund"], cwd=cwd, check=True)


# FINAL GATE — process language that must never ship in a client deliverable.
BANNED_IN_FINALS = (
    "[VERIFY",
    "[verify",
    "page not pinned",
    "Prepared by the-firm",
    "this leg",
    "sources/",
)


def pack_gate_violations(pack: Path) -> dict[str, list[str]]:
    """Scan pack HTML for banned process language. Returns {file: [banned strings found]}."""
    hits: dict[str, list[str]] = {}
    for doc in DOCS.values():
        f = pack / f"{doc}.html"
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        found = [b for b in BANNED_IN_FINALS if b in text]
        if found:
            hits[f.name] = found
    return hits


def render_pack(pack: Path) -> list[str]:
    violations = pack_gate_violations(pack)
    if violations:
        detail = "; ".join(f"{f}: {', '.join(b)}" for f, b in violations.items())
        raise SystemExit(
            f"FINAL GATE: pack contains process language — resolve or excise before export ({detail})"
        )
    _ensure_puppeteer(pack)
    subprocess.run(["node", "render.js"], cwd=pack, check=True)
    return [str(p) for p in sorted(pack.glob("*.pdf"))]


def deliver_client_pack(matter: Matter) -> dict:
    if not matter.work_product.exists():
        raise SystemExit(f"no work product at {matter.work_product} — firm engine adopt first")
    pack = matter.final_dir / "pack"
    if not pack.is_dir():
        scaffold_pack(matter, CLIENT_DOCS)
    if not _pack_ready(pack):
        return {
            "pack_note": "Spawn mike for client pack: firm pack-next <matter>, then firm record-leg, then firm export again",
        }
    pdfs = render_pack(pack)
    return {"pack": str(pack), "pdfs": pdfs}
