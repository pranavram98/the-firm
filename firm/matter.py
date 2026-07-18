"""Matter workspaces: scaffolding and round bookkeeping."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml

from .home import matters_root, templates_dir

TEMPLATES_DIR = templates_dir()


def slugify(text: str, max_len: int = 48) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return (s[:max_len].strip("-") if s else "") or "matter"


def unique_slug(base: str, root: Path | None = None) -> str:
    root = root or matters_root()
    slug = base
    n = 2
    while (root / slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Matter:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        self.config_path = self.path / "matter.yaml"

    # -- resolution ---------------------------------------------------------

    @classmethod
    def resolve(cls, slug_or_path: str) -> "Matter":
        p = Path(slug_or_path).expanduser()
        candidate = p if p.is_dir() else matters_root() / slug_or_path
        m = cls(candidate)
        if not m.config_path.exists():
            raise SystemExit(f"not a matter (no matter.yaml): {candidate}")
        return m

    @classmethod
    def create(
        cls,
        slug: str,
        objective: str,
        cause_title: str = "",
        root: Path | None = None,
        *,
        surface: str = "claude",
    ) -> "Matter":
        path = (root or matters_root()) / slug
        if path.exists():
            raise SystemExit(f"matter already exists: {path}")
        path.mkdir(parents=True)
        (path / "sources").mkdir()
        (path / "final").mkdir()
        m = cls(path)
        from .cast import default_matter_cast

        m.write_config(
            {
                "slug": slug,
                "objective": objective,
                "cause_title": cause_title,
                "surface": surface,
                "status": "open",
                "round_cap": 3,
                "brief_cap": 3,
                "prep_cap": 2,
                "personas": {
                    "drafter": "mike",
                    "strategist": "harvey",
                    "procedure_reviewer": "tyagi",
                    "merit_reviewer": "jessica",
                },
                "cast": default_matter_cast(surface),
                "mode": "live",
            }
        )
        brief_tpl = TEMPLATES_DIR / "brief.md"
        if brief_tpl.exists():
            (path / "brief.md").write_text(
                brief_tpl.read_text(encoding="utf-8").replace("{{objective}}", objective),
                encoding="utf-8",
            )
        ctx_tpl = TEMPLATES_DIR / "harvey-context.md"
        if ctx_tpl.exists():
            (path / "harvey-context.md").write_text(ctx_tpl.read_text(encoding="utf-8"), encoding="utf-8")
        return m

    # -- config -------------------------------------------------------------

    @property
    def config(self) -> dict:
        return yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}

    def write_config(self, cfg: dict) -> None:
        self.config_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")

    def update_config(self, **kv) -> None:
        cfg = self.config
        cfg.update(kv)
        self.write_config(cfg)

    # -- rounds -------------------------------------------------------------

    def round_dirs(self) -> list[Path]:
        return sorted(
            (d for d in self.path.glob("round-*") if d.is_dir()),
            key=lambda d: int(re.sub(r"\D", "", d.name) or 0),
        )

    def current_round(self) -> int:
        dirs = self.round_dirs()
        return int(re.sub(r"\D", "", dirs[-1].name)) if dirs else 0

    def next_round_dir(self) -> Path:
        d = self.path / f"round-{self.current_round() + 1}"
        d.mkdir()
        return d

    # -- paths --------------------------------------------------------------

    @property
    def brief(self) -> Path:
        return self.path / "brief.md"

    @property
    def harvey_context(self) -> Path:
        return self.path / "harvey-context.md"

    def latest_harvey_notes(self) -> Path | None:
        candidates = sorted(self.path.glob("**/leg-*-harvey-*.md"))
        notes = [p for p in candidates if "notes" in p.name or "rebuttal" in p.name or "dispatch" in p.name]
        return notes[-1] if notes else None

    @property
    def sources(self) -> Path:
        return self.path / "sources"

    @property
    def final_dir(self) -> Path:
        return self.path / "final"

    @property
    def work_product(self) -> Path:
        return self.final_dir / "work-product.md"

    @property
    def decision_log(self) -> Path:
        return self.final_dir / "decision-log.md"

    @property
    def sources_index(self) -> Path:
        return self.sources / "index.md"

    def source_listing(self) -> str:
        files = sorted(p.relative_to(self.sources).as_posix() for p in self.sources.rglob("*") if p.is_file())
        return "\n".join(f"- sources/{f}" for f in files) or "(no source files yet)"

    def ingest_sources(self, paths: list[Path]) -> list[str]:
        """Copy case files and folder contents into sources/. Returns basenames ingested."""
        ingested: list[str] = []
        for raw in paths:
            p = Path(raw).expanduser().resolve()
            if not p.exists():
                raise SystemExit(f"not found: {p}")
            if p.is_file():
                dest = self._unique_source_name(p.name)
                shutil.copy2(p, self.sources / dest)
                ingested.append(dest)
                continue
            for f in sorted(p.rglob("*")):
                if not f.is_file():
                    continue
                rel = f.relative_to(p).as_posix()
                name = rel.replace("/", "-") if "/" in rel else f.name
                dest = self._unique_source_name(name)
                shutil.copy2(f, self.sources / dest)
                ingested.append(dest)
        from .sources_index import build_sources_index

        build_sources_index(self)
        return ingested

    def _unique_source_name(self, name: str) -> str:
        dest = self.sources / name
        if not dest.exists():
            return name
        stem = Path(name).stem
        suffix = Path(name).suffix
        n = 2
        while True:
            candidate = f"{stem}-{n}{suffix}"
            if not (self.sources / candidate).exists():
                return candidate
            n += 1
