"""Fetch the German article body, using the MM+ cookie session when available.

Markup facts established by inspecting live pages (2026-08-09):

* A readable article puts its text in `<div class="article-body-default__content">`.
  Nested divs live inside it, so the container must be sliced by tracking div depth --
  a regex stopping at the first `</div>` silently returns nothing.
* An MM+ gated article does NOT contain that container at all. It carries
  `paywall__textblur` / `paywall-default__login` instead. That absence is the gate
  signal, and it is reliable.
* `Artikel freischalten` is NOT a gate marker -- it appears on every page as a share
  widget. Detecting the wall by that string reports 100% paywalled and is wrong.
* Do not sweep all <p> tags as a fallback: `list-greatfurtherread__contents`
  (related articles) then leaks headline+URL noise into the body.
"""
from __future__ import annotations

import argparse
import json
import re
import time

from common import build_opener, cookies_available, http_get, log, strip_html
from sources import FETCH_DELAY_SECONDS

BODY_CLASS = "article-body-default__content"
GATE = re.compile(r"paywall__textblur|paywall-default__login", re.I)
MIN_BODY_CHARS = 120
CREDIT = re.compile(r"^\s*©|^\s*dpa[-:]|^\s*Redaktion\s*$", re.I)


class Paywalled(Exception):
    """No readable body: MM+ gate, or the session is logged out/expired."""


def slice_container(html_text: str, cls: str = BODY_CLASS) -> str | None:
    """Return the inner HTML of the first div carrying `cls`, depth-aware."""
    m = re.search(r'<div[^>]*class=["\'][^"\']*' + re.escape(cls) + r'[^"\']*["\'][^>]*>',
                  html_text)
    if not m:
        return None
    start, depth = m.end(), 1
    for tag in re.finditer(r"<(/?)div\b[^>]*>", html_text[start:]):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return html_text[start:start + tag.start()]
    return html_text[start:]


def _paragraphs(fragment: str) -> str:
    out = []
    for p in re.findall(r"<p[^>]*>(.*?)</p>", fragment, re.S | re.I):
        text = strip_html(p)
        if text and not CREDIT.match(text):
            out.append(text)
    return "\n\n".join(out)


def _from_jsonld(html_text: str) -> str:
    for m in re.finditer(
        r'<script[^>]*type=["\']?application/ld\+json["\']?[^>]*>(.*?)</script>',
        html_text, re.S | re.I,
    ):
        try:
            data = json.loads(m.group(1).strip())
        except Exception:
            continue
        for obj in data if isinstance(data, list) else [data]:
            if isinstance(obj, dict) and obj.get("articleBody"):
                return strip_html(obj["articleBody"])
    return ""


def extract_body(html_text: str) -> str:
    """Body text, or "" when the page is gated."""
    body = _from_jsonld(html_text)
    if len(body) >= MIN_BODY_CHARS:
        return body
    fragment = slice_container(html_text)
    if fragment:
        body = _paragraphs(fragment)
        if len(body) >= MIN_BODY_CHARS:
            return body
    return ""


def is_gated(html_text: str) -> bool:
    return slice_container(html_text) is None and bool(GATE.search(html_text))


def fetch_article(url: str, opener=None) -> str:
    opener = opener or build_opener(use_cookies=cookies_available())
    html_text = http_get(url, opener)
    body = extract_body(html_text)
    if not body:
        raise Paywalled("MM+ gate" if is_gated(html_text) else "no body container")
    return body


def fetch_many(items: list[dict], opener=None) -> tuple[int, int]:
    """Attach `body_de` in place. Returns (full, gated)."""
    opener = opener or build_opener(use_cookies=cookies_available())
    full = gated = 0
    for i, item in enumerate(items):
        if i:
            time.sleep(FETCH_DELAY_SECONDS)
        try:
            item["body_de"] = fetch_article(item["link"], opener)
            full += 1
        except Paywalled as e:
            item["body_de"] = ""
            gated += 1
            log(f"  gated ({e}): {item['title_de'][:55]}")
        except Exception as e:
            item["body_de"] = ""
            log(f"  WARN fetch failed ({type(e).__name__}): {item['link']}")
    return full, gated


def _compare(url: str) -> None:
    """Anonymous vs cookie session on the same URL -- proves the cookies work."""
    for label, use in (("anonymous", False), ("with cookies", True)):
        if use and not cookies_available():
            log("with cookies : NO COOKIE FILE -- skipped")
            continue
        try:
            body = extract_body(http_get(url, build_opener(use_cookies=use)))
            log(f"{label:13}: {len(body)} chars" + ("" if body else "  <- gated"))
        except Exception as e:
            log(f"{label:13}: ERROR {type(e).__name__}: {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--compare", action="store_true",
                    help="fetch anonymously and with cookies, compare body length")
    a = ap.parse_args()

    if a.compare:
        _compare(a.url)
        raise SystemExit(0)

    log(f"cookies: {'loaded' if cookies_available() else 'NONE (anonymous)'}")
    try:
        text = fetch_article(a.url)
        log(f"OK -- {len(text)} chars")
        if a.show:
            print(text)
    except Paywalled as e:
        log(f"PAYWALLED: {e}")
        raise SystemExit(2)
