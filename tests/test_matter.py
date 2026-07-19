"""Matter scaffold and sources."""

from firm.matter import Matter, slugify, unique_slug
from firm.prompts import HARVEY_PIPE, mike_draft
from firm.scaffold import open_matter


def test_slugify(tmp_path):
    assert slugify("Reply under s.5 Limitation Act!") == "reply-under-s5-limitation-act"
    assert unique_slug("demo", tmp_path) == "demo"
    (tmp_path / "demo").mkdir()
    assert unique_slug("demo", tmp_path) == "demo-2"


def test_open_matter_and_ingest(tmp_path, monkeypatch):
    monkeypatch.setenv("FIRM_MATTERS", str(tmp_path))
    src = tmp_path / "order.pdf"
    src.write_bytes(b"%PDF")
    m = open_matter("Draft reply", [src], slug="case")
    assert (m.path / "sources" / "order.pdf").exists()
    assert m.sources_index.is_file()
    idx = m.sources_index.read_text(encoding="utf-8")
    assert "order.pdf" in idx
    assert "Read this file first" in idx
    assert m.harvey_context.exists()
    assert m.config["mode"] == "office"

    folder = tmp_path / "bundle"
    folder.mkdir()
    (folder / "a.pdf").write_bytes(b"%PDF")
    assert "a.pdf" in m.ingest_sources([folder])

    debate = m.path / "brief-debate"
    debate.mkdir(exist_ok=True)
    rd = m.next_round_dir()
    prompt = mike_draft(m, rd, None)
    assert "sources/index.md" in prompt
    assert "harvey-context.md" in prompt
    assert "in full" in prompt.lower() or "marked read" in prompt.lower()
    assert "every file in sources" not in prompt
