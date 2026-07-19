"""Auto-build sources/index.md — read index first; originals only on doubt."""

from __future__ import annotations

import re
from pathlib import Path

from .matter import Matter
from .tokens import index_preview_chars

LARGE_BYTES = 5 * 1024 * 1024
TEXT_PREVIEW = 600
TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".html", ".htm"}

SCOPE_RE = re.compile(r"(?ms)^## Scope\s*\n(.*?)(?=^## |\Z)")


def _human_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f}MB"
    if n >= 1024:
        return f"{n / 1024:.0f}KB"
    return f"{n}B"


def _preview(path: Path, *, max_chars: int = TEXT_PREVIEW) -> str:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return ""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    one = " ".join(raw.split())
    if len(one) <= max_chars:
        return one
    return one[:max_chars].rstrip() + "…"


def _auto_note(path: Path, size: int, *, preview_chars: int = TEXT_PREVIEW) -> str:
    if path.suffix.lower() in TEXT_SUFFIXES:
        prev = _preview(path, max_chars=preview_chars)
        if prev:
            return prev
    if size >= LARGE_BYTES:
        return "large — use index + Grep; open original only if fact disputed"
    if path.suffix.lower() == ".pdf":
        return "pdf — open only if index/harvey-context lacks the fact"
    return "open only if index or harvey-context lacks the fact"


def _scope_block(existing: str) -> str:
    m = SCOPE_RE.search(existing)
    if m and m.group(1).strip():
        return m.group(1).rstrip() + "\n"
    return (
        "<!-- Harvey: after reading synopsis/order, list which files matter, "
        "what to skip, chronology pointers -->\n"
    )


def build_sources_index(matter: Matter) -> Path:
    index_path = matter.sources / "index.md"
    existing = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    scope = _scope_block(existing)

    rows: list[str] = []
    large: list[str] = []
    for path in sorted(matter.sources.rglob("*")):
        if not path.is_file() or path.name == "index.md":
            continue
        rel = path.relative_to(matter.sources).as_posix()
        size = path.stat().st_size
        note = _auto_note(path, size, preview_chars=index_preview_chars(matter))
        rows.append(f"| `{rel}` | {_human_size(size)} | {note} |")
        if size >= LARGE_BYTES:
            large.append(rel)

    files_table = "\n".join(rows) if rows else "| *(empty)* | — | — |"
    large_note = ""
    if large:
        large_note = (
            "\n\n**Large files (>5MB):** "
            + ", ".join(f"`{n}`" for n in large)
            + " — do not bulk-read; Grep or targeted Read only.\n"
        )

    body = (
        "# Record index\n\n"
        "**Read this file first on every leg** — then `brief.md` and `harvey-context.md`. "
        "Previews in the Files table are **routing hints only**; they do not substitute for "
        "reading substantive filings when your leg requires it (see leg prompt read depth).\n\n"
        "**By leg:** brief-debate + prep + draft → read scoped/substantive files **in full** "
        "(split large scans). Review legs → draft + index first; open originals when a pin, "
        "quote, or procedure turn needs the source.\n\n"
        "## Scope\n\n"
        f"{scope}\n"
        "## Files\n\n"
        "| File | Size | Notes |\n"
        "|------|------|-------|\n"
        f"{files_table}\n"
        f"{large_note}"
    )
    index_path.write_text(body, encoding="utf-8")
    return index_path


_INDEX_FIRST = (
    "Read `sources/index.md`, then `brief.md` and `harvey-context.md`. "
    "Index previews are routing only — not a substitute for reading substantive filings "
    "when your leg requires it."
)

READ_MODES: dict[str, str] = {
    "default": (
        _INDEX_FIRST + " Open `sources/` when a fact is disputed or the index lacks detail — "
        "Grep before Read on large PDFs."
    ),
    "debate": (
        _INDEX_FIRST + " **Brief debate / procedure map:** read **in full** — impugned order, "
        "synopsis/cause papers, limitation/service/verification filings, and every file Harvey "
        "lists in index ## Scope. Waiver and record pins require the actual filing, not the "
        "preview. Grep/split large PDFs; read page-ranges visually."
    ),
    "prep": (
        _INDEX_FIRST + " **Prep / record sweep:** read **every substantive filing of every party** "
        "(incl. parallel proceedings) — mark read/unread per index row. Index-only prep is a "
        "FATAL failure. Split scanned PDFs into page-ranges; Read visually."
    ),
    "draft": (
        _INDEX_FIRST + " **Draft leg:** every item marked READ in prep must be open; every pin "
        "traces to a full read of that source. Open `sources/` for any fact you cite."
    ),
    "review": (
        _INDEX_FIRST + " **Review leg:** draft + index first; open `sources/` when a pin is "
        "missing, a quote looks wrong, or procedure turns on record text the index cannot show."
    ),
    "office": (
        _INDEX_FIRST + " **Office take:** read debate legs + index; open scoped `sources/` "
        "before making a substantive record claim."
    ),
    "task": (
        _INDEX_FIRST + " **Assigned task:** read every source the task requires **in full** — "
        "do not answer from index previews alone."
    ),
}


def source_read_instruction(*, include_legs: str = "", mode: str = "default") -> str:
    base = READ_MODES.get(mode, READ_MODES["default"])
    if include_legs:
        return f"{base}\n{include_legs}"
    return base
