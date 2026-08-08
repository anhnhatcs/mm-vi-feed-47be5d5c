#!/bin/bash
# Commit and push docs/feed.xml. No-op when nothing changed.
set -uo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || exit 1

git add docs/feed.xml docs/robots.txt 2>/dev/null

if git diff --cached --quiet; then
  echo "feed unchanged -- nothing to publish"
  exit 0
fi

git -c user.name="mm-vi-feed" -c user.email="noreply@localhost" \
    commit -q -m "feed: $(date '+%F %H:%M')" || exit 1

if git remote get-url origin >/dev/null 2>&1; then
  git push -q origin HEAD && echo "pushed" || { echo "push FAILED"; exit 1; }
else
  echo "no remote configured -- committed locally only"
fi
