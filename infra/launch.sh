#!/usr/bin/env bash
# PV-Pranali launcher — spawns 24 tmux windows, each with one Claude Code session
# Usage: ./infra/launch.sh [phase]   # phase = 0|1|2|3|4|5|all (default all)
set -euo pipefail

SESSION="pp"
PHASE="${1:-all}"
PROJECT_DIR="$HOME/work/pv-pranali"
MODEL="mimo-v2.5"

declare -A WINDOWS=(
  [0.1]="init|50000"
  [0.2]="env|30000"
  [0.3]="mimo|20000"
  [1.1]="graph|200000"
  [1.2]="db|100000"
  [1.3]="mcp|200000"
  [2.1]="mcp-vid|250000"
  [2.2]="mcp-ant|300000"
  [2.3]="mcp-shi|300000"
  [2.4]="mcp-sur|200000"
  [2.5]="mcp-vyt|300000"
  [2.6]="mcp-pho|200000"
  [2.7]="mcp-kar|150000"
  [3.1]="a-res|400000"
  [3.2]="a-src|400000"
  [3.3]="a-ec|400000"
  [3.4]="a-sw|300000"
  [3.5]="a-rf|250000"
  [3.6]="a-out|350000"
  [3.7]="a-pm|350000"
  [4.1]="ui|250000"
  [4.2]="web|200000"
  [5.1]="e2e|600000"
  [5.2]="harden|200000"
)

tmux has-session -t $SESSION 2>/dev/null || tmux new-session -d -s $SESSION -n bootstrap

for ID in "${!WINDOWS[@]}"; do
  IFS='|' read -r WIN CAP <<< "${WINDOWS[$ID]}"
  PH="${ID%%.*}"
  if [ "$PHASE" != "all" ] && [ "$PHASE" != "$PH" ]; then continue; fi

  PROMPT_FILE="$PROJECT_DIR/prompts/${ID}_${WIN}.md"
  LOG="/tmp/pp_${WIN}.log"

  tmux new-window -t $SESSION -n "$WIN" 2>/dev/null || true
  tmux send-keys -t "$SESSION:$WIN" "cd $PROJECT_DIR && \
    claude --dangerously-skip-permissions --model $MODEL \
    -p \"\$(cat $PROMPT_FILE)\" 2>&1 | tee $LOG" C-m
done

# Token guard daemon (background)
(
  while true; do
    for ID in "${!WINDOWS[@]}"; do
      IFS='|' read -r WIN CAP <<< "${WINDOWS[$ID]}"
      LOG="/tmp/pp_${WIN}.log"
      [ -f "$LOG" ] || continue
      CHARS=$(wc -c < "$LOG")
      TOKENS=$((CHARS/4))
      if [ "$TOKENS" -gt "$CAP" ]; then
        tmux send-keys -t "$SESSION:$WIN" C-c 2>/dev/null || true
        echo "[$(date -Iseconds)] CAPPED $WIN @ ${TOKENS}/${CAP}" >> /tmp/pp_guard.log
      fi
    done
    sleep 60
  done
) &

echo "PV-Pranali launched. Attach: tmux attach -t $SESSION"
echo "Guard log: tail -f /tmp/pp_guard.log"
