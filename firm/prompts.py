"""Task prompts for delegated legs — Harvey writes strategy live; these run Mike/Tyagi/Jessica."""

from __future__ import annotations

from pathlib import Path

from .matter import Matter
from .sources_index import source_read_instruction

LOOP_POWERS = (
    "**Push back / close loop (you have the power — engine follows your last line):**\n"
    "- **Push back:** VERDICT: MATERIAL OBJECTIONS (n) + DISPATCH: who fixes it "
    "(tyagi|mike|jessica|harvey).\n"
    "- **Close your loop:** VERDICT: CLEARED + DISPATCH: harvey (or closed if your gate is done).\n"
    "- **Corrections:** one numbered list, one owner — do not leave routing vague.\n\n"
)

CLIENT_WORK = (
    "**Client work product** — what leaves the firm is real: court, client, opposing counsel.\n"
    "Swift, straight, file-ready. Quality is mandatory; **spin is forbidden**.\n\n"
    "**Iteration discipline (firm-wide):**\n"
    "- One correction pass on a point is normal; **three on the same niggle is failure**.\n"
    "- Do not re-litigate a Harvey ruling or a CLEARED gate unless the record changed.\n"
    "- Material objections only — no perfectionism theater.\n"
    "- If two fixes will not close it, DISPATCH: harvey — escalate, do not loop.\n"
    "- Engine caps (defaults): `brief_cap` 3 Tyagi passes · `prep_cap` 2 Mike prep · "
    "`round_cap` 3 Mike drafts — then forced close with residual risk logged.\n\n"
)

PROCEDURE_FIRST = (
    "**Universal rule — procedure before merits:** Every leg, every forum, every colleague. "
    "Limitation, forum, verification, service, record, and registry practice come first. "
    "If procedure can knock the case off or win on a point, that leads until Tyagi clears "
    "or Harvey rules otherwise. Do not bury procedure under merits rhetoric. Mike does not "
    "draft merits-heavy work while open procedure items remain uncleared. Jessica routes "
    "live procedure to Tyagi before merit spiral.\n\n"
)

FIRM_ROLES = (
    CLIENT_WORK
    + PROCEDURE_FIRST
    + "**The firm** — common-law matters worldwide; law from `brief.md` (not the TV shows):\n"
    "- **Harvey** (*Suits* — Harvey Specter) — partner; strategy, synthesis, sign-off.\n"
    "- **Tyagi** (*Maamla Legal Hai* — V.D. Tyagi; **Tyagi only**) — procedure hunter: lapses "
    "in the client's favour; often enough to knock a case off or win on a point.\n"
    "- **Mike** (*Suits* — Mike Ross) — prep + final work product.\n"
    "- **Jessica** (*Suits* — Jessica Pearson) — opposing-counsel / bench read.\n"
    "Shows = personality. Push back and close loops via VERDICT + DISPATCH.\n\n"
)

DISPATCH_INSTRUCTION = (
    "Mandatory final line — the engine routes from this:\n"
    "DISPATCH: tyagi|mike|jessica|harvey|closed"
)

VERDICT_INSTRUCTION = (
    "End with VERDICT (mandatory for reviewers):\n"
    "VERDICT: CLEARED\n"
    "or\n"
    "VERDICT: MATERIAL OBJECTIONS (n)\n\n"
    + LOOP_POWERS
    + DISPATCH_INSTRUCTION
)

REVIEWER_TAIL = LOOP_POWERS + VERDICT_INSTRUCTION

NO_FABRICATION = (
    "CITATION: brief.md + harvey-context.md jurisdiction. Record facts → sources/ or [VERIFY]. "
    "Law → fetch or [VERIFY]. Pin impugned-order internal pages; full cite at first use. "
    "No invented cases/sections.\n"
)

RECORD_SWEEP = (
    "**RECORD SWEEP (prep — mandatory):** inventory every party's filings (incl. parallel "
    "proceedings); **Read each substantive filing in full** — index preview ≠ read; "
    "read/unread mark per row; no draft while opponent/co-respondent submissions unread; "
    "waiver hunt; fetch list resolved before draft leg.\n\n"
)

GOLD_STANDARD = (
    "**GOLD STANDARD:** dispositive answers first; numbered propositions with bold leads; "
    "answer every opposing ground; one citation key; pack template headers are law.\n\n"
)

FINAL_GATE = (
    "**FINAL GATE:** no [VERIFY]/process language in deliverables — fetch or excise; footers = "
    "counsel + citation key.\n\n"
)

WAIVER_HUNT = (
    "**Waiver:** each procedural objection — taken below? Silence + pin is the first answer.\n\n"
)

HARVEY_PIPE = (
    "Read `sources/index.md`, then `harvey-context.md` (Mike must/must-not, dispatch, flags).\n\n"
)


def _listing(folder: Path, matter: Path) -> str:
    legs = sorted(folder.glob("leg-*.md"))
    if not legs:
        return "(no legs yet)"
    return "\n".join(f"- {p.relative_to(matter)}" for p in legs)


def _harvey_packet(matter: Matter) -> str:
    notes = matter.latest_harvey_notes()
    extra = ""
    if notes:
        extra = f"Also read `{notes.relative_to(matter.path)}` (latest Harvey notes).\n"
    return HARVEY_PIPE + extra


def _office(matter: Matter, *, inline: bool = True) -> str:
    from .office import office_prompt_block

    return office_prompt_block(matter, inline=inline)


def _leg_open(matter: Matter, *, inline_office: bool = False) -> str:
    return _office(matter, inline=inline_office) + _harvey_packet(matter)


OFFICE_ROOM = "Read `office.md` — colleagues may be parallel; respond by name.\n\n"

ROOM_ASSIGNMENTS_BLOCK = (
    "# Room assignments\n"
    "Assign **one colleague, one task** per movement.\n"
    "Phase rules — do not assign review or draft until Mike has written the round draft:\n"
    "- **Brief debate:** tyagi | brief-debate · jessica | office-take · mike | task\n"
    "- **Pre-draft:** mike | prep · tyagi | task · jessica | office-take\n"
    "- **Review (post-draft):** jessica | review · tyagi | viability · mike | task\n"
    "Format: `- persona | kind | <specific task>`\n\n"
)


def _harvey_task(task: str) -> str:
    if not task.strip():
        return ""
    return f"**Harvey assigned you:** {task.strip()}\n\n"


def harvey_proposal(matter: Matter) -> str:
    cfg = matter.config
    return (
        f"{_office(matter, inline=True)}"
        f"You are **opening the office** — conductor, not clerk. OBJECTIVE: {cfg.get('objective')}\n"
        f"CAUSE TITLE: {cfg.get('cause_title') or '(set jurisdiction & forum in brief)'}\n\n"
        f"Sources:\n{matter.source_listing()}\n\n"
        "Open the room, set strategy, write the brief — **procedure before merits**. "
        "**Send Tyagi to map procedure** — lapses in the client's favour and exposure we must cure "
        "before Mike researches or drafts merits. "
        "After reading synopsis/order, fill **Scope** in `sources/index.md` (what matters, what to skip). "
        "Update harvey-context.md.\n\n"
        "Structure:\n"
        "# Office\n"
        "<open the room — partner voice>\n\n"
        f"{ROOM_ASSIGNMENTS_BLOCK}"
        "# Brief\n"
        "<full brief markdown for brief.md>\n\n"
        "End with: DISPATCH: tyagi\n\n" + NO_FABRICATION
    )


def harvey_conduct(matter: Matter, folder: Path, *, phase: str) -> str:
    if phase == "debate":
        reopen = "**Re-open brief debate** — Tyagi has not cleared; send Tyagi back in.\n\n"
    elif phase == "pre_draft":
        reopen = (
            "**Pre-draft with Mike** — brief is locked. Align on outline, record gaps, and "
            "drafting plan before Mike writes final outputs.\n\n"
        )
    else:
        reopen = (
            "**Review movement** — Jessica has not cleared. One focused re-read or one Mike "
            "correction list. **Do not** reopen settled points. Three passes on the same clause "
            "→ ship with residual risk.\n\n"
        )
    return (
        f"{_office(matter, inline=True)}"
        f"{CLIENT_WORK}"
        f"{reopen}"
        f"Prior legs:\n{_listing(folder, matter.path)}\n\n"
        "Structure:\n"
        "# Office\n"
        "<open the movement — address the colleague by name>\n\n"
        f"{ROOM_ASSIGNMENTS_BLOCK}"
        "Update harvey-context.md Current dispatch.\n\n" + NO_FABRICATION
    )


def harvey_synthesize(matter: Matter, folder: Path, *, phase: str, reason: str = "") -> str:
    from .caps import (
        brief_cap,
        brief_cap_blurb,
        brief_cap_reached,
        mike_draft_count,
        mike_prep_count,
        prep_cap,
        prep_cap_reached,
        review_cap_reached,
        round_cap,
        tyagi_challenge_count,
    )

    cap_note = ""
    if reason == "brief-cap" or (phase == "debate" and brief_cap_reached(matter)):
        cap_note = (
            f"\n**BRIEF CAP ({tyagi_challenge_count(matter)}/{brief_cap(matter)} Tyagi passes).** "
            f"{brief_cap_blurb(matter)}\n"
            "Lock brief next — log open procedure in # Residual procedure risk. "
            "DISPATCH: closed (mandatory).\n"
        )
    elif reason == "prep-cap" or (phase == "pre_draft" and prep_cap_reached(matter)):
        cap_note = (
            f"\n**PREP CAP ({mike_prep_count(matter)}/{prep_cap(matter)} Mike prep legs).** "
            "Lock prep next — log gaps in # Residual prep risk. DISPATCH: mike (mandatory).\n"
        )
    elif phase == "review" and review_cap_reached(matter):
        cap_note = (
            f"\n**ROUND CAP ({mike_draft_count(matter)}/{round_cap(matter)} Mike drafts).** "
            "No further Mike redrafts. DISPATCH: closed — partner sign-off with residual risk next.\n"
        )
    return (
        f"{_office(matter, inline=True)}"
        f"{CLIENT_WORK}"
        "**Close the movement.** Your colleague returned — you rule and dispatch.\n\n"
        f"Read office.md, all legs since this movement opened:\n{_listing(folder, matter.path)}\n\n"
        "1. # Office close — synthesize; ACCEPT/REJECT each objection; update harvey-context.md "
        "(Mike must / must not).\n"
        "2. # Objection Rulings / # Revised Brief — if brief debate.\n\n"
        "**Cut loops:** REJECT duplicate niggles; consolidate fixes; if the same point is back "
        "for a third time, DISPATCH: closed (sign-off with residual risk) — do not dispatch Mike again.\n\n"
        "**Partner dispatch (mandatory last line):** send the baton — corrections or next gate.\n"
        "- Prep clear → DISPATCH: mike\n"
        "- Need Tyagi on procedure → DISPATCH: tyagi\n"
        "- Need Jessica re-read → DISPATCH: jessica\n"
        "- Mike must revise → DISPATCH: mike (unless round cap spent)\n"
        "- Jessica cleared, ready to sign → DISPATCH: closed\n"
        f"{cap_note}\n"
        f"{DISPATCH_INSTRUCTION}\n\n"
        + NO_FABRICATION
    )


def delegated_task(matter: Matter, persona: str, task: str, folder: Path) -> str:
    read = source_read_instruction(
        mode="task", include_legs=f"Legs:\n{_listing(folder, matter.path)}"
    )
    dispatch = (DISPATCH_INSTRUCTION + "\n\n") if persona == "mike" else ""
    return (
        f"{_leg_open(matter, inline_office=False)}"
        f"{OFFICE_ROOM}"
        f"{_harvey_task(task)}"
        f"You are **{persona.title()}** on Harvey's parallel task list.\n\n"
        f"{read}\n\n"
        "Structure:\n"
        "# Office\n"
        "<what you said in the room — respond to colleagues>\n\n"
        "# Work\n"
        "<deliver the assigned task — memo, chronology, cite list, etc.>\n\n"
        + dispatch
        + NO_FABRICATION
    )


def jessica_office_take(matter: Matter, debate_dir: Path, *, task: str = "") -> str:
    read = source_read_instruction(
        mode="office", include_legs=f"Debate legs:\n{_listing(debate_dir, matter.path)}"
    )
    return (
        f"{_leg_open(matter, inline_office=False)}"
        f"{OFFICE_ROOM}"
        f"{_harvey_task(task)}"
        "You are in the room **before** Mike drafts — colleagues speaking in parallel.\n\n"
        f"{read}\n\n"
        "Managing-partner preview — merit and perception. Speak to Harvey and Tyagi.\n\n"
        "Structure:\n"
        "# Office\n"
        "<what you said in the room>\n\n"
        "# Merit preview\n"
        "<numbered risks only if material>\n\n"
        "No VERDICT — Tyagi owns procedure.\n\n"
        + NO_FABRICATION
    )


def mike_office_take(matter: Matter, debate_dir: Path, *, task: str = "") -> str:
    read = source_read_instruction(
        mode="office", include_legs=f"Debate legs:\n{_listing(debate_dir, matter.path)}"
    )
    return (
        f"{_leg_open(matter, inline_office=False)}"
        f"{OFFICE_ROOM}"
        f"{_harvey_task(task)}"
        "You are in the room **before** you draft — colleagues speaking in parallel.\n\n"
        f"{read}\n\n"
        "Associate voice: feasibility, record gaps, research plan. Push back if brief is wrong.\n\n"
        "Structure:\n"
        "# Office\n"
        "<respond to last speaker>\n\n"
        "# Drafting notes\n"
        "<bullets>\n\n"
        + NO_FABRICATION
    )


def tyagi_brief_debate(matter: Matter, debate_dir: Path, *, task: str = "") -> str:
    read = source_read_instruction(
        mode="debate", include_legs=f"Debate:\n{_listing(debate_dir, matter.path)}"
    )
    return (
        f"{_leg_open(matter, inline_office=False)}"
        f"{OFFICE_ROOM}"
        f"{_harvey_task(task)}"
        "BRIEF DEBATE — procedure map with Harvey. Hunt lapses in the client's favour; flag our "
        "exposure. Tyagi ↔ Harvey until you clear.\n\n"
        f"{read}\n\n"
        f"{WAIVER_HUNT}"
        "Number findings; FATAL/CURABLE/HARASSMENT-VALUE; state strike or cure.\n\n"
        f"{REVIEWER_TAIL}\n\n{NO_FABRICATION}"
    )


def harvey_dispatch(matter: Matter, last_artifact: Path) -> str:
    rel = last_artifact.relative_to(matter.path)
    return (
        f"{_office(matter, inline=True)}"
        f"Last leg: {rel}. You route the matter from the partner chair.\n\n"
        "Rule on every numbered objection in the room. Update harvey-context.md "
        "(Flags & rulings, Mike must/must-not, Current dispatch). "
        "Tell the room who goes next.\n\n"
        f"{DISPATCH_INSTRUCTION}\n\n" + NO_FABRICATION
    )


def harvey_signoff(matter: Matter, round_dir: Path, draft: Path, *, cap_forced: bool = False) -> str:
    from .caps import mike_draft_count, open_objections_blurb, round_cap

    rel = draft.relative_to(matter.path)
    cap_block = ""
    if cap_forced:
        cap_block = (
            f"\n**ENGINE ROUND CAP — {mike_draft_count(matter)}/{round_cap(matter)} Mike drafts spent.** "
            "You must close now. REDRAFT is not available.\n"
            f"Open gates: {open_objections_blurb(matter)}\n\n"
            "Ship with logged residual risk — list every uncleared objection, [VERIFY] cite, "
            "and client exposure in # Residual risk. Accept what cannot be fixed without another draft.\n"
        )
    header = (
        f"{_office(matter)}**Partner sign-off under round cap** — {rel} is the final draft this round.\n"
        if cap_forced
        else f"{_office(matter)}Jessica CLEARED on {rel}. **Final partner sign-off** — close the matter.\n"
    )
    read = source_read_instruction(
        mode="review", include_legs=f"Prior legs:\n{_listing(round_dir, matter.path)}"
    )
    return header + cap_block + (
        f"\n{read}\n"
        "Read the draft and Jessica's opposing-counsel review.\n\n"
        f"{FINAL_GATE}"
        "1. In # Office: tell the room you sign or send Mike back.\n"
        "2. # Sign-off — formal ruling. The FINAL GATE is a sign-off condition: a draft that "
        "still carries [VERIFY]/process language is not signable — send it back or excise on "
        "the record (residual items go to the internal risk register, never the deliverable).\n"
        "3. # Residual risk — numbered list of accepted open items (required if shipping under cap "
        "or with uncleared gates).\n"
        "4. Update harvey-context.md Current dispatch.\n\n"
        "End with exactly one line (last line of file):\n"
        "SIGNOFF: APPROVED   — adopt draft, close matter\n"
        "SIGNOFF: APPROVED WITH RESIDUAL RISK   — adopt with logged open items (use under cap or "
        "when you accept exposure)\n"
        "SIGNOFF: REDRAFT    — Mike revises; Jessica will re-review"
        + (" (unavailable — cap spent)" if cap_forced else "")
        + "\n\n"
        + NO_FABRICATION
    )


def mike_prep(matter: Matter, prep_dir: Path, *, task: str = "") -> str:
    read = source_read_instruction(
        mode="prep", include_legs=f"Debate legs:\n{_listing(prep_dir, matter.path)}"
    )
    return (
        f"{_leg_open(matter, inline_office=False)}"
        f"{OFFICE_ROOM}"
        f"{_harvey_task(task)}"
        "PRE-DRAFT with Harvey — **not** the final work product yet.\n\n"
        f"{read}\n\n"
        f"{RECORD_SWEEP}"
        "Deliver: the record-sweep inventory (read/unread per item), outline/structure, record "
        "gaps, waiver findings, the fetch list (statutes + citations to resolve before drafting), "
        "drafting risks, Mike must/must-not proposal for Harvey to rule on. **Procedure before "
        "merits** — if Tyagi has not cleared or harvey-context lists open procedure, say so and "
        "do not front-load merits research.\n\n"
        "Structure:\n"
        "# Office\n"
        "<what you said to Harvey>\n\n"
        "# Prep memo\n"
        "<outline, gaps, plan>\n\n"
        + NO_FABRICATION
    )


def tyagi_viability(matter: Matter, round_dir: Path, draft: Path | None, *, task: str = "") -> str:
    if draft and draft.exists():
        draft_ctx = (
            f"Draft at {draft.relative_to(matter.path)} — hunt fresh procedure lapses in the client's "
            "favour; gate new exposure on our side.\n"
        )
    else:
        draft_ctx = (
            "Procedure recall — brief is locked. Map lapses in the client's favour on prep, "
            "outline, or drafting plan as it stands; flag our exposure.\n"
        )
    debate = matter.path / "brief-debate" / "final-brief.md"
    debate_note = (
        "Brief cleared in brief-debate/ — attack new procedural exposure only.\n"
        if debate.exists()
        else ""
    )
    legs_ctx = f"{debate_note}{draft_ctx}Prior legs:\n{_listing(round_dir, matter.path)}"
    read = source_read_instruction(mode="debate", include_legs=legs_ctx)
    return (
        f"{_leg_open(matter, inline_office=False)}"
        f"{OFFICE_ROOM}"
        f"{_harvey_task(task)}"
        "**Tyagi** (*Maamla Legal Hai* — procedure recall). Called back mid-pipeline.\n\n"
        f"{read}\n\n"
        f"{WAIVER_HUNT}"
        "Apply your lens ruthlessly. Number each material objection and state what would "
        f"cure it.\n\n{REVIEWER_TAIL}\n\n{NO_FABRICATION}"
    )


def mike_draft(matter: Matter, round_dir: Path, prior_draft: Path | None) -> str:
    from .caps import mike_draft_count, review_cap_reached, round_cap

    redraft = (
        f"**REDRAFT** from {prior_draft.relative_to(matter.path)} — implement **every** ruled fix "
        "in this one pass. Do not dribble partial edits.\n"
        if prior_draft and prior_draft.exists()
        else ""
    )
    cap_note = ""
    if review_cap_reached(matter):
        cap_note = (
            f"\n**Last draft this round** ({mike_draft_count(matter)}/{round_cap(matter)}). "
            "Make it file-ready.\n"
        )
    elif prior_draft:
        cap_note = (
            f"\nDraft {mike_draft_count(matter) + 1}/{round_cap(matter)} this round — "
            "close all open corrections now.\n"
        )
    legs_ctx = f"{redraft}{cap_note}Prior legs:\n{_listing(round_dir, matter.path)}"
    read = source_read_instruction(mode="draft", include_legs=legs_ctx)
    return (
        f"{_leg_open(matter, inline_office=False)}"
        f"{CLIENT_WORK}"
        f"{read}\n\n"
        "Produce the **final work product** the brief calls for, in markdown. "
        "Pre-draft prep is cleared — this is the filing-ready draft.\n\n"
        f"{GOLD_STANDARD}{FINAL_GATE}"
        "**Procedure before merits:** lead with procedure where the brief calls for it; never "
        "bury open Tyagi items under merits sections. If procedural exposure is live, "
        "DISPATCH: tyagi instead of finishing a merits-heavy draft.\n\n"
        "Implement every item under 'Mike must' in harvey-context.md. "
        "Violate nothing under 'Mike must not'. "
        "Where the brief itself is wrong, add a short 'BRIEF PUSHBACK' section at the end.\n\n"
        "End with: DISPATCH: jessica\n"
        "If you spot **procedural** exposure (forum, limitation, verification, record): "
        f"DISPATCH: tyagi instead.\n\n"
        + NO_FABRICATION
    )


def jessica_review(matter: Matter, round_dir: Path, draft: Path, *, task: str = "") -> str:
    rel = draft.relative_to(matter.path)
    read = source_read_instruction(
        mode="review", include_legs=f"Prior legs:\n{_listing(round_dir, matter.path)}"
    )
    return (
        f"{_leg_open(matter, inline_office=False)}"
        f"{OFFICE_ROOM}"
        f"{_harvey_task(task)}"
        f"Review the draft at {rel} as **opposing counsel** — third-party attack, not in-house counsel.\n"
        f"{read}\n\n"
        "Attack like OC: facts vs record, weakest link, bench irritants, exposure. "
        "**Procedure before merits** — if limitation, forum, verification, service, or record "
        "is live or unchecked, DISPATCH: tyagi; do not merit-spiral past open procedure.\n"
        "**Material only** — would OC actually say this? Would the judge care?\n"
        "Do not reopen points Harvey ruled or Tyagi cleared unless the record changed.\n\n"
        f"{WAIVER_HUNT}"
        "**Completeness check:** sweep the opponent's pleading ground by ground (A–Z / 1–n) — "
        "any ground the draft leaves unanswered is a material finding, whatever the theory "
        "says.\n"
        f"{FINAL_GATE}"
        "**Procedure** (limitation, forum, verification, record) → DISPATCH: tyagi. "
        "Merit → DISPATCH: mike or harvey.\n\n"
        f"{REVIEWER_TAIL}\n\n"
        "End with: DISPATCH: harvey\n"
    )


def mike_pack(matter: Matter, doc_list: str) -> str:
    cfg = matter.config
    return (
        f"{_leg_open(matter, inline_office=False)}"
        f"{CLIENT_WORK}"
        "Fill the **client briefing pack** — four HTML docs in `final/pack/`. "
        "Edit in place; obey each template header comment.\n\n"
        f"Documents:\n{doc_list}\n\n"
        f"{FINAL_GATE}"
        f"{source_read_instruction(mode='draft', include_legs='Read final/work-product.md for pack content.')}\n"
        f"Cause title: \"{cfg.get('cause_title') or cfg.get('slug', '')}\"\n\n"
        "Write a short `# Office` note in OUT (_mike-pack-notes.md) confirming pack complete.\n"
        f"Last line: DISPATCH: closed\n\n"
        + NO_FABRICATION
    )
