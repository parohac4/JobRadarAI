from app.services.geo import enrich_location_preferences, haversine_km, job_distance, lookup_city, resolve_coordinates


def test_lookup_strakonice():
    hit = lookup_city("Strakonice")
    assert hit is not None
    assert abs(hit[1] - 49.26) < 0.1


def test_resolve_location_in_string():
    coords = resolve_coordinates("Strakonice, Jihočeský kraj")
    assert coords is not None


def test_haversine_strakonice_to_budejovice():
    s = lookup_city("Strakonice")
    b = lookup_city("České Budějovice")
    assert s and b
    km = haversine_km(s[1], s[2], b[1], b[2])
    assert 40 < km < 70


def test_job_distance_remote():
    home = {"lat": 49.26, "lon": 13.90}
    info = job_distance(home, "Remote / home office")
    assert info.remote
    assert info.distance_km is None


def test_enrich_preferences_home_city():
    prefs = enrich_location_preferences({"home_city": "Tábor", "regions": ["Jihočeský kraj"]})
    assert prefs["home"]["city"]
    assert prefs["home"]["lat"]
