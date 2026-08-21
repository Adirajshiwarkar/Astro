import json
import logging
import urllib.parse
import urllib.request
from typing import Tuple, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger("app.services.geocoder")

# Global location coordinate and timezone cache for fast lookup
COMMON_CITIES = {
    "mumbai": (19.0760, 72.8777, "Asia/Kolkata"),
    "delhi": (28.6139, 77.2090, "Asia/Kolkata"),
    "new delhi": (28.6139, 77.2090, "Asia/Kolkata"),
    "bangalore": (12.9716, 77.5946, "Asia/Kolkata"),
    "bengaluru": (12.9716, 77.5946, "Asia/Kolkata"),
    "hyderabad": (17.3850, 78.4867, "Asia/Kolkata"),
    "chennai": (13.0827, 80.2707, "Asia/Kolkata"),
    "kolkata": (22.5726, 88.3639, "Asia/Kolkata"),
    "pune": (18.5204, 73.8567, "Asia/Kolkata"),
    "ahmedabad": (23.0225, 72.5714, "Asia/Kolkata"),
    "jaipur": (26.9124, 75.7873, "Asia/Kolkata"),
    "indore": (22.7196, 75.8577, "Asia/Kolkata"),
    "bhopal": (23.2599, 77.4126, "Asia/Kolkata"),
    "surat": (21.1702, 72.8311, "Asia/Kolkata"),
    "lucknow": (26.8467, 80.9462, "Asia/Kolkata"),
    "nagpur": (21.1458, 79.0882, "Asia/Kolkata"),
    "patna": (25.5941, 85.1376, "Asia/Kolkata"),
    "new york": (40.7128, -74.0060, "America/New_York"),
    "london": (51.5074, -0.1278, "Europe/London"),
    "paris": (48.8566, 2.3522, "Europe/Paris"),
    "tokyo": (35.6762, 139.6503, "Asia/Tokyo"),
    "sydney": (-33.8688, 151.2093, "Australia/Sydney"),
    "los angeles": (34.0522, -118.2437, "America/Los_Angeles"),
    "chicago": (41.8781, -87.6298, "America/Chicago"),
    "san francisco": (37.7749, -122.4194, "America/Los_Angeles"),
    "toronto": (43.6532, -79.3832, "America/Toronto"),
    "dubai": (25.2048, 55.2708, "Asia/Dubai"),
    "singapore": (1.3521, 103.8198, "Asia/Singapore"),
}


def geocode_location(location_name: str) -> Tuple[Optional[float], Optional[float]]:
    """Convert location string to (latitude, longitude) based on user input place."""
    if not location_name:
        return None, None

    clean_name = location_name.strip().lower()

    # 1. Match against known common locations
    for city, data in COMMON_CITIES.items():
        if city in clean_name:
            logger.info(
                f"[GEOCODER] Geocoded location '{location_name}' to lat={data[0]}, lon={data[1]}"
            )
            return data[0], data[1]

    # 2. Try Nominatim Geocoding service for dynamic lookup
    try:
        encoded_query = urllib.parse.quote(location_name)
        url = f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&limit=1"
        req = urllib.request.Request(url, headers={"User-Agent": "AstroAPI/1.0"})
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    logger.info(
                        f"[GEOCODER] Dynamically resolved location '{location_name}' to lat={lat}, lon={lon}"
                    )
                    return lat, lon
    except Exception as e:
        logger.warning(
            f"[GEOCODER] Online geocoding attempt for '{location_name}' failed: {e}"
        )

    return None, None


def resolve_timezone_name(tz_input: str) -> str:
    """Normalize and resolve arbitrary timezone inputs or city strings to valid IANA timezone names."""
    if not tz_input:
        return "Asia/Kolkata"

    clean_tz = tz_input.strip()

    # 1. Check if it's already a valid IANA timezone name
    try:
        ZoneInfo(clean_tz)
        return clean_tz
    except ZoneInfoNotFoundError:
        pass

    # 2. Check if a known city is contained in the string (e.g. "Indore ,India")
    lower_tz = clean_tz.lower()
    for city, data in COMMON_CITIES.items():
        if city in lower_tz:
            logger.info(
                f"[TIMEZONE RESOLVER] Mapped city input '{tz_input}' -> '{data[2]}'"
            )
            return data[2]

    # 3. Check for regional keywords
    if any(kw in lower_tz for kw in ["india", "bharat", "ist", "indore"]):
        logger.info(f"[TIMEZONE RESOLVER] Mapped Indian region input '{tz_input}' -> 'Asia/Kolkata'")
        return "Asia/Kolkata"

    # Default fallback timezone
    logger.warning(
        f"[TIMEZONE RESOLVER] Could not match timezone '{tz_input}', defaulting to 'Asia/Kolkata'"
    )
    return "Asia/Kolkata"
