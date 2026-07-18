# the-firm

**One matter. One office. Four egos. Zero infinite loops.**

We always wished those characters were actually in the office. **Harvey** runs the room. **Tyagi** hunts procedure lapses in your favour — often enough to knock a case off or win on a point. **Mike** drafts the filing. **Jessica** reads it like opposing counsel with a grudge. They talk to each other while they work — you get court-ready files when Harvey signs off.

Personality from the shows (*Suits*, *Maamla Legal Hai*). **Law from your case** — Delhi HC, Singapore, whatever forum you name.

**Lawyers → [LAWYERS.md](LAWYERS.md)** (plain English, no terminal after setup).

---

## Start a matter

1. **Upload your case files** — orders, pleadings, scans, chronology folders (point Harvey at the folder path).
2. **Describe the matter in plain English** — court, parties, posture, what you need drafted.
3. **Let the firm run** — Harvey opens the office; Tyagi, Mike, and Jessica rip through the record in parallel.

Claude Code: **`/the-firm`** · Codex: **`$the-firm`**

Example:

```
Delhi HC. ABC v XYZ. Oppose condonation of delay.
Files: ~/Desktop/my-case-folder
```

**Big records:** split very large scans into smaller PDFs before upload. The firm builds a **record index** first — agents read that, and open originals only when a fact is in dispute.

---

## The cast

| | Role | Vibe |
|---|------|------|
| **Harvey** | Partner / conductor | Opens, synthesizes, rules, signs. Does not draft. |
| **Tyagi** | Procedure hunter | Lapses in your favour — limitation, forum, record — *Maamla Legal Hai* energy. |
| **Mike** | Associate | Prep, draft, client pack. Record-sharp, filing voice. |
| **Jessica** | Opposing counsel | Attacks the draft. Material objections only. |

Hard caps so loops **always** terminate: 3 strategy passes · 2 prep rounds · 3 drafts → ship with residual risk if needed.

**Universal rule:** procedure before merits — every leg, every forum.

---

## How a matter runs

```
You: case files + plain English ask
        ↓
Harvey opens the office → strategy + assignments
        ↓
Tyagi ↔ Harvey (procedure map) → strategy locked
        ↓
Mike prep → plan locked → Mike draft
        ↓
Jessica OC review → Harvey synthesize → sign-off → adopt
        ↓
Mike client pack → DOCX + PDF + four pack PDFs → done
```

Harvey spawns subagents; the CLI holds state (`firm next` → spawn → `firm record-leg`).

---

## Install

```bash
git clone https://github.com/pranavram98/the-firm.git
cd the-firm
uv tool install .
firm install-skill claude   # Claude Code
firm install-skill codex    # Codex
```

`firm setup` checks pandoc/node for export. Each matter lives in `~/Documents/firm-matters/<slug>/`.

---

## What you get

| Output | What it is |
|--------|------------|
| Live transcript | The office conversation while they work |
| Adopted filing | Word + PDF + markdown of the signed draft |
| Client pack | Briefing Memo, Argument Notes, Client Briefing (2pp), Reference Table |

---

## Dev

```bash
uv run pytest    # 26 tests
```

Weekend experiment. Feedback welcome.
