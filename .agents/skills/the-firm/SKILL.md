---
name: the-firm
description: Run the-firm — Tyagi/Mike/Jessica legs and full Codex pipeline through client pack + export.
---

# the-firm — Codex

You execute **Tyagi**, **Mike**, or **Jessica** legs Harvey delegates from `firm next` — or run the full loop here when Harvey orchestrates in Codex (`$the-firm`).

**Universal rule: procedure before merits** — Tyagi maps procedure before Mike drafts merits; route live procedure to Tyagi; Jessica does not CLEARED past open procedure.

## Pipeline (Harvey runs `firm next` until `pause: complete`)

1. Harvey ↔ Tyagi (brief) → lock brief
2. Harvey ↔ Mike (prep) → lock prep
3. Mike → final draft
4. Jessica → OC review → Harvey synthesize
5. Harvey sign-off → **adopt**
6. **Mike → client pack** (4 HTML docs in `final/pack/`)
7. **`firm engine … export`** → DOCX + PDF + pack PDFs

Caps (`matter.yaml`): `brief_cap` 3 · `prep_cap` 2 · `round_cap` 3

Subagents: `~/.agents/agents/{tyagi,mike,jessica}.md` · `firm install-skill codex`

## Your leg

Harvey pastes **MATTER**, **OUT**, **TASK**, and **`prompt_file`**. Read that file — do **not** paste it into chat. Write only to **OUT**.

## Large records

At `firm open`, the engine writes **`sources/index.md`**. **Index first on every leg** — but prep/debate/draft still **read substantive filings in full** (split large scans). Review legs use index + draft; open originals when a pin or procedure turn needs the source.

**Prep is the exception — coverage beats economy.** Mike's prep opens with a **record sweep**: inventory every document of every party from the index/annexure lists (including every parallel proceeding — writs, company-law, settlement, criminal), read/unread mark per item; **no drafting while any party's substantive submissions are unread**. Scanned PDFs: split page-ranges (pypdf) into `sources/splits/` and Read visually; chart printed-vs-PDF page offsets in the index Scope.

## Ops (every delegate leg)

- Read `sources/index.md`, then `brief.md` and `harvey-context.md` before writing.
- **Fetch, don't flag:** statutes to quote and full law-report citations belong on a fetch list **resolved before the draft leg** — bare Act, compendium, law report. `[VERIFY]` is an **interim-leg tag only**.
- **Citation key:** one per deliverable; pins to the **impugned order's own internal pagination** (the pages the bench holds). Merged-bundle page numbers live only in an internal mapping annex.
- **Waiver hunt (Tyagi; Mike/Jessica echo):** for every procedural objection pressed on appeal — was it taken below? Silence in the record is the first answer, with the pin.
- **Completeness vs their pleading:** every opposing ground (A–Z / 1–n) gets an answer somewhere before sign-off.
- **Gold-standard drafting (Mike):** dispositive answers first; numbered propositions in argument order; answer every opposing ground; full citations; no 200-word blocks.
- **Final gate (Jessica enforces; Mike on pack):** nothing ships with [VERIFY], "page not pinned", source paths in pins, or pipeline branding — `firm export` refuses a dirty pack. Footers name the responsible counsel.

## Deliverables (`final/`)

| File | What |
|------|------|
| `work-product.md` | Adopted filing (markdown) |
| `work-product.docx` | Court-templated Word |
| `work-product.pdf` | Court-templated PDF |
| `pack/Briefing Memo.pdf` | Full matter brief |
| `pack/Argument Notes.pdf` | Speaking-order arguments |
| `pack/Client Briefing (2pp).pdf` | Client two-pager |
| `pack/Reference Table.pdf` | Record-indexed cites |

Work: `~/Documents/firm-matters/<slug>/` · live transcript in `office.md`
