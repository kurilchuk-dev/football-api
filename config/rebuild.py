"""Asks the hosting of the site to build it again after the data changed.

The site's pages are made at build time (so search engines can read them), so they need a new
build to show new scores. Visitors do not wait for it: the site also asks the API itself.

SITE_DEPLOY_HOOK_URL is a Cloudflare Pages "deploy hook". It is a secret: anyone who has it can
start builds. Without it nothing happens.
"""

import logging
import threading

import requests
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save

logger = logging.getLogger(__name__)

# The models whose data is written into the pages.
MODELS = ("matches.Match", "teams.Team", "players.Player")

_lock = threading.Lock()
_timer = None


def _call_hook():
    try:
        requests.post(settings.SITE_DEPLOY_HOOK_URL, timeout=30).raise_for_status()
    except requests.RequestException as error:
        # Not the exception itself: its text contains the secret address.
        logger.warning("Could not ask for a new build of the site: %s", type(error).__name__)


def _start_timer():
    """Waits for the edits to stop, so a whole round of scores gives one build, not twelve."""
    global _timer
    with _lock:
        if _timer is not None:
            _timer.cancel()
        _timer = threading.Timer(settings.SITE_DEPLOY_DELAY_SECONDS, _call_hook)
        _timer.daemon = True
        _timer.start()


def schedule_rebuild(**kwargs):
    if settings.SITE_DEPLOY_HOOK_URL:
        transaction.on_commit(_start_timer)


def connect():
    for model in MODELS:
        for signal in (post_save, post_delete):
            signal.connect(schedule_rebuild, sender=model, dispatch_uid=f"rebuild:{model}")
