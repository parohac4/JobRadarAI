"""Offline Czech populated places, GeoNames CC BY 4.0 (see data/README.md)."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from app.services.geo import haversine_km, normalize_place

ROWS = json.loads((Path(__file__).parents[1] / "data/cz_places.json").read_text())
COUNTS = Counter(normalize_place(r[0]) for r in ROWS)
PLACES = []
BY_NAME = defaultdict(list)
for name, lat, lon, population, region, district in ROWS:
    label = name if COUNTS[normalize_place(name)] == 1 else f"{name} ({lat:.5f}, {lon:.5f})"
    place = {"label": label, "name": name, "lat": lat, "lon": lon, "population": population, "region": region}
    PLACES.append(place)
    BY_NAME[normalize_place(name)].append(place)
BY_LABEL = {p["label"].casefold(): p for p in PLACES}


def suggestions(query: str) -> list[dict]:
    q = normalize_place(query)
    if not q:
        return []
    hits = [p for p in PLACES if q in normalize_place(p["name"])]
    hits.sort(key=lambda p: (not normalize_place(p["name"]).startswith(q), -p["population"], p["label"]))
    return hits[:20]


def resolve_place(label: str) -> dict | None:
    if label.casefold() in BY_LABEL:
        return BY_LABEL[label.casefold()]
    hits = BY_NAME.get(normalize_place(label), [])
    if len(hits) == 1:
        return hits[0]
    ranked = sorted(hits, key=lambda p: -p["population"])
    if ranked and ranked[0]["population"] > max(1000, ranked[1]["population"] * 10):
        return ranked[0]
    return None


def location_distance(home: dict, location: str) -> tuple[float | None, bool]:
    # Hybrid requires commuting; only explicit full remote bypasses the radius.
    norm = normalize_place(location)
    remote = any(x in norm for x in ("fully remote", "full remote", "100 remote", "prace z domova", "na dalku", "cela cr", "cesko"))
    if norm == "remote":
        remote = True
    words = norm.split()
    matches = []
    for length in range(min(7, len(words)), 0, -1):
        for start in range(len(words) - length + 1):
            phrase = " ".join(words[start:start + length])
            if phrase not in BY_NAME:
                continue
            p = resolve_place(phrase)
            if p:
                matches.append(p)
        if matches:
            break
    if not matches:
        return None, remote
    return round(min(haversine_km(home["lat"], home["lon"], p["lat"], p["lon"]) for p in matches), 1), False


def nearby_places(home: dict, radius: int) -> list[dict]:
    towns = [p for p in PLACES if p["population"] >= 5000 and haversine_km(home["lat"], home["lon"], p["lat"], p["lon"]) <= radius]
    towns.sort(key=lambda p: -p["population"])
    result = {home["label"]: home}
    for place in towns:
        result.setdefault(place["label"], place)
    return list(result.values())[:5]


def nearby_centres(home: dict, radius: int) -> list[str]:
    return [p["name"] for p in nearby_places(home, radius)]


def slug(city: str) -> str:
    return re.sub(r"\s+", "-", normalize_place(city))
