"""Geocoding and distance filtering centered on Ghent, Belgium."""

import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.settings import GHENT_LAT, GHENT_LON, SEARCH_RADIUS_KM

try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    _GEOPY_AVAILABLE = True
except ImportError:
    _GEOPY_AVAILABLE = False

# Module-level cache so we don't re-geocode the same string in one run
_geocache: dict[str, tuple[float, float] | None] = {}

_geolocator = (
    Nominatim(user_agent="job-engine-search/1.0", timeout=5)
    if _GEOPY_AVAILABLE
    else None
)

# Keywords that mean "remote / flexible location" → always include
_REMOTE_KEYWORDS = {"remote", "anywhere", "worldwide", "global", "home office"}

# Generic country/region names → include but can't compute distance
_VAGUE_LOCATIONS = {"belgium", "belgique", "belgië", "europe", "eu"}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def geocode_location(location_str: str) -> tuple[float, float] | None:
    """Return (lat, lon) for a location string, or None on failure."""
    if not location_str:
        return None

    key = location_str.strip().lower()

    if key in _geocache:
        return _geocache[key]

    if not _GEOPY_AVAILABLE or _geolocator is None:
        _geocache[key] = None
        return None

    try:
        time.sleep(1)  # Nominatim rate limit: 1 req/s
        result = _geolocator.geocode(location_str)
        if result:
            coords = (result.latitude, result.longitude)
            _geocache[key] = coords
            return coords
    except (GeocoderTimedOut, GeocoderServiceError):
        pass

    _geocache[key] = None
    return None


def is_within_radius(
    location_str: str,
) -> tuple[bool, float | None, float | None, float | None]:
    """
    Returns (within, lat, lon, dist_km).

    - Remote/blank → (True, None, None, None)
    - Vague (e.g. "Belgium") → (True, None, None, None)
    - Geocode failure → (True, None, None, None)  [include for manual review]
    - Otherwise → computed from Haversine
    """
    if not location_str:
        return True, None, None, None

    lower = location_str.strip().lower()

    if any(kw in lower for kw in _REMOTE_KEYWORDS):
        return True, None, None, None

    if lower in _VAGUE_LOCATIONS:
        return True, None, None, None

    coords = geocode_location(location_str)
    if coords is None:
        # Geocode failed — include with NULL distance for manual review
        return True, None, None, None

    lat, lon = coords
    dist = _haversine(GHENT_LAT, GHENT_LON, lat, lon)
    within = dist <= SEARCH_RADIUS_KM
    return within, lat, lon, round(dist, 1)


if __name__ == "__main__":
    tests = [
        ("Ghent, Belgium", True),
        ("Antwerp, Belgium", True),   # ~55 km
        ("Brussels, Belgium", True),  # ~55 km
        ("Eindhoven, Netherlands", False),  # ~145 km
        ("Remote", True),
        ("Belgium", True),
        ("", True),
    ]
    for loc, expected in tests:
        within, lat, lon, dist = is_within_radius(loc)
        status = "OK" if within == expected else "FAIL"
        print(f"[{status}] {loc!r:30s} -> within={within}, dist={dist} km")
