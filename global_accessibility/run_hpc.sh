#!/usr/bin/env bash
# Run global_accessibility_v03.py from the JupyterLab terminal.
#   bash run_hpc.sh check    # access to every server the run needs
#   bash run_hpc.sh dry      # access check + plan (disk, memory, workers); nothing is computed
#   bash run_hpc.sh run      # full run in the background (nohup); resumes from finished stages
#   bash run_hpc.sh status   # is it running? last log lines
#   bash run_hpc.sh log      # follow the newest log (Ctrl+C stops following, not the run)
#   bash run_hpc.sh stop     # stop the run
# Extra options go after the command, e.g.: bash run_hpc.sh run --no-cleanup
set -euo pipefail
cd "$(dirname "$0")"
SCRIPT="${GA_SCRIPT:-global_accessibility_v03.py}"
[ -f "$SCRIPT" ] || SCRIPT=global_accessibility_v3.py
PY="${PYTHON:-python}"
cmd="${1:-help}"; shift || true
stamp=$(date +%Y%m%d_%H%M)
case "$cmd" in
  check)  "$PY" "$SCRIPT" --check-access "$@" ;;
  dry)    "$PY" "$SCRIPT" --check-access && "$PY" "$SCRIPT" --dry-run "$@" 2>&1 | tee "dryrun_$stamp.log" ;;
  run)
    if [ -f run.pid ] && kill -0 "$(cat run.pid)" 2>/dev/null; then
      echo "already running (pid $(cat run.pid)); use: bash run_hpc.sh status"; exit 1
    fi
    nohup "$PY" -u "$SCRIPT" "$@" > "run_$stamp.log" 2>&1 &
    echo $! > run.pid
    echo "started pid $(cat run.pid), log run_$stamp.log" ;;
  status)
    if [ -f run.pid ] && kill -0 "$(cat run.pid)" 2>/dev/null; then
      ps -o pid,etime,rss,cmd -p "$(cat run.pid)"
    else
      echo "not running"
    fi
    log=$(ls -t run_*.log 2>/dev/null | head -1 || true)
    if [ -n "$log" ]; then echo "--- $log"; tail -n 15 "$log"; fi ;;
  log)    tail -f "$(ls -t run_*.log | head -1)" ;;
  stop)   [ -f run.pid ] && kill "$(cat run.pid)" && echo "stopped pid $(cat run.pid)" || echo "no run.pid" ;;
  *)      sed -n 2,9p "$0" ;;
esac
