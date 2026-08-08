"""Shared helpers: HTTP with a browser UA, optional MM+ cookie jar, HTML stripping."""
from __future__ import annotations

import gzip
import html
import http.cookiejar
import os
import re
import sys
import time
import urllib.request
import zlib

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)

COOKIE_PATH = os.path.expanduser("~/.config/mm-vi-feed/cookies.txt")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def build_opener(use_cookies: bool = False):
    """An opener that looks like Safari. With use_cookies, load the MM+ session.

    MozillaCookieJar drops session cookies unless both ignore_* flags are set --
    that is the classic way this silently reads as logged-out.
    """
    handlers = []
    jar = None
    if use_cookies:
        jar = http.cookiejar.MozillaCookieJar(COOKIE_PATH)
        jar.load(ignore_discard=True, ignore_expires=True)
        handlers.append(urllib.request.HTTPCookieProcessor(jar))
    opener = urllib.request.build_opener(*handlers)
    opener.addheaders = [
        ("User-Agent", UA),
        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("Accept-Language", "de-DE,de;q=0.9,en;q=0.8"),
        ("Accept-Encoding", "gzip, deflate"),
    ]
    opener.cookie_jar = jar
    return opener


def cookies_available() -> bool:
    return os.path.exists(COOKIE_PATH) and os.path.getsize(COOKIE_PATH) > 0


def http_get(url: str, opener=None, timeout: int = 30) -> str:
    opener = opener or build_opener()
    with opener.open(url, timeout=timeout) as r:
        raw = r.read()
        enc = (r.headers.get("Content-Encoding") or "").lower()
    if enc == "gzip":
        raw = gzip.decompress(raw)
    elif enc == "deflate":
        raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw.decode("utf-8", errors="replace")


_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\xa0]+")


def strip_html(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>", "\n", s)
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = _WS.sub(" ", s)
    return "\n".join(ln.strip() for ln in s.split("\n") if ln.strip()).strip()
