"""Citation audit — record facts trace to sources/; law carries [VERIFY] unless confirmed."""

from __future__ import annotations

import re
from pathlib import Path

from .matter import Matter

# Indian statute / section patterns, generic case citations
LAW_CITE = re.compile(
    r"(?:Section|Sec\.|s\.|Art\.|Article)\s*\d+[A-Za-z0-9.-]*"
    r"|(?:\bv\.?\b|\bvs\.?\b)\s+[A-Z][A-Za-z0-9&.,'()\- ]{2,80}"
    r"|\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?\s+v\.?\s+[A-Z]",
    re.M,
)
VERIFY_TAG = "[VERIFY]"


def _source_tokens(matter: Matter) -> set[str]:
    tokens: set[str] = set()
    for p in matter.sources.rglob("*"):
        if p.is_file():
            tokens.add(p.name.lower())
            tokens.add(p.stem.lower())
            # chunk stems for nested-ingest names like nested-affidavit
            for part in re.split(r"[-_]", p.stem.lower()):
                if len(part) > 3:
                    tokens.add(part)
    return tokens


def _line_has_verify(line: str) -> bool:
    return VERIFY_TAG in line


def _line_cites_record(line: str, tokens: set[str]) -> bool:
    low = line.lower()
    if "sources/" in low:
        return True
    return any(t in low for t in tokens if len(t) > 4)


def audit_text(matter: Matter, text: str) -> tuple[str, list[str]]:
    """Return (possibly modified text, list of audit notes)."""
    tokens = _source_tokens(matter)
    notes: list[str] = []
    out_lines: list[str] = []

    for line in text.splitlines():
        if LAW_CITE.search(line) and not _line_has_verify(line):
            if not _line_cites_record(line, tokens):
                line = line.rstrip() + f" {VERIFY_TAG}"
                notes.append(f"tagged unverified cite: {line[:80]}…")
        out_lines.append(line)

    return "\n".join(out_lines) + ("\n" if text.endswith("\n") else ""), notes


def audit_work_product(matter: Matter) -> dict:
    path = matter.work_product
    if not path.is_file():
        return {"audited": False}
    text = path.read_text(encoding="utf-8")
    fixed, notes = audit_text(matter, text)
    if fixed != text:
        path.write_text(fixed, encoding="utf-8")
    return {"audited": True, "notes": notes, "path": str(path)}


def audit_draft_file(matter: Matter, draft: Path) -> dict:
    text = draft.read_text(encoding="utf-8")
    fixed, notes = audit_text(matter, text)
    if fixed != text:
        draft.write_text(fixed, encoding="utf-8")
    return {"notes": notes, "path": str(draft)}
