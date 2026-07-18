"""Court-specific deliverable templates."""

from __future__ import annotations

import re
from pathlib import Path

from .home import templates_dir
from .matter import Matter

COURTS = templates_dir() / "courts"

# Order matters — first match wins
JURISDICTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"gujarat\s+high\s+court|gujarat\s+hc|guj\s*hc", re.I), "india-gujarat-hc"),
    (re.compile(r"delhi\s+high\s+court|delhi\s+hc", re.I), "india-delhi-hc"),
    (re.compile(r"india|bharat", re.I), "india-default"),
    (re.compile(r"england|wales|uk", re.I), "uk-default"),
]


def infer_court_id(matter: Matter) -> str:
    cfg = matter.config.get("court")
    if cfg:
        return str(cfg)
    blob = " ".join(
        filter(
            None,
            [
                matter.config.get("objective", ""),
                matter.config.get("cause_title", ""),
                matter.brief.read_text(encoding="utf-8")[:4000] if matter.brief.is_file() else "",
            ],
        )
    )
    for pat, court_id in JURISDICTION_PATTERNS:
        if pat.search(blob):
            return court_id
    return "default"


def court_dir(matter: Matter) -> Path:
    cid = infer_court_id(matter)
    p = COURTS / cid
    return p if p.is_dir() else COURTS / "default"


def draft_css(matter: Matter) -> str:
    css = court_dir(matter) / "draft.css"
    if css.is_file():
        return css.read_text(encoding="utf-8")
    return (
        "body{max-width:800px;margin:2em auto;font-family:Georgia,serif;"
        "line-height:1.55;font-size:11pt}"
    )


def draft_header_md(matter: Matter) -> str:
    tpl = court_dir(matter) / "header.md"
    if not tpl.is_file():
        cause = matter.config.get("cause_title") or matter.config.get("slug", "")
        return f"**{cause}**\n\n" if cause else ""
    text = tpl.read_text(encoding="utf-8")
    return (
        text.replace("{{cause_title}}", matter.config.get("cause_title", ""))
        .replace("{{objective}}", matter.config.get("objective", ""))
        .replace("{{slug}}", matter.config.get("slug", ""))
    )


def pandoc_reference_doc(matter: Matter) -> Path | None:
    ref = court_dir(matter) / "reference.docx"
    return ref if ref.is_file() else None
