# Mannheimer Morgen → Tiếng Việt

Daily job on the netcup VPS: pull the Mannheimer Morgen RSS feeds, fetch each article,
translate it to Vietnamese with the headless Claude CLI, and publish a Vietnamese RSS
feed to GitHub Pages for Feedly.

**Feed URL (subscribe to this in Feedly):**
`https://anhnhatcs.github.io/mm-vi-feed-47be5d5c/feed.xml`

The repo is public but unlisted, and `docs/robots.txt` blocks search engines.

## How it runs

```
cron 07:00 Europe/Berlin
  └─ run.sh                flock, logs to logs/run.log
       └─ pipeline.py
            ├─ fetch.py     6 MM feeds → items       (sources.py)
            ├─ store.py     sqlite state.db, skip anything already done
            ├─ article.py   article page → German body
            ├─ translate.py claude -p, 3 articles per call
            └─ build.py     → docs/feed.xml
       └─ publish.sh        git commit + push (no-op if unchanged)
```

Everything is Python **standard library only** — there is no pip on this VPS and
nothing to install.

## MM+ cookies (optional, unlocks the paywalled articles)

Without cookies the job still works: roughly **87%** of items are free agency articles
and come through in full; MM+ items fall back to their teaser and are labelled in the
feed. To get the remaining ~13% in full:

1. Log in to mannheimer-morgen.de in your browser as MM+.
2. Export that domain's cookies in **Netscape format** (e.g. the "Get cookies.txt
   LOCALLY" extension).
3. Save on the VPS as `~/.config/mm-vi-feed/cookies.txt`, then `chmod 600` it.

Verify they actually took effect — this compares the same article with and without
the session:

```bash
python3 article.py --compare --url "<a gated MM+ article URL>"
# anonymous   : 0 chars  <- gated
# with cookies: 3xxx chars
```

When the session later expires, the job does not fail silently: the feed grows a
pinned item **"⚠️ MM cookie hết hạn"**, so the reminder reaches you in Feedly.

## Operating it

```bash
python3 fetch.py --dry-run              # feeds reachable? item counts
python3 pipeline.py --limit 5           # small real run
python3 pipeline.py --dry-run           # fetch bodies, skip translation
./run.sh                                # exactly what cron runs
python3 tests/make_fixtures.py          # fixtures are gitignored; fetch them once
python3 -m unittest discover -s tests   # extraction tests (fixture-pinned)
tail -f logs/run.log
```

Tuning lives in `sources.py`: which feeds, articles per run, batch size, feed length.
To add a source, append its `(slug, name)` to `FEEDS` — the URL pattern is
`https://www.mannheimer-morgen.de/feed/<slug>`.

## Notes for whoever touches this next

- **Always send a browser User-Agent.** With the default urllib agent, MM's sister
  domains return a 1.4 KB stub and it looks like bot-blocking. It isn't.
- **Feed 146 ("Das Wichtigste") looks like the right front-page feed but is stale** —
  its newest item was 6 days old. The topic and regional feeds are the live ones.
- **`Artikel freischalten` is not a paywall marker.** It is on every page as a share
  widget; keying the gate off it reports 100% paywalled. The real signal is the
  absence of `div.article-body-default__content`, plus `paywall__textblur`.
- **Slice that container by div depth**, not with a regex that stops at the first
  `</div>` — the body has nested divs.
- **Never fall back to sweeping every `<p>` on the page**: the related-articles list
  (`list-greatfurtherread__contents`) then leaks headlines and URLs into the body.
- **The Claude CLI needs a clean environment.** Inherited `CLAUDE_CODE_*` session
  variables make a nested run fail with `Not logged in`; `translate.py` therefore
  calls it with an explicit minimal `env`. Cron provides that naturally.
