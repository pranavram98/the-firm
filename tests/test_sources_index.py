"""sources/index.md auto-build."""

from firm.matter import Matter
from firm.sources_index import build_sources_index


def test_build_sources_index(tmp_path, monkeypatch):
    monkeypatch.setenv("FIRM_MATTERS", str(tmp_path))
    m = Matter.create("idx", "Test index", root=tmp_path)
    (m.sources / "synopsis.md").write_text("Tribunal listed the matter on 12 Jan 2024.", encoding="utf-8")
    big = m.sources / "scan.pdf"
    big.write_bytes(b"%PDF-" + b"x" * (6 * 1024 * 1024))

    build_sources_index(m)
    text = m.sources_index.read_text(encoding="utf-8")
    assert "synopsis.md" in text
    assert "Tribunal listed" in text
    assert "scan.pdf" in text
    assert "large" in text.lower()
    assert "## Scope" in text

    m.sources_index.write_text(
        text.replace(
            "<!-- Harvey: after reading synopsis/order",
            "Skip scan part 2.\n\n<!-- Harvey: after reading synopsis/order",
        ),
        encoding="utf-8",
    )
    build_sources_index(m)
    rebuilt = m.sources_index.read_text(encoding="utf-8")
    assert "Skip scan part 2." in rebuilt
    assert "Tribunal listed" in rebuilt
