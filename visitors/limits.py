"""Hourly limits that keep anyone from flooding the visit log.

The counters live in the Django cache (by default the memory of the process), so they start over
after a restart and are separate in every worker. The service runs a single worker, which is
enough to stop a flood.

The IP comes from the X-Forwarded-For header, which a sender can fake. That is why every kind of
event also has a total limit that does not depend on the address.
"""

from django.core.cache import cache

HOUR = 60 * 60


def _within(key, limit):
    """Count one more event under the key; False once there are more than `limit` in the hour."""
    if limit <= 0:  # 0 switches the limit off
        return True
    cache.add(key, 0, HOUR)
    try:
        return cache.incr(key) <= limit
    except ValueError:  # the counter expired between the two calls
        return True


def allow(kind, ip, per_ip, total):
    """True while both the limit of this address and the limit of all of them are not used up."""
    # In this order, so that an address over its own limit does not use up the total.
    return _within(f"visits:{kind}:ip:{ip}", per_ip) and _within(f"visits:{kind}:total", total)
