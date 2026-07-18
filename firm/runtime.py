"""Verdict/dispatch parsing and firm stdout helpers."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass

VERDICT_RE = re.compile(
    r"VERDICT:\s*(?:(CLEARED)|MATERIAL\s+OBJECTIONS\s*\(?\s*(\d+)\s*\)?)",
    re.I,
)
DISPATCH_RE = re.compile(
    r"DISPATCH:\s*(tyagi|mike|jessica|donna|harvey|closed)\s*\Z",
    re.I | re.M,
)
SIGNOFF_RE = re.compile(
    r"SIGNOFF:\s*(APPROVED(?:\s+WITH\s+RESIDUAL\s+RISK)?|REDRAFT)\s*\Z",
    re.I | re.M,
)
REVISED_BRIEF_RE = re.compile(r"^#\s*Revised Brief\s*\n", re.I | re.M)

_quiet = False


@dataclass
class Verdict:
    cleared: bool
    objections: int

    @property
    def label(self) -> str:
        return "CLEARED" if self.cleared else f"MATERIAL OBJECTIONS ({self.objections})"


def parse_verdict(text: str) -> Verdict:
    matches = VERDICT_RE.findall(text)
    if not matches:
        return Verdict(cleared=False, objections=-1)
    cleared, count = matches[-1]
    if cleared:
        return Verdict(cleared=True, objections=0)
    return Verdict(cleared=False, objections=int(count))


def parse_dispatch(text: str) -> str | None:
    matches = DISPATCH_RE.findall(text)
    if not matches:
        return None
    d = matches[-1].lower()
    return "jessica" if d == "donna" else d


def parse_signoff(text: str) -> str | None:
    matches = SIGNOFF_RE.findall(text)
    if not matches:
        return None
    raw = matches[-1].upper()
    if "RESIDUAL" in raw:
        return "APPROVED_WITH_RESIDUAL_RISK"
    return raw


def signoff_adopts(decision: str | None) -> bool:
    return decision in ("APPROVED", "APPROVED_WITH_RESIDUAL_RISK")


def extract_revised_brief(text: str) -> str:
    m = REVISED_BRIEF_RE.search(text)
    if m:
        return text[m.end() :].strip()
    if "# Brief" in text:
        return text.split("# Brief", 1)[1].split("DISPATCH:", 1)[0].strip()
    return text.strip()


def set_quiet(q: bool) -> None:
    global _quiet
    _quiet = q


def say(msg: str) -> None:
    if not _quiet:
        print(f"[firm] {msg}", flush=True)
        sys.stdout.flush()
