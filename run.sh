#!/bin/bash
# Daily entry point. Safe to run from cron: no shell profile is assumed.
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export HOME=/home/claude
export PATH=/usr/local/bin:/usr/bin:/bin
mkdir -p "$DIR/logs"
LOG="$DIR/logs/run.log"

# One run at a time; a slow run must never overlap the next cron tick.
exec 9>"$DIR/.run.lock"
if ! flock -n 9; then
  echo "[$(date '+%F %T')] another run holds the lock, exiting" >>"$LOG"
  exit 0
fi

{
  echo "===== $(date '+%F %T') start ====="
  python3 "$DIR/pipeline.py" "$@"
  rc=$?
  echo "pipeline exit=$rc"
  if [ $rc -eq 0 ]; then
    bash "$DIR/publish.sh"
    echo "publish exit=$?"
  else
    echo "pipeline failed -- keeping the previously published feed"
  fi
  echo "===== $(date '+%F %T') end ====="
} >>"$LOG" 2>&1
