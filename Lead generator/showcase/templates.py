"""
Static HTML for the two showcase pages. Self-contained (inline CSS, no external
requests), noindex, and built only from real data about the business.
"""

import html
import urllib.parse
from datetime import date
from typing import Dict, Any, List, Optional

from config.settings import settings

E = lambda v: html.escape(str(v or ""), quote=True)  # noqa: E731

# ---------------------------------------------------------------------------- shared

def studio_cta(business: str) -> List[Dict[str, str]]:
    """Ways for the prospect to reach Synex Labs."""
    links = []
    digits = "".join(ch for ch in settings.STUDIO_WHATSAPP if ch.isdigit())
    if digits:
        text = urllib.parse.quote(f"Hi Synex Labs, I saw the page you made for {business}.")
        links.append({"label": "WhatsApp us", "href": f"https://wa.me/{digits}?text={text}"})
    if settings.BOOKING_URL:
        links.append({"label": "Book a 15 min call", "href": settings.BOOKING_URL})
    if settings.STUDIO_EMAIL:
        links.append({"label": "Email us", "href": f"mailto:{settings.STUDIO_EMAIL}?subject={urllib.parse.quote('Website for ' + business)}"})
    if not links:
        links.append({"label": "Talk to Synex Labs", "href": f"{settings.SITE_URL}/#contact"})
    return links


HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="referrer" content="no-referrer">
<title>{title}</title>
<style>{css}</style>
</head>
"""

# ---------------------------------------------------------------------------- demo homepage

PALETTES = {
    "health":   {"bg": "#f3f8f8", "ink": "#0f2a2e", "muted": "#4d6668", "accent": "#0f8b8d", "soft": "#dcefee", "on": "#ffffff", "serif": False},
    "beauty":   {"bg": "#fbf6f4", "ink": "#2b1d1f", "muted": "#715a5e", "accent": "#b84c70", "soft": "#f5e3e6", "on": "#ffffff", "serif": True},
    "food":     {"bg": "#fbf7f0", "ink": "#2a1d12", "muted": "#6e5a47", "accent": "#bf5f1a", "soft": "#f4e6d3", "on": "#ffffff", "serif": True},
    "legal":    {"bg": "#f6f6f3", "ink": "#151c2c", "muted": "#555c6b", "accent": "#9a7a2e", "soft": "#ebe6d8", "on": "#ffffff", "serif": True},
    "fitness":  {"bg": "#101211", "ink": "#f1f3ef", "muted": "#a3aaa2", "accent": "#b6e33b", "soft": "#1b1f1c", "on": "#101211", "serif": False},
    "property": {"bg": "#f4f7f5", "ink": "#14231c", "muted": "#53635b", "accent": "#1f7a55", "soft": "#dcebe3", "on": "#ffffff", "serif": False},
    "trades":   {"bg": "#f4f7fb", "ink": "#101a2b", "muted": "#4d5a70", "accent": "#2457d6", "soft": "#e0e8f8", "on": "#ffffff", "serif": False},
    "default":  {"bg": "#f6f6f8", "ink": "#16161d", "muted": "#585866", "accent": "#4f46e5", "soft": "#e6e5fa", "on": "#ffffff", "serif": False},
}

GROUPS = [
    ("health", ("dent", "clinic", "doctor", "physio", "health", "medical", "optic", "vet", "pharm", "chiro")),
    ("beauty", ("salon", "hair", "beauty", "spa", "barber", "nail", "makeup", "skin")),
    ("food", ("restaurant", "cafe", "café", "bakery", "food", "bar", "catering", "pizza", "coffee")),
    ("legal", ("lawyer", "law", "legal", "account", "tax", "consult", "notary")),
    ("fitness", ("gym", "fitness", "yoga", "pilates", "martial", "crossfit", "sport")),
    ("property", ("real estate", "estate", "property", "realtor", "architect", "interior")),
    ("trades", ("plumb", "electric", "hvac", "roof", "repair", "clean", "construct", "garage", "mechanic", "car")),
]

FALLBACK_COPY = {
    "health": ("Care that puts you at ease", "Modern treatment, friendly people and appointments that fit your day.",
               ["Check-ups", "Treatments", "Emergency visits", "Family care", "Consultations", "Aftercare"], "Book a visit"),
    "beauty": ("Look good, feel better", "Skilled hands, a relaxed space and a look made for you.",
               ["Cuts and styling", "Colour", "Treatments", "Bridal and events", "Grooming", "Care advice"], "Book now"),
    "food": ("Good food, made with care", "Fresh dishes, a warm welcome and a table waiting for you.",
             ["Dine in", "Takeaway", "Group bookings", "Seasonal menu", "Private events", "Catering"], "Reserve a table"),
    "legal": ("Clear advice you can rely on", "Straight answers and steady guidance when it matters most.",
              ["Consultations", "Documents", "Representation", "Business advice", "Personal matters", "Ongoing support"], "Book a consultation"),
    "fitness": ("Stronger every week", "Coaching, equipment and a community that keeps you going.",
                ["Memberships", "Personal training", "Group classes", "Strength", "Conditioning", "Nutrition tips"], "Start today"),
    "property": ("Find the right place", "Local know-how to help you buy, sell or rent with confidence.",
                 ["Buying", "Selling", "Renting", "Valuations", "Property management", "Local advice"], "Talk to us"),
    "trades": ("Fixed right, first time", "Reliable work, honest quotes and people who turn up when they say.",
               ["Repairs", "Installations", "Maintenance", "Emergency call-outs", "Inspections", "Free quotes"], "Get a quote"),
    "default": ("Quality you can count on", "A local business that cares about doing the job well.",
                ["Our services", "Consultations", "Custom work", "Support", "Advice", "Aftercare"], "Get in touch"),
}


def niche_group(niche: str) -> str:
    n = (niche or "").lower()
    for group, keys in GROUPS:
        if any(k in n for k in keys):
            return group
    return "default"


def fallback_copy(p: Dict[str, Any]) -> Dict[str, Any]:
    head, sub, services, cta = FALLBACK_COPY[niche_group(p.get("niche"))]
    city = (p.get("city") or "").split(",")[0]
    return {
        "headline": head,
        "subheadline": f"{sub} In {city}." if city else sub,
        "services": [{"title": s, "text": ""} for s in services],
        "about": f"{p.get('name')} serves customers in {city or 'the area'}. "
                 f"Call us or drop by, we are happy to help.",
        "cta": cta,
    }


def demo_css(pal: Dict[str, Any]) -> str:
    heading_font = "Georgia, 'Times New Roman', serif" if pal["serif"] else "'Segoe UI', system-ui, -apple-system, sans-serif"
    return f"""
:root{{--bg:{pal['bg']};--ink:{pal['ink']};--muted:{pal['muted']};--accent:{pal['accent']};--soft:{pal['soft']};--on:{pal['on']}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 'Segoe UI',system-ui,-apple-system,sans-serif}}
a{{color:inherit}}.wrap{{max-width:1120px;margin:0 auto;padding:0 20px}}
.concept{{background:#111;color:#f5f5f5;font-size:13px;text-align:center;padding:8px 16px}}
.concept a{{color:#ffb38a;font-weight:600;margin-left:6px}}
header{{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 90%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid color-mix(in srgb,var(--ink) 10%,transparent)}}
.nav{{display:flex;align-items:center;justify-content:space-between;height:68px;gap:16px}}
.logo{{font:700 20px/1 {heading_font};letter-spacing:-.01em}}
.links{{display:flex;gap:24px;font-size:15px;color:var(--muted)}}.links a{{text-decoration:none}}
.btn{{display:inline-block;background:var(--accent);color:var(--on);padding:12px 22px;border-radius:6px;text-decoration:none;font-weight:600;transition:transform .2s,box-shadow .2s}}
.btn:hover{{transform:translateY(-2px);box-shadow:0 10px 24px -12px var(--accent)}}
.btn.ghost{{background:transparent;color:var(--ink);border:1.5px solid color-mix(in srgb,var(--ink) 25%,transparent)}}
.hero{{display:grid;grid-template-columns:1.1fr .9fr;gap:48px;align-items:center;padding:72px 0 64px}}
.hero h1{{font:700 clamp(38px,5.4vw,64px)/1.05 {heading_font};letter-spacing:-.02em;margin:0 0 18px}}
.hero p{{font-size:19px;color:var(--muted);margin:0 0 28px;max-width:34ch}}
.actions{{display:flex;gap:12px;flex-wrap:wrap}}
.proof{{margin-top:26px;display:flex;align-items:center;gap:10px;color:var(--muted);font-size:15px}}
.stars{{color:var(--accent);letter-spacing:2px}}
.art{{position:relative;aspect-ratio:1/1;border-radius:14px;background:radial-gradient(circle at 30% 30%,var(--soft),transparent 60%),linear-gradient(135deg,var(--accent),color-mix(in srgb,var(--accent) 40%,var(--ink)));overflow:hidden}}
.art::before,.art::after{{content:"";position:absolute;border-radius:50%;background:color-mix(in srgb,var(--on) 18%,transparent);animation:float 9s ease-in-out infinite}}
.art::before{{width:55%;height:55%;right:-10%;top:-8%}}.art::after{{width:38%;height:38%;left:8%;bottom:6%;animation-delay:-4s}}
.art span{{position:absolute;left:8%;bottom:10%;font:700 clamp(40px,7vw,84px)/1 {heading_font};color:var(--on);opacity:.92;max-width:84%}}
section{{padding:72px 0}}.eyebrow{{text-transform:uppercase;letter-spacing:.14em;font-size:12px;color:var(--accent);font-weight:700}}
h2{{font:700 clamp(28px,3.4vw,40px)/1.15 {heading_font};margin:8px 0 28px;letter-spacing:-.01em}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}
.card{{background:color-mix(in srgb,var(--soft) 70%,var(--bg));border-radius:10px;padding:24px;transition:transform .25s}}
.card:hover{{transform:translateY(-4px)}}.card h3{{margin:0 0 6px;font-size:18px}}.card p{{margin:0;color:var(--muted);font-size:15px}}
.num{{font:700 13px/1 ui-monospace,monospace;color:var(--accent);margin-bottom:14px;display:block}}
.about{{display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center}}
.about p{{font-size:18px;color:var(--muted)}}
.visit{{background:var(--ink);color:var(--bg);border-radius:14px;padding:44px;display:grid;grid-template-columns:1.2fr .8fr;gap:32px;align-items:center}}
.visit h2{{color:var(--bg);margin:0 0 12px}}.visit p{{margin:4px 0;opacity:.85}}
.visit .btn{{background:var(--accent);color:var(--on)}}
footer{{padding:36px 0;color:var(--muted);font-size:14px;text-align:center}}
.reveal{{animation:rise .7s ease both}}
@keyframes rise{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:none}}}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-14px)}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
@media (max-width:820px){{.hero,.about,.visit{{grid-template-columns:1fr}}.grid{{grid-template-columns:1fr 1fr}}.links{{display:none}}.hero{{padding:40px 0}}}}
@media (max-width:520px){{.grid{{grid-template-columns:1fr}}.visit{{padding:28px}}}}
"""


def render_demo(p: Dict[str, Any], copy: Dict[str, Any]) -> str:
    pal = PALETTES[niche_group(p.get("niche"))]
    name = p.get("name") or "Your business"
    city = (p.get("city") or "").split(",")[0]
    phone = p.get("phone") or ""
    tel = "tel:" + "".join(ch for ch in phone if ch.isdigit() or ch == "+") if phone else "#visit"
    maps = p.get("maps_url") or "#visit"
    cta = copy.get("cta") or "Get in touch"
    services = (copy.get("services") or [])[:6]
    studio = studio_cta(name)[0]

    proof = ""
    if p.get("rating") and p.get("review_count"):
        proof = (f'<div class="proof"><span class="stars">★</span>'
                 f'<span>{E(p["rating"])} from {E(p["review_count"])} Google reviews</span></div>')

    cards = "".join(
        f'<div class="card reveal" style="animation-delay:{i * 60}ms"><span class="num">0{i + 1}</span>'
        f'<h3>{E(s.get("title"))}</h3>' + (f'<p>{E(s.get("text"))}</p>' if s.get("text") else "") + "</div>"
        for i, s in enumerate(services)
    )
    visit_lines = "".join(f"<p>{E(x)}</p>" for x in (p.get("address"), phone) if x)

    body = f"""<body>
<div class="concept">Concept preview made by Synex Labs for {E(name)}. This is not the official website.
<a href="{E(studio['href'])}" target="_blank" rel="noopener">{E(studio['label'])}</a></div>
<header><div class="wrap nav"><div class="logo">{E(name)}</div>
<nav class="links"><a href="#services">Services</a><a href="#about">About</a><a href="#visit">Visit</a></nav>
<a class="btn" href="{E(tel)}">{E(cta)}</a></div></header>
<main class="wrap">
<div class="hero"><div class="reveal"><h1>{E(copy.get('headline'))}</h1><p>{E(copy.get('subheadline'))}</p>
<div class="actions"><a class="btn" href="{E(tel)}">{E(cta)}</a><a class="btn ghost" href="{E(maps)}" target="_blank" rel="noopener">Get directions</a></div>
{proof}</div>
<div class="art reveal" style="animation-delay:120ms" aria-hidden="true"><span>{E(city or name)}</span></div></div>
<section id="services"><div class="eyebrow">What we do</div><h2>Services</h2><div class="grid">{cards}</div></section>
<section id="about" class="about"><div><div class="eyebrow">About</div><h2>{E(name)}</h2></div><p>{E(copy.get('about'))}</p></section>
<section id="visit"><div class="visit"><div><h2>Visit us{(' in ' + E(city)) if city else ''}</h2>{visit_lines}</div>
<div class="actions"><a class="btn" href="{E(tel)}">{E(cta)}</a><a class="btn ghost" style="color:inherit;border-color:currentColor" href="{E(maps)}" target="_blank" rel="noopener">Open in Maps</a></div></div></section>
</main>
<footer>© {date.today().year} {E(name)} · Concept design by Synex Labs</footer>
</body></html>"""
    return HEAD.format(title=E(f"{name} | Concept preview"), css=demo_css(pal)) + body


# ---------------------------------------------------------------------------- audit page

FIXES = [
    (("https", "ssl", "not secure"), "Install a free SSL certificate and force HTTPS so browsers stop warning visitors."),
    (("phone", "viewport", "mobile friendly"), "Rebuild the layout so it works on phones, where most of your visitors are."),
    (("load", "speed score", "seconds"), "Compress images, cache pages and serve the site from a fast network."),
    (("copyright",), "Refresh the content so the site looks current and cared for."),
    (("wordpress",), "Update the site or move it to a modern, low-maintenance setup."),
    (("flash", "jquery"), "Replace outdated code with modern, supported components."),
    (("title tag", "meta description"), "Write proper page titles and descriptions so Google shows you well."),
    (("free", "own domain"), "Move to your own domain so customers trust the address."),
    (("page not found", "down", "dead end", "shut down"), "Fix the link on your Google listing and bring the site back online."),
    (("dated", "design"), "A clean, modern design that matches the quality of your work."),
    (("no website", "social page"), "A simple, fast website of your own that shows up on Google."),
]


def fix_for(issue: str) -> str:
    low = issue.lower()
    for keys, fix in FIXES:
        if any(k in low for k in keys):
            return fix
    return "We would fix this as part of a refresh."


AUDIT_CSS = """
:root{--bg:#f2efe8;--card:#faf8f3;--ink:#11110f;--muted:#5c5a53;--line:rgb(17 17 15/.14);--accent:#ff4a14}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 'Segoe UI',system-ui,-apple-system,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:0 20px}a{color:inherit}
header{display:flex;align-items:center;gap:12px;padding:22px 0;border-bottom:1px solid var(--line)}
.mark{display:inline-grid;place-items:center;width:38px;height:38px;background:var(--accent);color:var(--ink);font:800 15px/1 system-ui;border-radius:4px}
header small{color:var(--muted);display:block}
h1{font:700 clamp(30px,4.6vw,48px)/1.1 system-ui;letter-spacing:-.02em;margin:40px 0 10px}
.lede{font-size:18px;color:var(--muted);max-width:60ch;margin:0 0 28px}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:32px}
.metric{background:var(--card);border:1px solid var(--line);border-radius:4px;padding:14px 16px}
.metric b{display:block;font-size:22px;letter-spacing:-.02em}.metric span{color:var(--muted);font-size:13px}
.bad b{color:var(--accent)}
.shots{display:grid;grid-template-columns:3fr 1fr;gap:12px;margin:0 0 36px;align-items:start}
.shots figure{margin:0}.shots img{width:100%;display:block;border:1px solid var(--line);border-radius:4px;background:#fff}
.shots figcaption{font-size:12px;color:var(--muted);margin-top:6px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:0 0 12px}
.finding{display:grid;grid-template-columns:28px 1fr;gap:12px;padding:16px 0;border-top:1px solid var(--line)}
.finding i{width:10px;height:10px;background:var(--accent);margin-top:8px;border-radius:1px}
.finding p{margin:0}.finding .fix{color:var(--muted);font-size:15px;margin-top:2px}
.good{margin:28px 0;padding:14px 16px;border-left:3px solid #1f7a3a;background:var(--card)}
.cta{margin:40px 0 56px;padding:28px;background:var(--ink);color:var(--bg);border-radius:4px}
.cta h2{color:var(--bg);font-size:22px;text-transform:none;letter-spacing:-.01em;margin:0 0 8px}
.cta p{margin:0 0 18px;opacity:.8}.btns{display:flex;gap:10px;flex-wrap:wrap}
.btn{display:inline-block;padding:11px 18px;border-radius:4px;background:var(--accent);color:var(--ink);text-decoration:none;font-weight:700}
.btn.alt{background:transparent;color:var(--bg);border:1px solid rgb(242 239 232/.4)}
footer{color:var(--muted);font-size:13px;padding:0 0 40px}
@media (max-width:720px){.metrics{grid-template-columns:1fr 1fr}.shots{grid-template-columns:1fr}}
"""


def render_audit(p: Dict[str, Any], audit: Dict[str, Any], issues: List[str], visual: Optional[Dict[str, Any]],
                 has_desktop: bool, has_mobile: bool) -> str:
    name = p.get("name") or "your business"

    def metric(value, label, bad):
        return f'<div class="metric{" bad" if bad else ""}"><b>{E(value)}</b><span>{E(label)}</span></div>'

    load = audit.get("response_seconds")
    speed = audit.get("pagespeed_mobile")
    metrics = [
        metric("Yes" if audit.get("https") else "No", "Secure (HTTPS)", not audit.get("https")),
        metric("Yes" if audit.get("has_viewport") else "No", "Works on phones", audit.get("has_viewport") is False),
        metric(f"{load:.1f}s" if isinstance(load, (int, float)) else "n/a", "Homepage load", isinstance(load, (int, float)) and load > 3),
        metric(f"{speed}/100" if speed is not None else (audit.get("copyright_year") or "n/a"),
               "Google mobile speed" if speed is not None else "Footer year", (speed is not None and speed < 50)),
    ]
    shots = ""
    if has_desktop or has_mobile:
        shots = '<div class="shots">'
        if has_desktop:
            shots += '<figure><img src="desktop.jpg" alt="Your homepage on a laptop"><figcaption>On a laptop</figcaption></figure>'
        if has_mobile:
            shots += '<figure><img src="mobile.jpg" alt="Your homepage on a phone"><figcaption>On a phone</figcaption></figure>'
        shots += "</div>"
    all_issues = list(issues) + [f"Design: {x}" for x in ((visual or {}).get("problems") or [])]
    shown_fixes, rows = set(), []
    for issue in all_issues:
        fix = fix_for(issue)
        fix_html = "" if fix in shown_fixes else f'<p class="fix">{E(fix)}</p>'
        shown_fixes.add(fix)
        rows.append(f'<div class="finding"><i></i><div><p>{E(issue)}</p>{fix_html}</div></div>')
    findings = "".join(rows) or '<p>No major problems found by the automated checks.</p>'
    good = f'<div class="good"><b>What works:</b> {E(visual["positive"])}</div>' if visual and visual.get("positive") else ""
    btns = "".join(
        f'<a class="btn{" alt" if i else ""}" href="{E(c["href"])}" target="_blank" rel="noopener">{E(c["label"])}</a>'
        for i, c in enumerate(studio_cta(name))
    )
    site = audit.get("final_url") or p.get("website") or ""
    body = f"""<body><div class="wrap">
<header><span class="mark">SN</span><div><b>Synex Labs</b><small>Website check · {date.today():%d %B %Y}</small></div></header>
<h1>A quick look at {E(name)}'s website</h1>
<p class="lede">We checked {E(site)} the way a new customer would find it. Here is what stood out and how we would fix it.</p>
<div class="metrics">{''.join(metrics)}</div>
{shots}
<h2>What we found</h2>
{findings}
{good}
<div class="cta"><h2>Want this fixed?</h2><p>We build fast, modern websites for local businesses, usually live within a week.</p><div class="btns">{btns}</div></div>
<footer>Prepared for {E(name)} by Synex Labs from automated checks on {date.today():%d %B %Y}. Results can change as the site changes.</footer>
</div></body></html>"""
    return HEAD.format(title=E(f"Website check for {name}"), css=AUDIT_CSS) + body
