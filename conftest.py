import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _no_site_rebuild(settings):
    """A deploy hook set in a local .env must never be called by the tests."""
    settings.SITE_DEPLOY_HOOK_URL = ""


@pytest.fixture(autouse=True)
def _fresh_cache():
    """The flood limits of the visitor log count in the cache; every test starts from zero."""
    cache.clear()


@pytest.fixture(autouse=True)
def _no_visit_log(settings):
    """The visitor log writes a row per request; the other tests count queries, so it is off.

    The tests of the log itself switch it back on (see visitors/tests.py).
    """
    settings.VISIT_LOG_ENABLED = False
