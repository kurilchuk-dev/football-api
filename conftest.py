import pytest


@pytest.fixture(autouse=True)
def _no_visit_log(settings):
    """The visitor log writes a row per request; the other tests count queries, so it is off.

    The tests of the log itself switch it back on (see visitors/tests.py).
    """
    settings.VISIT_LOG_ENABLED = False
