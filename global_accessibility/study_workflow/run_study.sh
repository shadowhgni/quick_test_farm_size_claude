#!/usr/bin/env bash
# Run access_effects_v01.py from the JupyterLab terminal.
#   bash run_study.sh check    # access to every server the run needs
#   bash run_study.sh dry      # access check + plan (disk, memory, workers); nothing is computed
#   bash run_study.sh run      # full run in the background (nohup); resumes from finished stages
#   bash run_study.sh status   # is it running? last log lines
#   bash run_study.sh log      # follow the newest log (Ctrl+C stops following, not the run)
#   bash run_study.sh stop     # stop the run
# Extra options go after the command, e.g.: bash run_study.sh run --stages treatment,landuse
set -euo pipefail
cd "$(dirname "$0")"
SCRIPT="${AE_SCRIPT:-access_effects_v01.py}"

PY="${PYTHON:-python}"
cmd="${1:-help}"; shift || true
stamp=$(date +%Y%m%d_%H%M)
case "$cmd" in
  check)  "$PY" "$SCRIPT" --check-access "$@" ;;
  dry)    "$PY" "$SCRIPT" --check-access && "$PY" "$SCRIPT" --dry-run "$@" 2>&1 | tee "drystudy_$stamp.log" ;;
  run)
    if [ -f study.pid ] && kill -0 "$(cat study.pid)" 2>/dev/null; then
      echo "already running (pid $(cat study.pid)); use: bash run_study.sh status"; exit 1
    fi
    nohup "$PY" -u "$SCRIPT" "$@" > "study_$stamp.log" 2>&1 &
    echo $! > study.pid
    echo "started pid $(cat study.pid), log study_$stamp.log" ;;
  status)
    if [ -f study.pid ] && kill -0 "$(cat study.pid)" 2>/dev/null; then
      ps -o pid,etime,rss,cmd -p "$(cat study.pid)"
    else
      echo "not running"
    fi
    log=$(ls -t study_*.log 2>/dev/null | head -1 || true)
    if [ -n "$log" ]; then echo "--- $log"; tail -n 15 "$log"; fi ;;
  log)    tail -f "$(ls -t study_*.log | head -1)" ;;
  stop)   [ -f study.pid ] && kill "$(cat study.pid)" && echo "stopped pid $(cat study.pid)" || echo "no study.pid" ;;
  *)      sed -n 2,9p "$0" ;;
esac
