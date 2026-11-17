"""
Business discovery sources for the Maps prospector.

- GooglePlacesSource: official Places API (New) Text Search. Accurate website/phone
  data. Needs GOOGLE_PLACES_API_KEY with billing enabled; a monthly call cap keeps
  usage inside Google's free allowance.
- OSMSource: free OpenStreetMap data (Nominatim + Overpass). No key needed, but a
  missing website tag often just means nobody mapped it, so those leads are marked
  "verify first".

Both use official APIs only. Never scrape Google Maps pages directly.
"""

import logging
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import requests

from config.settings import settings
from database.prospect_repository import ProspectRepository
from .filters import is_excluded

logger = logging.getLogger("prospector.sources")

PLACES_API = "google_places_text_search"


@dataclass
class Business:
    source: str
    place_id: str
    name: str
    address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    maps_url: str = ""
    rating: Optional[float] = None
    review_count: Optional[int] = None
    business_status: str = ""
    socials: List[str] = field(default_factory=list)
    map_added_recently: bool = False   # OpenStreetMap: created in the last year (likely a new business)
    niche: str = ""                    # set by website-group searches (kind of business from map tags)


class SourceError(Exception):
    """A search could not run (bad key, budget reached, service down)."""


def _recently_added(element: Dict[str, Any], days: int = 365) -> bool:
    """OpenStreetMap: first mapped within `days` and barely edited since, a hint of a new business."""
    from datetime import datetime, timezone, timedelta
    stamp, version = element.get("timestamp"), element.get("version") or 99
    if not stamp or version > 2:
        return False
    try:
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    return datetime.now(timezone.utc) - when <= timedelta(days=days)


def google_maps_search_link(name: str, city: str) -> str:
    query = urllib.parse.quote_plus(f"{name} {city}")
    return f"https://www.google.com/maps/search/?api=1&query={query}"


# ----------------------------------------------------------------------------
# Google Places API (New)
# ----------------------------------------------------------------------------

class GooglePlacesSource:
    name = "google_places"
    ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
    FIELD_MASK = ",".join([
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.internationalPhoneNumber",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "places.googleMapsUri",
        "places.rating",
        "places.userRatingCount",
        "places.businessStatus",
        "nextPageToken",
    ])

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GOOGLE_PLACES_API_KEY

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def remaining_budget(self) -> int:
        return max(0, settings.PLACES_MONTHLY_CALL_LIMIT - ProspectRepository.get_month_calls(PLACES_API))

    def search(self, niche: str, city: str) -> List[Business]:
        if not self.is_configured():
            raise SourceError("GOOGLE_PLACES_API_KEY is not set")

        # includeFutureOpeningBusinesses: "opening soon" listings are the best first-website leads
        body: Dict[str, Any] = {"textQuery": f"{niche} in {city}", "pageSize": 20, "includeFutureOpeningBusinesses": True}
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": self.FIELD_MASK,
        }
        results: List[Business] = []

        for page in range(settings.PLACES_PAGES_PER_SEARCH):
            if self.remaining_budget() <= 0:
                logger.warning("Places monthly call limit reached; stopping search early.")
                if not results:
                    raise SourceError(
                        f"Monthly Places limit reached ({settings.PLACES_MONTHLY_CALL_LIMIT} calls). "
                        "Raise PLACES_MONTHLY_CALL_LIMIT or wait for next month."
                    )
                break

            resp = requests.post(self.ENDPOINT, json=body, headers=headers, timeout=30.0)
            if not resp.ok:
                message = resp.text[:300]
                try:
                    message = resp.json().get("error", {}).get("message", message)
                except ValueError:
                    pass
                raise SourceError(f"Places API {resp.status_code}: {message}")

            ProspectRepository.add_calls(PLACES_API, 1)
            data = resp.json()
            for place in data.get("places", []):
                results.append(self._to_business(place))

            token = data.get("nextPageToken")
            if not token:
                break
            body["pageToken"] = token
            time.sleep(2.0)  # tokens take a moment to become valid

        return results

    def _to_business(self, place: Dict[str, Any]) -> Business:
        return Business(
            source=self.name,
            place_id=place.get("id", ""),
            name=(place.get("displayName") or {}).get("text", "Unknown"),
            address=place.get("formattedAddress", ""),
            phone=place.get("internationalPhoneNumber") or place.get("nationalPhoneNumber") or "",
            website=place.get("websiteUri", ""),
            maps_url=place.get("googleMapsUri", ""),
            rating=place.get("rating"),
            review_count=place.get("userRatingCount"),
            business_status=place.get("businessStatus", ""),
        )


# ----------------------------------------------------------------------------
# OpenStreetMap (free)
# ----------------------------------------------------------------------------

# Niche words -> OpenStreetMap tags. Google takes free text; OSM needs real tags.
OSM_NICHE_TAGS: Dict[str, List[tuple]] = {
    "dentist": [("amenity", "dentist")],
    "hair salon": [("shop", "hairdresser")],
    "salon": [("shop", "hairdresser"), ("shop", "beauty")],
    "barber": [("shop", "hairdresser")],
    "beauty salon": [("shop", "beauty")],
    "spa": [("leisure", "spa"), ("shop", "beauty")],
    "restaurant": [("amenity", "restaurant")],
    "cafe": [("amenity", "cafe")],
    "bakery": [("shop", "bakery")],
    "real estate agent": [("office", "estate_agent")],
    "real estate": [("office", "estate_agent")],
    "plumber": [("craft", "plumber")],
    "electrician": [("craft", "electrician")],
    "hvac": [("craft", "hvac")],
    "roofer": [("craft", "roofer")],
    "gym": [("leisure", "fitness_centre")],
    "yoga studio": [("leisure", "fitness_centre"), ("sport", "yoga")],
    "clinic": [("amenity", "clinic"), ("amenity", "doctors")],
    "doctor": [("amenity", "doctors")],
    "physiotherapist": [("healthcare", "physiotherapist")],
    "lawyer": [("office", "lawyer")],
    "accountant": [("office", "accountant")],
    "hotel": [("tourism", "hotel")],
    "car repair": [("shop", "car_repair")],
    "car dealer": [("shop", "car")],
    "veterinary": [("amenity", "veterinary")],
    "vet": [("amenity", "veterinary")],
    "florist": [("shop", "florist")],
    "pharmacy": [("amenity", "pharmacy")],
    "photographer": [("craft", "photographer"), ("shop", "photo")],
    "furniture store": [("shop", "furniture")],
    "clothing store": [("shop", "clothes")],
    "jewelry store": [("shop", "jewelry")],
    "optician": [("shop", "optician")],
    "driving school": [("amenity", "driving_school")],
    # Indian small businesses
    "coaching centre": [("amenity", "prep_school"), ("amenity", "training")],
    "coaching": [("amenity", "prep_school"), ("amenity", "training")],
    "school": [("amenity", "school")],
    "beauty parlour": [("shop", "beauty")],
    "jewellery shop": [("shop", "jewelry")],
    "boutique": [("shop", "boutique"), ("shop", "fashion")],
    "interior designer": [("shop", "interior_decoration"), ("craft", "interior_decorator")],
    "chartered accountant": [("office", "accountant"), ("office", "tax_advisor")],
    "travel agency": [("shop", "travel_agency"), ("office", "travel_agent")],
    "event venue": [("amenity", "events_venue")],
    "banquet hall": [("amenity", "events_venue")],
    "sweet shop": [("shop", "confectionery"), ("shop", "pastry")],
    "guest house": [("tourism", "guest_house")],
    "electronics store": [("shop", "electronics")],
    "mobile phone shop": [("shop", "mobile_phone")],
}


# "Old website hunt" searches: every business in these categories that lists a website.
# Values are a regex of tag values, or None for any value of that key.
WEBSITE_GROUPS: Dict[str, List[tuple]] = {
    "websites: shops": [("shop", None)],
    "websites: offices": [("office", None)],
    "websites: hotels and food": [
        ("tourism", "hotel|guest_house|motel|hostel|resort"),
        ("amenity", "restaurant|cafe|fast_food|bar|pub|ice_cream|food_court"),
    ],
    "websites: schools and fitness": [
        ("amenity", "school|college|prep_school|training|driving_school|kindergarten|language_school|music_school"),
        ("leisure", "fitness_centre|sports_centre|dance|yoga"),
    ],
    "websites: health and services": [
        ("amenity", "clinic|doctors|dentist|veterinary|pharmacy|events_venue"),
        ("healthcare", None),
        ("craft", None),
    ],
}


def niche_from_tags(tags: Dict[str, str]) -> str:
    """Best niche name for a map element, e.g. shop=jewelry -> 'jewellery shop'."""
    indian_names = {"jewelry store": "jewellery shop", "clothing store": "clothing store", "accountant": "chartered accountant"}
    for niche, pairs in OSM_NICHE_TAGS.items():
        if any(tags.get(k) == v for k, v in pairs):
            return indian_names.get(niche, niche)
    for key in ("shop", "office", "amenity", "tourism", "leisure", "healthcare", "craft"):
        value = tags.get(key)
        if value and value not in ("yes",):
            value = value.replace("_", " ")
            return f"{value} shop" if key == "shop" and "shop" not in value else value
    return "business"


def osm_tags_for(niche: str) -> List[tuple]:
    key = niche.lower().strip()
    if key in OSM_NICHE_TAGS:
        return OSM_NICHE_TAGS[key]
    if key.endswith("s") and key[:-1] in OSM_NICHE_TAGS:
        return OSM_NICHE_TAGS[key[:-1]]
    for name, tags in OSM_NICHE_TAGS.items():
        if name in key or key in name:
            return tags
    return []


class OSMSource:
    name = "osm"
    NOMINATIM = "https://nominatim.openstreetmap.org/search"
    # Public Overpass servers are often at capacity; try them in order.
    OVERPASS_ENDPOINTS = [
        "https://overpass-api.de/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]
    MAX_RESULTS = 200
    MAX_WEBSITE_RESULTS = 400

    def __init__(self):
        self.session = requests.Session()
        # Both services block generic or browser User-Agents
        self.session.headers.update({"User-Agent": settings.OSM_USER_AGENT, "Accept": "application/json"})

    def is_configured(self) -> bool:
        return True

    AROUND_METERS = 15000  # radius used when a city is only a point (e.g. Mumbai)

    def location(self, city: str) -> tuple:
        """
        ("area", osm_area_id) when the city has a boundary, otherwise
        ("around", lat, lon) to search a radius around the city's centre point.
        """
        cached = ProspectRepository.get_cached_area(city)
        if cached:
            if cached.get("osm_area_id"):
                return ("area", int(cached["osm_area_id"]))
            if cached.get("lat") is not None and cached.get("lon") is not None:
                return ("around", float(cached["lat"]), float(cached["lon"]))
            # older failed lookups are retried below

        time.sleep(1.1)  # Nominatim policy: max 1 request per second
        resp = self.session.get(
            self.NOMINATIM,
            params={"q": city, "format": "jsonv2", "limit": 5},
            timeout=20.0,
        )
        if not resp.ok:
            raise SourceError(f"Nominatim {resp.status_code} for {city!r}")
        hits = resp.json()
        for hit in hits:
            if hit.get("osm_type") == "relation":
                area = 3600000000 + int(hit["osm_id"])
                ProspectRepository.cache_area(city, area, hit.get("display_name", ""))
                return ("area", area)
        for hit in hits:
            if hit.get("lat") and hit.get("lon"):
                lat, lon = float(hit["lat"]), float(hit["lon"])
                ProspectRepository.cache_area(city, None, hit.get("display_name", ""), lat, lon)
                return ("around", lat, lon)
        raise SourceError(f"OpenStreetMap does not know {city!r}; try a different spelling")

    def _scope(self, city: str) -> tuple:
        loc = self.location(city)
        if loc[0] == "area":
            return f"area({loc[1]})->.a;\n", "(area.a)"
        return "", f"(around:{self.AROUND_METERS},{loc[1]:.5f},{loc[2]:.5f})"

    def search(self, niche: str, city: str) -> List[Business]:
        if niche in WEBSITE_GROUPS:
            return self.search_websites(niche, city)
        tags = osm_tags_for(niche)
        if not tags:
            raise SourceError(
                f"No OpenStreetMap tag mapping for niche {niche!r}. "
                "Add it to OSM_NICHE_TAGS in prospector/sources.py or use Google Places."
            )
        prefix, scope = self._scope(city)
        selectors = "\n".join(f'  nwr["{k}"="{v}"]["name"]{scope};' for k, v in tags)
        query = (
            f"[out:json][timeout:60];\n{prefix}(\n{selectors}\n);\n"
            f"out tags center meta {self.MAX_RESULTS};"
        )
        return [b for b in (self._to_business(el, city) for el in self._overpass(query)) if b]

    def search_websites(self, group: str, city: str) -> List[Business]:
        """
        Only businesses that list a website, across a whole family of categories.
        Used to hunt for old websites: niche searches mostly return places without one.
        Chains (brand tags) are skipped; they are not small-business clients.
        """
        prefix, scope = self._scope(city)
        selectors = []
        for key, values in WEBSITE_GROUPS[group]:
            match = f'["{key}"~"^({values})$"]' if values else f'["{key}"]'
            if key == "office":
                # never government, embassies, tax offices or real estate
                match += '["office"!~"^(government|diplomatic|estate_agent|tax|politician|political_party|real_estate|ngo|religion)$"]'
            if key == "shop":
                match += '["shop"!="estate_agent"]'
            selectors.append(f'  nwr["website"]["name"]{match}{scope};')
        query = (
            f"[out:json][timeout:90];\n{prefix}(\n" + "\n".join(selectors) + "\n);\n"
            f"out tags center meta {self.MAX_WEBSITE_RESULTS};"
        )
        out = []
        for el in self._overpass(query):
            t = el.get("tags", {})
            if t.get("brand") or t.get("brand:wikidata") or t.get("operator:wikidata"):
                continue
            b = self._to_business(el, city)
            if b and b.website:
                b.niche = niche_from_tags(t)
                out.append(b)
        return out

    def _to_business(self, el: Dict[str, Any], city: str) -> Optional[Business]:
        t = el.get("tags", {})
        name = t.get("name")
        if not name or is_excluded(name, niche_from_tags(t), t):
            return None  # unnamed, or a government / public facility
        address = " ".join(
            x for x in [
                t.get("addr:housenumber", ""),
                t.get("addr:street", ""),
                t.get("addr:city", ""),
                t.get("addr:postcode", ""),
            ] if x
        )
        socials = [
            t[k] for k in ("contact:facebook", "facebook", "contact:instagram", "instagram") if t.get(k)
        ]
        return Business(
            source=self.name,
            place_id=f"{el.get('type')}/{el.get('id')}",
            name=name,
            address=address,
            phone=t.get("phone") or t.get("contact:phone") or "",
            email=t.get("email") or t.get("contact:email") or "",
            website=t.get("website") or t.get("contact:website") or t.get("url") or "",
            maps_url=google_maps_search_link(name, city),
            socials=socials,
            map_added_recently=_recently_added(el),
        )

    def _overpass(self, query: str) -> List[Dict[str, Any]]:
        try:
            return self._overpass_once(query)
        except SourceError:
            time.sleep(20)  # public servers are often busy for a few seconds; one more round
            return self._overpass_once(query)

    def _overpass_once(self, query: str) -> List[Dict[str, Any]]:
        errors = []
        for endpoint in self.OVERPASS_ENDPOINTS:
            host = urllib.parse.urlparse(endpoint).netloc
            try:
                resp = self.session.post(endpoint, data={"data": query}, timeout=75.0)
            except requests.exceptions.RequestException as e:
                errors.append(f"{host}: {type(e).__name__}")
                continue
            if resp.ok:
                try:
                    return resp.json().get("elements", [])
                except ValueError:
                    errors.append(f"{host}: invalid JSON")
                    continue
            errors.append(f"{host}: HTTP {resp.status_code}")
        raise SourceError("All Overpass servers are busy (" + "; ".join(errors) + "). Try again later.")


def pick_source(preference: Optional[str] = None):
    """auto -> Google Places when a key exists, otherwise OpenStreetMap."""
    choice = (preference or settings.PROSPECT_SOURCE or "auto").lower()
    if choice in ("google", "google_places", "places"):
        return GooglePlacesSource()
    if choice == "osm":
        return OSMSource()
    google = GooglePlacesSource()
    return google if google.is_configured() else OSMSource()
