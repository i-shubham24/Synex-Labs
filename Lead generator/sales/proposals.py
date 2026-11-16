"""
Proposal draft per prospect: a printable page (Save as PDF from the browser).
Stays local; it is never copied to the public site.
"""

import html
import logging
from datetime import date, timedelta, datetime, timezone
from typing import Dict, Any, Optional

from config.settings import settings
from database.prospect_repository import ProspectRepository
from brain.gemini_analyzer import GeminiAnalyzer, GeminiUnavailable
from brain.prompts import PROPOSAL_SYSTEM_INSTRUCTION
from showcase.pages import ensure_slug, page_dir
from .packages import recommend, price_text, load_packages

logger = logging.getLogger("sales.proposals")
E = lambda v: html.escape(str(v or ""), quote=True)  # noqa: E731

CSS = """
:root{--bg:#ffffff;--ink:#11110f;--muted:#5c5a53;--line:rgb(17 17 15/.14);--accent:#ff4a14}
*{box-sizing:border-box}body{margin:0;background:#f2efe8;color:var(--ink);font:15px/1.6 'Segoe UI',system-ui,sans-serif}
.page{max-width:820px;margin:24px auto;background:var(--bg);padding:56px 60px;border:1px solid var(--line)}
header{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid var(--ink);padding-bottom:18px}
.mark{display:inline-grid;place-items:center;width:40px;height:40px;background:var(--accent);font:800 15px/1 system-ui;border-radius:4px}
.meta{text-align:right;color:var(--muted);font-size:13px}
h1{font-size:30px;letter-spacing:-.02em;margin:32px 0 6px}h2{font-size:13px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:30px 0 10px}
ul{margin:0;padding-left:18px}li{margin:4px 0}
table{width:100%;border-collapse:collapse;margin-top:6px}td{padding:10px 0;border-bottom:1px solid var(--line)}td:last-child{text-align:right;font-weight:700}
.total td{border-bottom:2px solid var(--ink);font-size:18px}
.note{color:var(--muted);font-size:13px}
.bar{max-width:820px;margin:16px auto 0;display:flex;gap:8px;justify-content:flex-end}
.bar button{font:inherit;padding:8px 14px;border:1px solid var(--ink);background:var(--accent);border-radius:4px;cursor:pointer;font-weight:600}
@media print{body{background:#fff}.page{margin:0;border:0;padding:0}.bar{display:none}}
"""


def build_proposal(prospect_id: int, package_id: Optional[str] = None) -> Dict[str, Any]:
    p = ProspectRepository.get(prospect_id)
    if not p:
        raise ValueError("prospect not found")
    pkg = next((x for x in load_packages() if x["id"] == package_id), None) or recommend(p)
    intro, outcomes = None, None
    gemini = GeminiAnalyzer()
    if gemini.is_configured():
        try:
            data = gemini.generate_json(
                f"Business: {p['name']} ({p.get('niche')}, {p.get('city')})\n"
                f"Website: {p.get('website') or 'none'}\nFindings:\n" +
                "\n".join(f"- {i}" for i in (p.get('issues') or [])) +
                f"\nPackage: {pkg['name']}: {pkg.get('summary')}",
                PROPOSAL_SYSTEM_INSTRUCTION,
            )
            intro = str(data.get("intro") or "") or None
            outcomes = [str(x) for x in (data.get("outcomes") or [])][:3] or None
        except (GeminiUnavailable, ValueError) as e:
            logger.info(f"Proposal intro via template ({e})")
    intro = intro or (
        f"{p['name']} deserves a website that matches the quality of its work. "
        f"We will design and build a fast, modern site that helps customers in {(p.get('city') or 'your area').split(',')[0]} "
        f"find you, trust you and get in touch."
    )
    outcomes = outcomes or [
        "A fast site that works on every phone",
        "Clear calls to action so visitors call or book",
        "Found on Google for the services you offer",
    ]
    today = date.today()
    price = price_text(pkg, p)
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>Proposal for {E(p['name'])}</title><style>{CSS}</style></head><body>
<div class="bar"><button onclick="window.print()">Save as PDF</button></div>
<div class="page">
<header><div><span class="mark">SN</span><div style="margin-top:8px"><b>Synex Labs</b><br><span class="note">{E(settings.SITE_URL.replace('https://', ''))}</span></div></div>
<div class="meta">Proposal<br>{today:%d %B %Y}<br>Valid until {(today + timedelta(days=14)):%d %B %Y}</div></header>
<h1>Website proposal for {E(p['name'])}</h1>
<p>{E(intro)}</p>
<h2>What you get</h2><ul>{''.join(f'<li>{E(o)}</li>' for o in outcomes)}</ul>
<h2>Scope: {E(pkg['name'])}</h2><ul>{''.join(f'<li>{E(d)}</li>' for d in pkg.get('deliverables') or [])}</ul>
<h2>Timeline</h2><p>About {E(pkg.get('timelineDays'))} days from kickoff to launch, with a review round at each stage.</p>
<h2>Investment</h2>
<table><tr><td>{E(pkg['name'])}</td><td>{E(price)}</td></tr>
<tr class="total"><td>Total</td><td>{E(price)}</td></tr></table>
<p class="note">50% to start, 50% at launch. Hosting and domain costs, if any, are billed at cost.</p>
<h2>Next steps</h2><ol><li>Reply to confirm, or ask for changes to the scope.</li><li>We send the invoice for the first 50% and a kickoff questionnaire.</li><li>Design preview within the first week.</li></ol>
<p class="note" style="margin-top:36px">{E(settings.EMAIL_SIGNATURE_NAME)}, Synex Labs</p>
</div></body></html>"""
    slug = ensure_slug(p)
    out = page_dir(slug)
    out.mkdir(parents=True, exist_ok=True)
    (out / "proposal.html").write_text(body, encoding="utf-8")
    ProspectRepository.update(prospect_id, proposal_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    return {"ok": True, "slug": slug, "package": pkg["name"], "price": price}
