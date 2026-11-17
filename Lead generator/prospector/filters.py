"""
Leaves out places that are not our clients:
government and public bodies, embassies and consulates, income tax / GST offices,
and real estate (agents, builders, property dealers).
"""

import re
from typing import Dict, Optional

PUBLIC_NAME_RE = re.compile(
    r"\b(CGHS|ESIC?|ECHS|DGD|PHC|UPHC|CHC|AIIMS|Mohalla Clinic|Government|Govt\.?|Municipal|Municipality|"
    r"(?:Urban )?Primary Health Cent(?:re|er)|Community Health Cent(?:re|er)|Urban Health Cent(?:re|er)|Civil Hospital|District Hospital|"
    r"General Hospital|Railway Hospital|Military Hospital|Police Hospital|Cantonment|"
    r"Kendriya Vidyalaya|Navodaya Vidyalaya|Sarvodaya|Rajkiya|Zilla Parishad|Panchayat|"
    r"Post Office|Police Station|Collectorate|Tehsil|Ministry|Directorate|Zonal Office|"
    r"Authority|Council|Commissioner|Department of|Transport Department)\b",
    re.I,
)
DIPLOMATIC_NAME_RE = re.compile(r"\b(Embassy|Consulate|High Commission|Consul General|Diplomatic|Chancery)\b", re.I)
TAX_NAME_RE = re.compile(r"\b(Income ?Tax|Aayakar|Aaykar|GST Bhawan|GST Bhavan|Tax Office|Tax Department|CGST|SGST)\b", re.I)
REAL_ESTATE_NAME_RE = re.compile(
    r"\b(Real ?Estate|Realty|Realtors?|Propert(?:y|ies)|Estates|Builders?|Promoters|Housing|Infra(?:structure)? Projects|Land ?Developers?)\b",
    re.I,
)

EXCLUDED_NICHES = {
    "government", "diplomatic", "embassy", "consulate", "tax", "real estate agent", "real estate", "estate agent",
    "estate agent office", "politician", "political party",
}
# OpenStreetMap tags that mark the same things
EXCLUDED_TAGS = {
    "office": {"government", "diplomatic", "estate_agent", "tax", "politician", "political_party", "real_estate"},
    "shop": {"estate_agent"},
    "amenity": {"embassy", "townhall", "courthouse", "police", "post_office", "prison", "fire_station"},
}
PUBLIC_OPERATOR_TYPES = {"government", "public", "military", "community"}


def is_public_facility(name: str, tags: Optional[Dict[str, str]] = None) -> bool:
    if PUBLIC_NAME_RE.search(name or ""):
        return True
    if tags:
        if (tags.get("operator:type") or "").lower() in PUBLIC_OPERATOR_TYPES:
            return True
        if PUBLIC_NAME_RE.search(tags.get("operator") or ""):
            return True
        if tags.get("government") or tags.get("diplomatic"):
            return True
    return False


def is_excluded(name: str, niche: Optional[str] = None, tags: Optional[Dict[str, str]] = None) -> bool:
    """True for anything we never pitch: government, embassies, tax offices, real estate."""
    if (niche or "").strip().lower() in EXCLUDED_NICHES:
        return True
    if tags:
        for key, values in EXCLUDED_TAGS.items():
            if (tags.get(key) or "") in values:
                return True
    n = name or ""
    return bool(
        is_public_facility(n, tags)
        or DIPLOMATIC_NAME_RE.search(n)
        or TAX_NAME_RE.search(n)
        or REAL_ESTATE_NAME_RE.search(n)
    )
