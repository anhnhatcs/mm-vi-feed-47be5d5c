"""One daily run: fetch -> pick new -> article bodies -> translate -> store -> build."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone

import build
import store
from article import fetch_many
from common import cookies_available, log
from fetch import fetch_all
from sources import MAX_ARTICLES_PER_RUN, SEED_WINDOW_HOURS
from translate import translate_all


def main(limit: int | None = None, dry_run: bool = False) -> int:
    con = store.connect()
    known = store.known_guids(con)
    first_run = not known
    log(f"state: {len(known)} items known" + (" (first run)" if first_run else ""))

    items = [i for i in fetch_all() if i["guid"] not in known]

    if first_run:
        # Don't translate months of backlog on day one.
        cutoff = datetime.now(timezone.utc) - timedelta(hours=SEED_WINDOW_HOURS)
        items = [i for i in items if i["pubdate"] and i["pubdate"] > cutoff]
        log(f"first run: seeding last {SEED_WINDOW_HOURS}h only -> {len(items)} items")

    cap = limit or MAX_ARTICLES_PER_RUN
    if len(items) > cap:
        log(f"capping {len(items)} new items to {cap}")
        items = items[:cap]

    if not items:
        log("nothing new")
        build.build()
        return 0

    have_cookies = cookies_available()
    log(f"fetching {len(items)} article bodies (cookies: {'yes' if have_cookies else 'no'})")
    full, gated = fetch_many(items)
    log(f"bodies: {full} full, {gated} gated")

    if dry_run:
        log("dry run -- stopping before translation")
        return 0

    translate_all(items)
    for item in items:
        store.insert_translated(con, item)
    log(f"stored {len(items)} translated items")

    json.dump({"full": full, "gated": gated, "cookies_present": have_cookies,
               "when": datetime.now(timezone.utc).isoformat()},
              open(build.STATUS_PATH, "w"))
    build.build()
    return len(items)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    main(limit=a.limit, dry_run=a.dry_run)
