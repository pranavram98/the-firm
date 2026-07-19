# the-firm — for lawyers

Pick **one** tool — Claude Code **or** Codex. Same firm, same files, same room.

---

## Claude Code

1. Open **Claude Code** anywhere
2. **`/the-firm`** — describe the case:

```
Gujarat HC. ABC v XYZ. Draft reply opposing condonation.
Files: ~/Desktop/my-case-folder
```

Harvey **conducts the office** — *Suits* personas (Harvey, Mike, Jessica) plus Tyagi from
*Maamla Legal Hai*. Any **common-law** forum; law comes from the brief, not the shows.

---

## Codex

1. Open **Codex** anywhere (after IT runs `firm install-skill codex`)
2. **`$the-firm`** — same plain English

Harvey spawns **tyagi / mike / jessica** subagents within Codex models (Sol/Terra/Luna). Same deliverables.

---

## What you get

`~/Documents/firm-matters/<slug>/`

| | |
|--|--|
| Conversation | `office.md` |
| Draft | `final/work-product.docx` · `.pdf` · `.md` |
| **Client pack** | `final/pack/Briefing Memo.pdf` · `Argument Notes.pdf` · `Client Briefing (2pp).pdf` · `Reference Table.pdf` |

Harvey runs the pipeline to **`pause: complete`** — adopt, then Mike fills the pack, then export. You do not run terminal commands.

**Timing:** ~3–8 min per leg · ~30–60 min full matter · caps: 3 Tyagi brief passes, 2 Mike prep, 3 drafts.

**Large records:** split big scans before open; the engine builds `sources/index.md`. Index first on every leg — but **prep, brief-debate, and draft still read substantive filings in full**; review legs open originals when a pin or procedure turn needs the source.

**Universal rule:** procedure before merits — Tyagi maps procedure before Mike drafts; no merits-heavy work while procedure is open.

**Flow:** Harvey (strategy) ↔ Tyagi (procedure weapons) ↔ Mike (draft) ↔ Jessica (review). Anyone may push back or close a loop via **VERDICT** + **DISPATCH** (last line). After the draft cap, Harvey **ships with residual risk**.

---

## IT setup

```bash
git clone <repo> ~/Documents/the-firm
cd ~/Documents/the-firm
uv tool install .
firm install-skill claude    # Claude lawyers
firm install-skill codex     # Codex lawyers
```

Also: `firm setup` (defaults to Claude skill + matters folder).

Re-install after a repo update:

```bash
firm install-skill claude    # or: codex
```

---

## Tips

- One case folder · always say **jurisdiction**
- Resume: `/the-firm` or `$the-firm` with matter path under `firm-matters/`
- `[VERIFY]` = confirm that cite before filing

---

## Confidentiality

Matters stay on your machine under **`~/Documents/firm-matters/`**.
