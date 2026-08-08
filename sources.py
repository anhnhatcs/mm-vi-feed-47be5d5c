"""The Mannheimer Morgen feeds we pull. Every URL verified HTTP 200, 2026-08-09.

Deliberately NOT included: feed 146 ("Das Wichtigste") -- it looks like the obvious
front-page feed but is stale, newest item was 6 days old when checked.
"""

BASE = "https://www.mannheimer-morgen.de/feed/"

FEEDS = [
    # (url slug, display name)
    ("60-rss.xml", "Metropolregion Mannheim"),
    ("61-rss.xml", "Region Rhein-Neckar"),
    ("62-rss.xml", "Region Bergstraße"),
    ("67-rss.xml", "Newsticker Rhein-Neckar"),
    ("55-politik-rss-feed.xml", "Politik"),
    ("56-wirtschaft-rss-feed.xml", "Wirtschaft"),
]

SOURCES = [(BASE + slug, name) for slug, name in FEEDS]

# Tuning knobs, kept in one place.
MAX_ARTICLES_PER_RUN = 40      # politeness cap on article-page fetches
FETCH_DELAY_SECONDS = 2.0      # between article-page fetches
SEED_WINDOW_HOURS = 48         # first run only translates the last N hours
FEED_ITEM_LIMIT = 80           # items kept in the published feed
TRANSLATE_BATCH = 3            # full articles per claude -p call
