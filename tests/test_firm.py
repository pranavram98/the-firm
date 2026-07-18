"""Core firm tests — cast, routing, record, setup."""

from pathlib import Path

import pytest

from firm.cast import model_for_leg, subagent_model, surface_for_matter
from firm.citations import audit_text
from firm.export import export_draft
from firm.handoff import next_handoff
from firm.home import matters_root
from firm.matter import Matter
from firm.office import append_speech, office_path, seed_office
from firm.personas import load_personas, parse_persona
from firm.record import record_leg, run_engine
from firm.runtime import parse_dispatch, parse_verdict
from firm.setup import install_skill
from firm.state import Phase, compute_phase, next_step


def _matter(tmp_path, monkeypatch, slug="t"):
    monkeypatch.setenv("FIRM_MATTERS", str(tmp_path))
    return Matter.create(slug, "Test", root=tmp_path)


def test_cast_and_handoff(tmp_path, monkeypatch):
    monkeypatch.setenv("FIRM_MATTERS", str(tmp_path))
    assert model_for_leg("harvey", "proposal", surface="claude") == "claude-fable-5"
    assert model_for_leg("harvey", "proposal", surface="codex") == "gpt-5.6-sol"
    assert subagent_model("claude", "tyagi") == "opus"
    assert subagent_model("codex", "mike") == "terra"

    m = Matter.create("h", "obj", root=tmp_path, surface="claude")
    assert surface_for_matter(m) == "claude"
    hop = next_handoff(m)
    assert hop["legs"][0]["persona"] == "harvey"
    assert hop["legs"][0]["mode"] == "harvey"
    assert "prompt" in hop["legs"][0]


def test_state_machine_flow(tmp_path, monkeypatch):
    m = _matter(tmp_path, monkeypatch, "flow")
    assert compute_phase(m) == Phase.BRIEF_OPEN

    debate = m.path / "brief-debate"
    debate.mkdir(exist_ok=True)
    (debate / "leg-01-harvey-proposal.md").write_text("prop", encoding="utf-8")
    step = next_step(m)
    assert len(step.legs) == 1 and step.legs[0].persona == "tyagi"

    (debate / "leg-02-tyagi-challenge.md").write_text("ok\nVERDICT: CLEARED\n", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].persona == "harvey" and step.legs[0].kind == "synthesize"

    (debate / "leg-03-harvey-synthesize.md").write_text("# Office close\nCleared.\n", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].persona == "__engine__" and step.legs[0].kind == "lock-brief"

    m.brief.write_text("# brief\n", encoding="utf-8")
    run_engine(m, "lock-brief")
    assert compute_phase(m) == Phase.PRE_DRAFT

    prep = m.path / "draft-prep"
    prep.mkdir(exist_ok=True)
    (prep / "leg-01-harvey-conduct.md").write_text("# Office\nPrep open.\n", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].persona == "mike" and step.legs[0].kind == "prep"

    (prep / "leg-02-mike-prep.md").write_text("# Prep memo\noutline\n", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].kind == "synthesize"

    (prep / "leg-03-harvey-synthesize.md").write_text("# Office close\nPrep clear.\nDISPATCH: mike\n", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].kind == "lock-pre-draft"

    run_engine(m, "lock-pre-draft")
    assert compute_phase(m) == Phase.EXECUTION

    rd = m.next_round_dir()
    (rd / "leg-01-mike-draft.md").write_text("final draft", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].persona == "jessica" and step.legs[0].kind == "review"

    (rd / "leg-02-jessica-review.md").write_text("ok\nVERDICT: CLEARED\nDISPATCH: harvey\n", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].kind == "synthesize"

    (rd / "leg-03-harvey-synthesize.md").write_text("# Office close\nCleared.\nDISPATCH: closed\n", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].kind == "sign-off"

    (rd / "leg-04-harvey-signoff.md").write_text("SIGNOFF: APPROVED\n", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].persona == "__engine__" and step.legs[0].kind == "adopt"


def test_deliver_pipeline(tmp_path, monkeypatch):
    from unittest.mock import patch

    from firm.pack import PACK_TEMPLATES, SKELETONS, scaffold_pack

    m = _matter(tmp_path, monkeypatch, "deliver")
    m.update_config(brief_debate="closed", pre_draft="closed", status="closed")
    m.final_dir.mkdir(exist_ok=True)
    m.work_product.write_text("# Filing\n", encoding="utf-8")
    assert compute_phase(m) == Phase.PACK

    step = next_step(m)
    assert step.legs[0].persona == "mike" and step.legs[0].kind == "pack"

    pack = scaffold_pack(m, ["memo", "notes", "2pp", "reftable"])
    skeleton = (PACK_TEMPLATES / SKELETONS["memo"]).read_text(encoding="utf-8")
    (pack / "Briefing Memo.html").write_text(skeleton + "\n<p>" + ("x" * 300) + "</p>", encoding="utf-8")

    assert compute_phase(m) == Phase.DELIVER
    step = next_step(m)
    assert step.legs[0].kind == "export"

    with patch("firm.export.finish_deliverables", return_value={"docx": "x", "pdf": "y", "pdfs": ["a"]}):
        run_engine(m, "export")
    assert m.config.get("export_done")
    assert compute_phase(m) == Phase.COMPLETE
    hop = next_handoff(m)
    assert hop["pause"] and hop["reason"] == "complete"


def test_jessica_dispatches_tyagi_recall(tmp_path, monkeypatch):
    m = _matter(tmp_path, monkeypatch, "tyagirecall")
    m.update_config(brief_debate="closed", pre_draft="closed")
    rd = m.next_round_dir()
    (rd / "leg-01-mike-draft.md").write_text("draft", encoding="utf-8")
    (rd / "leg-02-jessica-review.md").write_text(
        "limitation\nVERDICT: MATERIAL OBJECTIONS (1)\nDISPATCH: tyagi\n", encoding="utf-8"
    )
    step = next_step(m)
    assert step.legs[0].persona == "tyagi" and step.legs[0].kind == "viability"

    (rd / "leg-03-tyagi-viability.md").write_text("ok\nVERDICT: CLEARED\nDISPATCH: harvey\n", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].persona == "harvey" and step.legs[0].kind == "synthesize"
    assert step.legs[0].reason == "tyagi-recall-close"


def test_mike_recall_from_dispatch(tmp_path, monkeypatch):
    m = _matter(tmp_path, monkeypatch, "mikerecall")
    m.update_config(brief_debate="closed", pre_draft="closed")
    rd = m.next_round_dir()
    (rd / "leg-01-mike-draft.md").write_text("draft", encoding="utf-8")
    (rd / "leg-02-jessica-review.md").write_text(
        "obj\nVERDICT: MATERIAL OBJECTIONS (1)\nDISPATCH: mike\n", encoding="utf-8"
    )
    step = next_step(m)
    assert step.legs[0].persona == "mike" and step.legs[0].kind == "draft"


def test_jessica_correction_loop(tmp_path, monkeypatch):
    m = _matter(tmp_path, monkeypatch, "ocloop")
    m.update_config(brief_debate="closed", pre_draft="closed")
    rd = m.next_round_dir()
    (rd / "leg-01-mike-draft.md").write_text("draft v1", encoding="utf-8")
    (rd / "leg-02-jessica-review.md").write_text(
        "obj\nVERDICT: MATERIAL OBJECTIONS (2)\nDISPATCH: harvey\n", encoding="utf-8"
    )
    step = next_step(m)
    assert step.legs[0].kind == "synthesize"

    (rd / "leg-03-harvey-synthesize.md").write_text(
        "# Office close\nFix prayer.\nDISPATCH: mike\n", encoding="utf-8"
    )
    step = next_step(m)
    assert step.legs[0].persona == "mike" and step.legs[0].kind == "draft"

    (rd / "leg-04-mike-draft.md").write_text("draft v2\nDISPATCH: jessica\n", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].persona == "jessica" and step.legs[0].kind == "review"


def test_round_cap_forces_signoff(tmp_path, monkeypatch):
    from firm.caps import review_cap_reached

    m = _matter(tmp_path, monkeypatch, "cap")
    m.update_config(brief_debate="closed", pre_draft="closed", round_cap=2)
    rd = m.next_round_dir()
    (rd / "leg-01-mike-draft.md").write_text("v1", encoding="utf-8")
    (rd / "leg-02-jessica-review.md").write_text(
        "obj\nVERDICT: MATERIAL OBJECTIONS (1)\nDISPATCH: harvey\n", encoding="utf-8"
    )
    (rd / "leg-03-harvey-synthesize.md").write_text(
        "# Office close\nFix.\nDISPATCH: mike\n", encoding="utf-8"
    )
    (rd / "leg-04-mike-draft.md").write_text("v2\nDISPATCH: jessica\n", encoding="utf-8")
    assert review_cap_reached(m)

    step = next_step(m)
    assert step.legs[0].persona == "harvey" and step.legs[0].kind == "sign-off"
    assert step.legs[0].reason == "round-cap"

    hop = next_handoff(m)
    assert "ROUND CAP" in hop["legs"][0]["prompt"]
    assert "REDRAFT is not available" in hop["legs"][0]["prompt"]


def test_residual_risk_signoff_adopts(tmp_path, monkeypatch):
    m = _matter(tmp_path, monkeypatch, "residual")
    m.update_config(brief_debate="closed", pre_draft="closed")
    rd = m.next_round_dir()
    (rd / "leg-01-mike-draft.md").write_text("final", encoding="utf-8")
    (rd / "leg-02-jessica-review.md").write_text("ok\nVERDICT: CLEARED\nDISPATCH: harvey\n", encoding="utf-8")
    (rd / "leg-03-harvey-synthesize.md").write_text("# Office close\nCleared.\nDISPATCH: closed\n", encoding="utf-8")
    (rd / "leg-04-harvey-signoff.md").write_text(
        "# Residual risk\n1. Prayer wording.\nSIGNOFF: APPROVED WITH RESIDUAL RISK\n", encoding="utf-8"
    )
    step = next_step(m)
    assert step.legs[0].kind == "adopt"
    run_engine(m, "adopt")
    assert m.config["status"] == "closed"
    assert m.decision_log.is_file()


def test_brief_cap_forces_lock(tmp_path, monkeypatch):
    m = _matter(tmp_path, monkeypatch, "bcap")
    assert m.config["brief_cap"] == 3
    debate = m.path / "brief-debate"
    debate.mkdir(exist_ok=True)
    (debate / "leg-01-harvey-proposal.md").write_text("prop", encoding="utf-8")
    (debate / "leg-02-tyagi-challenge.md").write_text(
        "obj\nVERDICT: MATERIAL OBJECTIONS (1)\nDISPATCH: harvey\n", encoding="utf-8"
    )
    (debate / "leg-03-harvey-synthesize.md").write_text("# close\nfix\n", encoding="utf-8")
    (debate / "leg-04-tyagi-challenge.md").write_text(
        "still\nVERDICT: MATERIAL OBJECTIONS (1)\nDISPATCH: harvey\n", encoding="utf-8"
    )
    (debate / "leg-05-harvey-synthesize.md").write_text("# close\nfix2\n", encoding="utf-8")
    (debate / "leg-06-tyagi-challenge.md").write_text(
        "again\nVERDICT: MATERIAL OBJECTIONS (1)\nDISPATCH: harvey\n", encoding="utf-8"
    )
    m.brief.write_text("# brief\n", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].persona == "harvey" and step.legs[0].reason == "brief-cap"

    (debate / "leg-07-harvey-synthesize.md").write_text(
        "# Residual procedure risk\n1. Limitation.\nDISPATCH: closed\n", encoding="utf-8"
    )
    step = next_step(m)
    assert step.legs[0].kind == "lock-brief" and step.legs[0].reason == "brief-cap"


def test_prep_cap_forces_lock(tmp_path, monkeypatch):
    m = _matter(tmp_path, monkeypatch, "pcap")
    m.update_config(brief_debate="closed", prep_cap=2)
    prep = m.path / "draft-prep"
    prep.mkdir(exist_ok=True)
    (prep / "leg-01-harvey-conduct.md").write_text("# Office\nPrep.\n", encoding="utf-8")
    (prep / "leg-02-mike-prep.md").write_text("# Prep\nv1\n", encoding="utf-8")
    (prep / "leg-03-harvey-synthesize.md").write_text("# close\nmore prep\n", encoding="utf-8")
    (prep / "leg-04-mike-prep.md").write_text("# Prep\nv2\n", encoding="utf-8")
    step = next_step(m)
    assert step.legs[0].persona == "harvey" and step.legs[0].reason == "prep-cap"

    (prep / "leg-05-harvey-synthesize.md").write_text(
        "# Residual prep risk\n1. Record gap.\nDISPATCH: mike\n", encoding="utf-8"
    )
    step = next_step(m)
    assert step.legs[0].kind == "lock-pre-draft" and step.legs[0].reason == "prep-cap"


def test_runtime_parsing():
    assert parse_verdict("VERDICT: CLEARED\n").cleared
    assert parse_verdict("VERDICT: MATERIAL OBJECTIONS (2)\n").objections == 2
    assert parse_dispatch("DISPATCH: donna\n") == "jessica"
    assert parse_dispatch("no dispatch") is None
    from firm.runtime import parse_signoff, signoff_adopts

    assert parse_signoff("SIGNOFF: APPROVED\n") == "APPROVED"
    assert parse_signoff("SIGNOFF: APPROVED WITH RESIDUAL RISK\n") == "APPROVED_WITH_RESIDUAL_RISK"
    assert signoff_adopts("APPROVED_WITH_RESIDUAL_RISK")


def test_record_leg_and_engine(tmp_path, monkeypatch):
    m = _matter(tmp_path, monkeypatch, "rec")
    debate = m.path / "brief-debate"
    debate.mkdir(exist_ok=True)
    art = debate / "leg-02-tyagi-challenge.md"
    art.write_text("obj\nVERDICT: MATERIAL OBJECTIONS (1)\nDISPATCH: harvey\n", encoding="utf-8")
    out = record_leg(m, art)
    assert out["verdict"] == "MATERIAL OBJECTIONS (1)"
    assert "Tyagi" in office_path(m).read_text(encoding="utf-8")

    m.brief.write_text("# brief\n", encoding="utf-8")
    assert run_engine(m, "lock-brief")["kind"] == "lock-brief"
    assert m.config["brief_debate"] == "closed"


def test_room_assignments_parse():
    from firm.room import parse_room_assignments

    text = (
        "# Room assignments\n"
        "- tyagi | brief-debate | Forum under Order VII\n"
        "- mike | prep | Chronology from order.pdf\n"
    )
    got = parse_room_assignments(text)
    assert len(got) == 2
    assert got[1].persona == "mike" and got[1].kind == "prep"


def test_debate_tyagi_only(tmp_path, monkeypatch):
    m = _matter(tmp_path, monkeypatch, "room")
    debate = m.path / "brief-debate"
    debate.mkdir(exist_ok=True)
    (debate / "leg-01-harvey-proposal.md").write_text("prop", encoding="utf-8")

    hop = next_handoff(m)
    assert hop["batch"]["parallel"] is False
    assert len(hop["legs"]) == 1
    assert hop["legs"][0]["persona"] == "tyagi"


def test_debate_ignores_premature_jessica_review(tmp_path, monkeypatch):
    m = _matter(tmp_path, monkeypatch, "early-j")
    debate = m.path / "brief-debate"
    debate.mkdir(exist_ok=True)
    (debate / "leg-01-harvey-proposal.md").write_text(
        "# Office\nopen\n# Room assignments\n"
        "- tyagi | brief-debate | Limitation\n"
        "- jessica | review | Merit read on draft\n",
        encoding="utf-8",
    )
    hop = next_handoff(m)
    personas = {leg["persona"] for leg in hop["legs"]}
    assert "jessica" not in personas
    assert "tyagi" in personas


def test_cli_record_leg_argv(tmp_path, monkeypatch, capsys):
    from firm.cli import main

    m = _matter(tmp_path, monkeypatch, "cli-rec")
    debate = m.path / "brief-debate"
    debate.mkdir(exist_ok=True)
    art = debate / "leg-02-tyagi-challenge.md"
    art.write_text("VERDICT: CLEARED\nDISPATCH: harvey\n", encoding="utf-8")
    main(["record-leg", str(m.path), str(art.relative_to(m.path))])
    out = capsys.readouterr().out
    assert '"persona": "tyagi"' in out


def test_cli_engine_argv(tmp_path, monkeypatch, capsys):
    from firm.cli import main

    m = _matter(tmp_path, monkeypatch, "cli-eng")
    m.brief.write_text("# brief\n", encoding="utf-8")
    debate = m.path / "brief-debate"
    debate.mkdir(exist_ok=True)
    (debate / "leg-01-harvey-proposal.md").write_text("p", encoding="utf-8")
    (debate / "leg-02-tyagi-challenge.md").write_text(
        "VERDICT: CLEARED\nDISPATCH: harvey\n", encoding="utf-8"
    )
    (debate / "leg-03-harvey-synthesize.md").write_text("ok\n", encoding="utf-8")
    main(["engine", str(m.path), "lock-brief"])
    assert capsys.readouterr().out.strip().startswith("{")
    assert m.config["brief_debate"] == "closed"


def test_office_room(tmp_path, monkeypatch):
    m = _matter(tmp_path, monkeypatch, "room")
    seed_office(m)
    append_speech(m, "harvey", "Opening.", action="opens", dispatch="tyagi")
    assert "Harvey" in office_path(m).read_text(encoding="utf-8")


def test_personas():
    personas = load_personas()
    assert {"harvey", "tyagi", "mike", "jessica"} <= set(personas)
    bad = Path(__file__).parent / "_bad_persona.md"
    bad.write_text("---\nname: x\nrole: reviewer\nverdict: false\n---\np\n", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="verdict"):
            parse_persona(bad)
    finally:
        bad.unlink(missing_ok=True)


def test_export_and_citations(tmp_path, monkeypatch):
    m = _matter(tmp_path, monkeypatch, "exp")
    m.final_dir.mkdir(exist_ok=True)
    m.work_product.write_text("# Draft\n", encoding="utf-8")

    from unittest.mock import patch

    with patch("firm.export._pandoc", return_value=True), patch("firm.export._html_to_pdf"):
        assert "docx" in export_draft(m)

    text, notes = audit_text(m, "Under Section 5 of the Limitation Act.\n")
    assert "[VERIFY]" in text and notes


def test_matters_root_outside_repo(tmp_path, monkeypatch):
    monkeypatch.delenv("FIRM_MATTERS", raising=False)
    monkeypatch.setattr("firm.home.config_path", lambda: tmp_path / "none.yaml")
    assert matters_root().name == "firm-matters"


def _fake_repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    (repo / "personas").mkdir(parents=True)
    (repo / "templates").mkdir()
    for name, role, verdict in (
        ("harvey", "strategist", "false"),
        ("tyagi", "reviewer", "true"),
        ("mike", "drafter", "false"),
        ("jessica", "reviewer", "true"),
    ):
        (repo / "personas" / f"{name}.md").write_text(
            f"---\nname: {name}\nrole: {role}\ntools: read-only\n"
            f"fresh_context: true\nverdict: {verdict}\n---\n{name}\n",
            encoding="utf-8",
        )
    skill = repo / ".claude" / "skills" / "the-firm"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("x", encoding="utf-8")
    (repo / ".agents" / "skills" / "the-firm").mkdir(parents=True)
    (repo / ".agents" / "skills" / "the-firm" / "SKILL.md").write_text("x", encoding="utf-8")
    monkeypatch.setenv("FIRM_HOME", str(repo))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return repo


@pytest.mark.parametrize("surface,skill_dir,agents_dir", [
    ("claude", ".claude/skills/the-firm", ".claude/agents"),
    ("codex", ".agents/skills/the-firm", ".agents/agents"),
])
def test_install_skill(tmp_path, monkeypatch, surface, skill_dir, agents_dir):
    _fake_repo(tmp_path, monkeypatch)
    install_skill(surface)
    home = tmp_path / "home"
    assert (home / skill_dir).is_symlink()
    assert (home / agents_dir / "tyagi.md").is_file()
