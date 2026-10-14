"""Odhad vzdálenosti nabídek podle textu lokality a souřadnic měst v ČR (bez externího API)."""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

# Okresní města a časté lokality v inzerátech (WGS84, přibližně centrum)
CZ_PLACES: dict[str, tuple[float, float]] = {
    "benesov": (49.7816, 14.6870),
    "beroun": (49.9638, 14.0720),
    "blansko": (49.3640, 16.6446),
    "brno": (49.1951, 16.6068),
    "bruntal": (49.9884, 17.4647),
    "breclav": (48.7531, 16.8825),
    "ceska lipa": (50.6855, 14.5377),
    "ceske budejovice": (48.9745, 14.4747),
    "cesky krumlov": (48.8106, 14.3150),
    "ceska trebova": (49.9044, 16.4440),
    "cheb": (50.0736, 12.3699),
    "chomutov": (50.4605, 13.4178),
    "chrudim": (49.9480, 15.7956),
    "decin": (50.7726, 14.2128),
    "domazlice": (49.4405, 12.9310),
    "frydek mistek": (49.6853, 18.3484),
    "havlickuv brod": (49.6078, 15.5808),
    "hodonin": (48.8489, 17.1324),
    "hradec kralove": (50.2104, 15.8252),
    "jablonec nad nisou": (50.7243, 15.1711),
    "jesenik": (50.2294, 17.2046),
    "jicin": (50.4372, 15.3516),
    "jihlava": (49.3961, 15.5912),
    "jindrichuv hradec": (49.1445, 15.0061),
    "karlovy vary": (50.2317, 12.8718),
    "karvina": (49.8540, 18.5417),
    "kladno": (50.1475, 14.1028),
    "klatovy": (49.3956, 13.2951),
    "kolin": (50.0274, 15.2008),
    "kromeriz": (49.2979, 17.3931),
    "kutna hora": (49.9494, 15.2682),
    "liberec": (50.7663, 15.0543),
    "litomerice": (50.5335, 14.1318),
    "louny": (50.3569, 13.7967),
    "mlada boleslav": (50.4114, 14.9032),
    "most": (50.5030, 13.6366),
    "nachod": (50.4166, 16.1626),
    "novy jicin": (49.5944, 18.0103),
    "nymburk": (50.1861, 15.0417),
    "olomouc": (49.5938, 17.2509),
    "opava": (49.9387, 17.9026),
    "ostrava": (49.8209, 18.2625),
    "pardubice": (50.0343, 15.7812),
    "pelhrimov": (49.4316, 15.2230),
    "pisek": (49.3088, 14.1475),
    "plzen": (49.7384, 13.3736),
    "prachatice": (49.0129, 14.0000),
    "praha": (50.0755, 14.4378),
    "prostejov": (49.4725, 17.1119),
    "rakovnik": (50.1043, 13.7397),
    "rokycany": (49.7428, 13.5946),
    "rychnov nad kneznou": (50.1629, 16.2749),
    "semily": (50.6052, 15.3288),
    "sokolov": (50.1813, 12.6401),
    "strakonice": (49.2614, 13.9024),
    "sumperk": (49.9653, 16.9706),
    "svitavy": (49.7559, 16.4683),
    "tabor": (49.4144, 14.6578),
    "tachov": (49.7957, 12.6366),
    "teplice": (50.6404, 13.8245),
    "trebic": (49.2149, 15.8797),
    "trutnov": (50.5611, 15.9128),
    "uherske hradiste": (49.0698, 17.4597),
    "usti nad labem": (50.6611, 14.0531),
    "usti nad orlici": (49.9725, 16.3936),
    "vsetin": (49.3386, 17.9962),
    "vyskov": (49.2775, 16.9990),
    "zlin": (49.2265, 17.6677),
    "znojmo": (48.8555, 16.0488),
    "zdar nad sazavou": (49.5643, 15.9390),
    # časté varianty / větší obce
    "cesky tesin": (49.7461, 18.6261),
    "havirov": (49.7798, 18.4368),
    "pribram": (49.6899, 14.0104),
    "prerov": (49.4551, 17.4509),
    "zlin": (49.2265, 17.6677),
}

REMOTE_MARKERS = (
    "remote",
    "home office",
    "homeoffice",
    "na dálku",
    "na dalku",
    "práce z domova",
    "prace z domova",
    "hybrid",
    "celá čr",
    "cela cr",
    "celorepublikov",
)

_PLACE_BY_LEN = sorted(CZ_PLACES.keys(), key=len, reverse=True)


def normalize_place(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = folded.lower()
    folded = re.sub(r"[^a-z0-9\s]", " ", folded)
    return re.sub(r"\s+", " ", folded).strip()


def lookup_city(city: str) -> tuple[str, float, float] | None:
    key = normalize_place(city)
    if not key:
        return None
    if key in CZ_PLACES:
        lat, lon = CZ_PLACES[key]
        return city.strip(), lat, lon
    # „Praha 5“, „Brno-střed“
    for part in key.split():
        if part in CZ_PLACES:
            lat, lon = CZ_PLACES[part]
            return city.strip(), lat, lon
    for place in _PLACE_BY_LEN:
        if place in key or key in place:
            lat, lon = CZ_PLACES[place]
            return city.strip(), lat, lon
    return None


def search_places(query: str, limit: int = 15) -> list[str]:
    q = normalize_place(query)
    if not q:
        return []
    hits: list[str] = []
    for place in sorted(CZ_PLACES):
        if q in place:
            label = place.title().replace(" ", " ")
            # jednoduché zobrazení s diakritikou u známých měst
            display = _DISPLAY.get(place, label)
            if display not in hits:
                hits.append(display)
            if len(hits) >= limit:
                break
    return hits


_DISPLAY = {
    "ceske budejovice": "České Budějovice",
    "cesky krumlov": "Český Krumlov",
    "jindrichuv hradec": "Jindřichův Hradec",
    "hradec kralove": "Hradec Králové",
    "usti nad labem": "Ústí nad Labem",
    "strakonice": "Strakonice",
    "tabor": "Tábor",
    "pisek": "Písek",
    "praha": "Praha",
    "plzen": "Plzeň",
    "brno": "Brno",
    "ostrava": "Ostrava",
}


def is_remote_location(text: str) -> bool:
    low = normalize_place(text)
    return any(m in low for m in REMOTE_MARKERS)


def resolve_coordinates(location_text: str) -> tuple[float, float] | None:
    if not location_text or is_remote_location(location_text):
        return None
    norm = normalize_place(location_text)
    for place in _PLACE_BY_LEN:
        if place in norm:
            return CZ_PLACES[place]
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


@dataclass
class JobDistance:
    distance_km: float | None
    remote: bool
    unknown: bool


def job_distance(home: dict[str, Any], location: str, raw_text: str = "") -> JobDistance:
    combined = f"{location}\n{raw_text[:800]}"
    if is_remote_location(combined):
        return JobDistance(distance_km=None, remote=True, unknown=False)
    coords = resolve_coordinates(location) or resolve_coordinates(raw_text[:800])
    if not coords:
        return JobDistance(distance_km=None, remote=False, unknown=True)
    try:
        lat = float(home["lat"])
        lon = float(home["lon"])
    except (KeyError, TypeError, ValueError):
        return JobDistance(distance_km=None, remote=False, unknown=True)
    km = haversine_km(lat, lon, coords[0], coords[1])
    return JobDistance(distance_km=round(km, 1), remote=False, unknown=False)


def enrich_location_preferences(preferences: dict[str, Any]) -> dict[str, Any]:
    """Doplní preferences.home z home_city; při neznámém městě vyhodí ValueError."""
    prefs = dict(preferences or {})
    city_raw = (prefs.get("home_city") or "").strip()
    if not city_raw:
        prefs.pop("home", None)
        return prefs
    resolved = lookup_city(city_raw)
    if not resolved:
        raise ValueError(
            f"Neznámé město „{city_raw}“. Zadejte okresní město (např. Strakonice, České Budějovice)."
        )
    label, lat, lon = resolved
    prefs["home"] = {"city": label, "lat": lat, "lon": lon}
    max_km = prefs.get("max_distance_km")
    if max_km in ("", None):
        prefs["max_distance_km"] = None
    elif max_km is not None:
        try:
            prefs["max_distance_km"] = max(1, min(500, int(max_km)))
        except (TypeError, ValueError):
            raise ValueError("max_distance_km musí být celé číslo 1–500 km.")
    return prefs
