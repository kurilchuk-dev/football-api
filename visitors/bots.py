"""Telling robots from people by the User-Agent header.

It is a best effort: honest robots (search engines, link previews, monitors, scripts) name
themselves, so they are filtered out of the statistics. A robot that pretends to be a browser
cannot be told apart this way.
"""

# Case-insensitive; one word is enough. A browser never has any of these in its User-Agent.
BOT_PATTERN = (
    r"bot|crawl|spider|slurp|monitor|uptime|headless|preview|facebookexternalhit|whatsapp"
    r"|curl|wget|python-|httpx|axios|go-http-client|okhttp|java/|scrapy|lighthouse|pingdom"
    r"|statuscake|gtmetrix|semrush|ahrefs|mj12|yandex|baidu|duckduck|applebot|embedly|vkshare"
)


def human_visits(queryset):
    """The visits whose User-Agent does not look like a robot."""
    return queryset.exclude(user_agent__iregex=BOT_PATTERN)


def bot_visits(queryset):
    """The visits whose User-Agent looks like a robot."""
    return queryset.filter(user_agent__iregex=BOT_PATTERN)
