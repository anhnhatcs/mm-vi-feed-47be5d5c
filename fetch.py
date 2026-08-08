"""Fetch the MM RSS feeds and normalise their items.

One failing feed must never abort the run -- it is logged and skipped.
"""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from common import build_opener, http_get, log, strip_html
from sources import SOURCES


def _item(node, source: str) -> dict | None:
    link = (node.findtext("link") or "").strip()
    title = strip_html(node.findtext("title"))
    if not link or not title:
        return None
    guid = (node.findtext("guid") or link).strip()
    try:
        pub = parsedate_to_datetime(node.findtext("pubDate"))
    except Exception:
        pub = None
    enclosure = node.find("enclosure")
    return {
        "guid": guid,
        "link": link,
        "title_de": title,
        "teaser_de": strip_html(node.findtext("description")),
        "pubdate": pub,
        "category": strip_html(node.findtext("category")),
        "image": enclosure.get("url") if enclosure is not None else None,
        "source": source,
    }


def fetch_all() -> list[dict]:
    opener = build_opener()
    items, seen = [], set()
    for url, name in SOURCES:
        try:
            xml = http_get(url, opener)
            nodes = ET.fromstring(xml).find("channel").findall("item")
        except Exception as e:
            log(f"WARN feed failed, skipping: {name} ({type(e).__name__}: {e})")
            continue
        n = 0
        for node in nodes:
            it = _item(node, name)
            if it and it["guid"] not in seen:
                seen.add(it["guid"])
                items.append(it)
                n += 1
        log(f"  {name}: {n} items")
    items.sort(key=lambda i: (i["pubdate"] is not None, i["pubdate"]), reverse=True)
    return items


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.parse_args()
    got = fetch_all()
    log(f"total {len(got)} unique items")
    for i in got[:5]:
        print(f"  {i['pubdate']} | {i['source']:24} | {i['title_de'][:60]}")
