#!/usr/bin/env bash
# PV-Pranali PARALLEL dispatcher — N Claude Code sessions concurrent, with token caps,
# DAG waves, file locks, blocker handling, auto-commit. Unattended overnight on MiMo.
# Usage: ./infra/parallel.sh {wave1|...|wave6|all|status|resume}
# Deps: sudo apt install -y tmux jq parallel flock
set -euo pipefail
PROJECT_DIR="$HOME/work/pv-pranali"
cd "$PROJECT_DIR"
MODEL="${MIMO_MODEL:-mimo-v2.5}"
LOG_DIR="/tmp/pp-logs"
mkdir -p "$LOG_DIR" blockers .state

declare -A WAVES
WAVES[wave1]="0.1|init|50000  0.2|env|30000  0.3|mimo|20000"
WAVES[wave2]="1.1|graph|200000  1.2|db|100000  1.3|mcp|200000"
WAVES[wave3]="2.1|mcp-vid|250000  2.2|mcp-ant|300000  2.3|mcp-shi|300000  2.4|mcp-sur|200000  2.5|mcp-vyt|300000  2.6|mcp-pho|200000  2.7|mcp-kar|150000"
WAVES[wave4]="3.1|a-res|400000  3.2|a-src|400000  3.3|a-ec|400000  3.4|a-sw|300000  3.5|a-rf|250000  3.6|a-out|350000  3.7|a-pm|350000"
WAVES[wave5]="4.1|ui|250000  4.2|web|200000"
WAVES[wave6]="5.1|e2e|600000  5.2|harden|200000"

MAX_PARALLEL="${MAX_PARALLEL:-4}"

run_session() {
  local ID="$1" WIN="$2" CAP="$3"
  local PROMPT="prompts/${ID}_${WIN}.md"
  local LOG="$LOG_DIR/${ID}_${WIN}.log"
  local LOCK=".state/${ID}.lock"
  local DONE=".state/${ID}.done"
  [ -f "$DONE" ] && { echo "[$ID] done"; return 0; }
  [ ! -f "$PROMPT" ] && { echo "[$ID] missing $PROMPT" >> "$LOG_DIR/_dispatch.log"; return 0; }
  exec 9>"$LOCK"; flock -n 9 || { echo "[$ID] locked"; return 0; }
  echo "[$(date -Iseconds)] START $ID ($WIN cap=$CAP)" | tee -a "$LOG_DIR/_dispatch.log"
  ( claude --dangerously-skip-permissions --model "$MODEL" -p "$(cat "$PROMPT")" 2>&1 | tee "$LOG" ) &
  local PID=$!
  ( while kill -0 "$PID" 2>/dev/null; do
      [ -f "$LOG" ] || { sleep 10; continue; }
      TOK=$(( $(wc -c <"$LOG") / 4 ))
      if [ "$TOK" -gt "$CAP" ]; then
        echo "[$(date -Iseconds)] CAPPED $ID @ ${TOK}/${CAP}" >> "$LOG_DIR/_dispatch.log"
        kill "$PID" 2>/dev/null || true
        echo "capped at ${TOK} tokens" > "blockers/${ID}.md"
        break
      fi
      sleep 30
    done ) &
  wait "$PID" || true
  if [ -f "blockers/${ID}.md" ]; then
    echo "[$(date -Iseconds)] BLOCKED $ID" | tee -a "$LOG_DIR/_dispatch.log"
  else
    touch "$DONE"
    echo "[$(date -Iseconds)] DONE  $ID" | tee -a "$LOG_DIR/_dispatch.log"
    git add -A && git commit -m "[$ID] auto-commit" 2>/dev/null || true
    git pull --rebase --autostash 2>/dev/null || true
    git push 2>/dev/null || true
  fi
}
export -f run_session
export MODEL LOG_DIR

run_wave() {
  local W="$1"
  local L="${WAVES[$W]:-}"
  [ -z "$L" ] && { echo "unknown wave: $W"; exit 1; }
  echo "[$(date -Iseconds)] >>> $W (parallel=$MAX_PARALLEL)" | tee -a "$LOG_DIR/_dispatch.log"
  echo "$L" | tr ' ' '\n' | grep -v '^$' | parallel -j "$MAX_PARALLEL" --colsep '\\|' run_session {1} {2} {3}
}

case "${1:-help}" in
  wave1|wave2|wave3|wave4|wave5|wave6) run_wave "$1" ;;
  all) for w in wave1 wave2 wave3 wave4 wave5 wave6; do run_wave "$w"; done ;;
  status)
    echo == DONE ==; ls .state/*.done 2>/dev/null | sed 's|.*/||;s|.done||' || echo none
    echo == BLOCKED ==; ls blockers/*.md 2>/dev/null | sed 's|.*/||;s|.md||' || echo none
    tail -20 "$LOG_DIR/_dispatch.log" 2>/dev/null || true ;;
  resume) rm -f blockers/*.md; for w in wave1 wave2 wave3 wave4 wave5 wave6; do run_wave "$w"; done ;;
  *) echo "Usage: $0 {wave1..6|all|status|resume}  Env: MAX_PARALLEL=4 MIMO_MODEL=mimo-v2.5" ;;
esac
