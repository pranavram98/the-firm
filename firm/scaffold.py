"""Open a matter and ingest sources."""

from __future__ import annotations

from pathlib import Path

from .home import matters_root
from .matter import Matter, slugify, unique_slug


def open_matter(
    objective: str,
    paths: list[Path],
    *,
    cause_title: str = "",
    slug: str | None = None,
    surface: str = "claude",
) -> Matter:
    root = matters_root()
    matter_slug = slug or unique_slug(slugify(objective), root)
    m = Matter.create(matter_slug, objective, cause_title, root=root, surface=surface)
    ingested = m.ingest_sources(paths)
    if not ingested:
        raise SystemExit("no documents found in sources")
    (m.path / "brief-debate").mkdir(exist_ok=True)
    m.update_config(mode="office")
    from .office import seed_office

    seed_office(m)
    return m
