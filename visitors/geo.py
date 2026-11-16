"""Approximate location of an IP address from the offline MaxMind GeoLite2-City database.

Only the city level is available (an IP does not reveal a street, and the point is often several
kilometres off). When the database file is missing or the address is not found, the location is
simply empty: logging a visit never fails because of geolocation.
"""

import logging
from functools import lru_cache

import geoip2.database
import geoip2.errors
from django.conf import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _reader():
    path = settings.GEOIP_DB_PATH
    try:
        return geoip2.database.Reader(str(path))
    except (OSError, ValueError):
        logger.warning("GeoIP database not found at %s, locations will be empty", path)
        return None


def reset_reader():
    """Forget the opened database (after it was downloaded again, and in tests)."""
    reader = _reader()
    if reader:
        reader.close()
    _reader.cache_clear()


def locate(ip):
    """Return a dict of Visit location fields for the address, empty when unknown."""
    reader = _reader()
    if reader is None or not ip:
        return {}
    try:
        city = reader.city(ip)
    except (geoip2.errors.AddressNotFoundError, ValueError):
        return {}
    region = city.subdivisions.most_specific
    return {
        "country": city.country.names.get("uk") or city.country.name or "",
        "country_code": city.country.iso_code or "",
        "region": region.names.get("uk") or region.name or "",
        "city": city.city.names.get("uk") or city.city.name or "",
        "latitude": city.location.latitude,
        "longitude": city.location.longitude,
    }
