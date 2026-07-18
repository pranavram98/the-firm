"""Post-office deliverables — court-templated DOCX/PDF + client pack."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .citations import audit_work_product
from .courts import draft_css, draft_header_md, infer_court_id, pandoc_reference_doc
from .matter import Matter
from .pack import deliver_client_pack
from .runtime import say


def _pandoc(src: Path, dest: Path, extra: list[str] | None = None) -> bool:
    if not shutil.which("pandoc"):
        return False
    cmd = ["pandoc", str(src), "-o", str(dest), *(extra or [])]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        say(f"pandoc: {r.stderr.strip() or r.stdout.strip()}")
        return False
    return True


def _ensure_puppeteer(cwd: Path) -> None:
    if (cwd / "node_modules" / "puppeteer").exists():
        return
    probe = subprocess.run(["node", "-e", "require('puppeteer')"], cwd=cwd, capture_output=True, text=True)
    if probe.returncode != 0:
        subprocess.run(["npm", "i", "puppeteer", "--no-audit", "--no-fund"], cwd=cwd, check=True)


def _html_to_pdf(html: Path, pdf: Path, workdir: Path) -> None:
    _ensure_puppeteer(workdir)
    script = workdir / "_render-draft.js"
    script.write_text(
        f"""const puppeteer = require('puppeteer');
(async () => {{
  const browser = await puppeteer.launch({{ headless: 'new', args: ['--no-sandbox'] }});
  const page = await browser.newPage();
  await page.goto('file://' + {json.dumps(html.resolve().as_posix())}, {{ waitUntil: 'networkidle0' }});
  await page.pdf({{
    path: {json.dumps(pdf.resolve().as_posix())},
    format: 'A4',
    printBackground: true,
    margin: {{ top: '20mm', bottom: '20mm', left: '18mm', right: '18mm' }},
  }});
  await browser.close();
}})();
""",
        encoding="utf-8",
    )
    subprocess.run(["node", str(script)], cwd=workdir, check=True)


def _styled_markdown(matter: Matter) -> Path:
    """Merge court header + body for pandoc."""
    final = matter.final_dir
    final.mkdir(exist_ok=True)
    body = matter.work_product.read_text(encoding="utf-8")
    header = draft_header_md(matter)
    styled = final / "_work-product-styled.md"
    styled.write_text(f"{header}\n{body}", encoding="utf-8")
    return styled


def export_draft(matter: Matter) -> dict:
    wp = matter.work_product
    if not wp.is_file():
        return {}

    matter.update_config(court=infer_court_id(matter))
    audit_work_product(matter)
    final = matter.final_dir
    final.mkdir(exist_ok=True)
    out: dict = {"court": matter.config.get("court", "default")}

    styled = _styled_markdown(matter)
    css_path = final / "_court-draft.css"
    css_path.write_text(draft_css(matter), encoding="utf-8")

    docx = final / "work-product.docx"
    docx_args = ["--standalone"]
    ref = pandoc_reference_doc(matter)
    if ref:
        docx_args += [f"--reference-doc={ref}"]
    if _pandoc(styled, docx, docx_args):
        out["docx"] = str(docx)
    else:
        out["docx_note"] = "install pandoc for DOCX (brew install pandoc)"

    pdf = final / "work-product.pdf"
    html = final / "_work-product.html"
    if _pandoc(styled, html, ["--standalone", f"--css={css_path}"]):
        _html_to_pdf(html, pdf, final)
        out["pdf"] = str(pdf)
    elif _pandoc(styled, pdf, ["--pdf-engine=pdflatex"]):
        out["pdf"] = str(pdf)
    else:
        out["pdf_note"] = "needs pandoc (+ node for HTML→PDF)"

    return out


def finish_deliverables(matter: Matter) -> dict:
    if not matter.work_product.is_file():
        return {}
    say("building court-templated deliverables …")
    out = export_draft(matter)
    try:
        out.update(deliver_client_pack(matter))
    except (SystemExit, subprocess.CalledProcessError, OSError) as e:
        out["pack_note"] = str(e) if str(e) else "spawn mike for client pack: firm pack-next, then firm export"
    return out
