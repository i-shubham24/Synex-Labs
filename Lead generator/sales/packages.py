"""Reads service packages straight from the website (src/data/packages.ts), so prices stay in one place."""

import re
from functools import lru_cache
from typing import Dict, Any, List

from config.settings import BASE_DIR

PACKAGES_TS = BASE_DIR.parent / "src" / "data" / "packages.ts"

DEFAULTS = [
    {"id": "synex-starter-website", "name": "Starter Business Website Package", "kind": "Website",
     "summary": "A fast company website with SEO and an enquiry form.", "price": 499, "priceInr": 24999,
     "timelineDays": 7, "deliverables": ["Custom responsive design", "Technical SEO", "Lead capture form"]},
    {"id": "synex-ecommerce-store", "name": "E-Commerce Online Storefront", "kind": "Online store",
     "summary": "Online store with catalogue, cart and payments.", "price": 999, "priceInr": 49999,
     "timelineDays": 21, "deliverables": ["Product catalogue", "Cart and checkout", "Payment gateway"]},
]

STORE_NICHES = ("clothing", "jewel", "furniture", "boutique", "store", "shop", "florist", "bakery")


@lru_cache(maxsize=1)
def load_packages() -> List[Dict[str, Any]]:
    try:
        text = PACKAGES_TS.read_text(encoding="utf-8")
    except OSError:
        return DEFAULTS
    blocks = re.split(r"\n\s*\{\s*\n\s*id:", text)[1:]
    out = []
    for block in blocks:
        block = "id:" + block

        def field(name, pattern=r'"([^"]*)"'):
            m = re.search(rf"\b{name}:\s*{pattern}", block)
            return m.group(1) if m else None

        deliverables_m = re.search(r"deliverables:\s*\[(.*?)\]", block, re.S)
        deliverables = re.findall(r'"([^"]+)"', deliverables_m.group(1)) if deliverables_m else []
        try:
            out.append({
                "id": field("id"),
                "name": field("name"),
                "kind": field("kind"),
                "summary": field("summary"),
                "price": int(field("price", r"(\d+)") or 0),
                "priceInr": int(field("priceInr", r"(\d+)") or 0),
                "timelineDays": int(field("timelineDays", r"(\d+)") or 0),
                "deliverables": deliverables,
            })
        except (TypeError, ValueError):
            continue
    return [p for p in out if p["id"] and p["name"] and p["price"]] or DEFAULTS


def recommend(prospect: Dict[str, Any]) -> Dict[str, Any]:
    packages = load_packages()
    niche = (prospect.get("niche") or "").lower()
    wanted = "Online store" if any(k in niche for k in STORE_NICHES) else "Website"
    for p in packages:
        if p["kind"] == wanted:
            return p
    return packages[0]


def is_india(prospect: Dict[str, Any]) -> bool:
    return "india" in (prospect.get("city") or "").lower() or (prospect.get("phone") or "").strip().startswith("+91")


def price_text(package: Dict[str, Any], prospect: Dict[str, Any]) -> str:
    if is_india(prospect) and package.get("priceInr"):
        return f"Rs {package['priceInr']:,}"
    return f"${package['price']:,}"
