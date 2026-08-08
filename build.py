"""Render the stored Vietnamese items into docs/feed.xml (RSS 2.0)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

import store
from common import PROJECT_DIR, log
from sources import FEED_ITEM_LIMIT

FEED_PATH = os.path.join(PROJECT_DIR, "docs", "feed.xml")
STATUS_PATH = os.path.join(PROJECT_DIR, "last_run.json")

FEED_TITLE = "Mannheimer Morgen (Tiếng Việt)"
FEED_DESC = "Tin tức Mannheimer Morgen, dịch sang tiếng Việt hằng ngày."


def _rfc822(iso: str | None) -> str:
    if not iso:
        return format_datetime(datetime.now(timezone.utc))
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return format_datetime(datetime.now(timezone.utc))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return format_datetime(dt)


def _cdata(text: str) -> str:
    return "<![CDATA[" + (text or "").replace("]]>", "]]&gt;") + "]]>"


def _html_body(row) -> str:
    parts = []
    if row["image"]:
        parts.append(f'<p><img src="{escape(row["image"], {chr(34): "&quot;"})}" /></p>')
    body = row["body_vi"] or ""
    if body.strip():
        parts += [f"<p>{escape(p)}</p>" for p in body.split("\n\n") if p.strip()]
    else:
        parts.append(f"<p>{escape(row['teaser_vi'] or '')}</p>")
        parts.append('<p><em>(Chỉ có phần tóm tắt — bài viết này thuộc diện MM+.)</em></p>')
    parts.append(f'<p><a href="{escape(row["link"])}">Đọc bản gốc tiếng Đức</a></p>')
    return "\n".join(parts)


def _item_xml(row) -> str:
    return f"""    <item>
      <title>{escape(row['title_vi'] or '')}</title>
      <link>{escape(row['link'])}</link>
      <guid isPermaLink="false">{escape(row['guid'])}</guid>
      <pubDate>{_rfc822(row['pubdate'])}</pubDate>
      <category>{escape(row['source'] or '')}</category>
      <description>{_cdata(row['teaser_vi'] or '')}</description>
      <content:encoded>{_cdata(_html_body(row))}</content:encoded>
    </item>"""


def _warning_item() -> str:
    """Surface an expired cookie in Feedly, not only in the VPS log."""
    try:
        st = json.load(open(STATUS_PATH))
    except Exception:
        return ""
    if not (st.get("cookies_present") and st.get("gated", 0) > 0):
        return ""
    now = format_datetime(datetime.now(timezone.utc))
    day = datetime.now().strftime("%Y-%m-%d")
    msg = (f"{st['gated']} bài bị chặn dù đã có cookie — phiên MM+ có lẽ đã hết hạn. "
           f"Hãy đăng nhập lại và xuất cookies.txt mới.")
    return f"""    <item>
      <title>⚠️ MM cookie hết hạn — cần xuất lại</title>
      <link>https://www.mannheimer-morgen.de/login.html</link>
      <guid isPermaLink="false">mm-vi-feed-cookie-warning-{day}</guid>
      <pubDate>{now}</pubDate>
      <category>Status</category>
      <description>{_cdata(msg)}</description>
    </item>"""


def build() -> int:
    con = store.connect()
    rows = store.recent(con, FEED_ITEM_LIMIT)
    items = [x for x in (_warning_item(),) if x] + [_item_xml(r) for r in rows]
    now = format_datetime(datetime.now(timezone.utc))
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"
     xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{FEED_TITLE}</title>
    <link>https://www.mannheimer-morgen.de/</link>
    <description>{FEED_DESC}</description>
    <language>vi</language>
    <lastBuildDate>{now}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""
    os.makedirs(os.path.dirname(FEED_PATH), exist_ok=True)
    with open(FEED_PATH, "w", encoding="utf-8") as fh:
        fh.write(xml)
    log(f"wrote {FEED_PATH} ({len(rows)} items)")
    return len(rows)


if __name__ == "__main__":
    build()
