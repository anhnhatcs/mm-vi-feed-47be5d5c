"""German -> Vietnamese via the headless Claude CLI.

The CLI must be invoked with a clean environment: inherited CLAUDE_CODE_* session
variables make a nested run fail with "Not logged in". `env -i` is what cron gives us
anyway, so this is also what the cron path exercises.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess

from common import log
from sources import TRANSLATE_BATCH

CLAUDE = "/home/claude/.npm-global/bin/claude"
MODEL = "sonnet"
TIMEOUT = 900

PROMPT = """You are translating German news from the Mannheimer Morgen into Vietnamese.

Rules:
- Translate faithfully. Do not summarise, comment, or add anything.
- Natural Vietnamese news register.
- Keep proper nouns (people, places, parties, companies) in their German form.
- "body_vi" keeps the paragraph breaks of the input, separated by blank lines.
- If an article's "body" is empty, return "" for its "body_vi".

Output ONLY a JSON array. No prose, no markdown fence.
Schema: [{"id": <int>, "title_vi": "...", "teaser_vi": "...", "body_vi": "..."}]

Input:
"""


def _run_claude(prompt: str) -> str:
    proc = subprocess.run(
        [CLAUDE, "-p", "--output-format", "json", "--model", MODEL],
        input=prompt, capture_output=True, text=True, timeout=TIMEOUT,
        env={"HOME": os.path.expanduser("~"), "PATH": "/usr/bin:/bin"},
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude exit {proc.returncode}: {proc.stderr[:200]}")
    payload = json.loads(proc.stdout)
    if payload.get("is_error"):
        raise RuntimeError(f"claude error: {str(payload.get('result'))[:200]}")
    return payload["result"]


def _parse(text: str) -> list[dict]:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < 0:
        raise ValueError("no JSON array in reply")
    return json.loads(text[start:end + 1])


def translate_batch(batch: list[dict]) -> None:
    """Attach *_vi fields in place. German is kept, marked, if translation fails."""
    payload = [
        {"id": n, "title": it["title_de"], "teaser": it["teaser_de"],
         "body": it.get("body_de", "")}
        for n, it in enumerate(batch)
    ]
    prompt = PROMPT + json.dumps(payload, ensure_ascii=False)

    for attempt in (1, 2):
        try:
            got = {int(r["id"]): r for r in _parse(_run_claude(prompt))}
            for n, it in enumerate(batch):
                r = got.get(n)
                if not r:
                    raise ValueError(f"missing id {n} in reply")
                it["title_vi"] = r.get("title_vi") or it["title_de"]
                it["teaser_vi"] = r.get("teaser_vi") or it["teaser_de"]
                it["body_vi"] = r.get("body_vi") or ""
            return
        except Exception as e:
            log(f"  WARN translation attempt {attempt} failed: {type(e).__name__}: {e}")

    log(f"  translation gave up for {len(batch)} items -- keeping German")
    for it in batch:
        it["title_vi"] = "[DE] " + it["title_de"]
        it["teaser_vi"] = it["teaser_de"]
        it["body_vi"] = it.get("body_de", "")


def translate_all(items: list[dict]) -> None:
    for i in range(0, len(items), TRANSLATE_BATCH):
        batch = items[i:i + TRANSLATE_BATCH]
        log(f"  translating {i + 1}-{i + len(batch)} of {len(items)}")
        translate_batch(batch)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=3)
    a = ap.parse_args()

    from article import fetch_many
    from fetch import fetch_all

    items = fetch_all()[:a.sample]
    ok, walled = fetch_many(items)
    log(f"bodies: {ok} full, {walled} paywalled")
    translate_all(items)
    for it in items:
        print("=" * 70)
        print("DE :", it["title_de"])
        print("VI :", it["title_vi"])
        print("VI teaser:", it["teaser_vi"])
        print("VI body  :", (it["body_vi"] or "(none)")[:600])
