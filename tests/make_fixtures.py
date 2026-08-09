"""(Re)download the test fixtures.

The fixtures are full MM article pages, so they are gitignored rather than published
in this public repo. Run this once on a fresh checkout before the tests:

    python3 tests/make_fixtures.py && python3 -m unittest discover -s tests

If either URL 404s (articles do get retired), swap in any current article for FREE and
any MM+ article for GATED, then re-run the tests.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import build_opener, http_get  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

PAGES = {
    "free_article.html": (
        "https://www.mannheimer-morgen.de/politik_artikel,"
        "-niedrigwasser-gruene-und-linke-kritisieren-bundesregierung-_arid,2392466.html"
    ),
    "gated_article.html": (
        "https://www.mannheimer-morgen.de/orte/walldorf_artikel,"
        "-walldorf-ohne-schulterschluss-keine-strassenbahnlinie-24-nach-walldorf-"
        "_arid,2392465.html"
    ),
}

if __name__ == "__main__":
    os.makedirs(FIX, exist_ok=True)
    opener = build_opener()
    for name, url in PAGES.items():
        html = http_get(url, opener)
        with open(os.path.join(FIX, name), "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"{name}: {len(html)} chars")
