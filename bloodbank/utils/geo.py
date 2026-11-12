"""Geo utilities: distance calculation and location resolution."""
import math

# Known city centers (fallback geocoding without external API calls)
CITY_COORDS = {
    "Visakhapatnam": (17.6868, 83.2185),
    "Vijayawada": (16.5062, 80.6480),
    "Guntur": (16.3067, 80.4365),
    "Nellore": (14.4426, 79.9865),
    "Kurnool": (15.8281, 78.0373),
    "Kadapa": (14.4673, 78.8242),
    "Rajahmundry": (17.0005, 81.8040),
    "Kakinada": (16.9891, 82.2475),
    "Tirupati": (13.6288, 79.4192),
}


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in kilometers."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def geocode_address(address, api_enabled=True):
    """
    Try to resolve a free-text address to (lat, lon) using geopy/Nominatim if
    available and network access is permitted. Falls back to None on failure.
    """
    if not api_enabled:
        return None
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="blood_bank_availability_agent", timeout=5)
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
    except Exception:
        return None
    return None


def resolve_location(city=None, address=None, coords=None):
    """
    Resolve a user's location to (lat, lon) with best available method:
    1. explicit coords (e.g. from browser geolocation)
    2. free-text address geocoded via Nominatim
    3. known city center lookup
    Returns (lat, lon, source_label) or (None, None, None).
    """
    if coords:
        return coords[0], coords[1], "device location"

    if address:
        result = geocode_address(address)
        if result:
            return result[0], result[1], "geocoded address"

    if city and city in CITY_COORDS:
        lat, lon = CITY_COORDS[city]
        return lat, lon, f"{city} city center"

    return None, None, None


def reverse_geocode(lat, lon):
    """
    Best-effort reverse geocode of (lat, lon) into a human-readable address
    using Nominatim. Returns None if unavailable (no network, rate limited,
    etc.) — callers should fall back to showing raw coordinates.
    """
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="blood_bank_availability_agent", timeout=5)
        location = geolocator.reverse((lat, lon), exactly_one=True)
        if location:
            return location.address
    except Exception:
        return None
    return None


def estimate_travel_time_minutes(distance_km, mode="ambulance"):
    """Rough ETA estimate based on distance and transport mode."""
    speeds_kmph = {"ambulance": 45, "hospital_vehicle": 35, "public": 25}
    speed = speeds_kmph.get(mode, 35)
    return round((distance_km / speed) * 60, 1)
