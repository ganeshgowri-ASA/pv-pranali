# PV-Pranali — WSL + tmux + Claude Code + MiMo Runbook

## 0. Prerequisites (one-time, in WSL Ubuntu)
```bash
sudo apt update && sudo apt install -y tmux git curl jq build-essential
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs
curl -LsSf https://astral.sh/uv/install.sh | sh
gh auth login   # if not already
claude --version   # confirm Claude Code installed and configured against MiMo
```
Verify your `~/.claude/settings.json` (or env) has MiMo as the provider:
```json
{
  "apiBaseUrl": "https://platform.xiaomimimo.com/v1",
  "apiKey": "$MIMO_API_KEY",
  "model": "mimo-v2.5"
}
```

## 1. Clone
```bash
mkdir -p ~/work && cd ~/work
gh repo clone ganeshgowri-ASA/pv-pranali
cd pv-pranali
chmod +x infra/launch.sh
```

## 2. Secrets (.env, never commit)
```bash
cp .env.example .env
$EDITOR .env   # fill MIMO_API_KEY, SUPABASE_URL/KEY, MOUSER_API_KEY, DIGIKEY_*, GITHUB_TOKEN, VERCEL_TOKEN
```

## 3. Free-tier infra one-time setup
- **Supabase**: create project `pv-pranali`, enable `pgvector`, copy URL + anon key into .env
- **Railway**: create empty project `pv-pranali-workers`, copy token
- **Vercel**: link project (will be created later by 4.2)
- **Mouser/DigiKey**: register for free API keys (DigiKey requires app registration)

## 4. Kick off Phase 0 (cheap, ~100k tokens total)
```bash
./infra/launch.sh 0
tmux attach -t pp     # detach with Ctrl-b d
```
Wait until `/tmp/pp_init.log` shows `0.1 OK <sha>`. Verify dirs scaffolded.

## 5. Phase 1–2 (foundations + MCP wrappers, ~1.7M tokens) — schedule off-peak
```bash
crontab -e
# add:
0 23 * * 0 cd ~/work/pv-pranali && ./infra/launch.sh 1 >> /tmp/pp_cron.log 2>&1
0 23 * * 1 cd ~/work/pv-pranali && ./infra/launch.sh 2 >> /tmp/pp_cron.log 2>&1
0 8  * * * tmux kill-session -t pp 2>/dev/null
```

## 6. Phase 3 (domain agents, ~2.4M tokens)
```bash
# off-peak, 2 nights
./infra/launch.sh 3
```

## 7. Phase 4–5 (UX + E2E)
```bash
./infra/launch.sh 4
./infra/launch.sh 5
```

## 8. Monitor without attaching
```bash
tail -f /tmp/pp_guard.log    # token cap events
tail -f /tmp/pp_*.log        # per-window logs
ls blockers/                 # any session that hit a blocker
```

## 9. HITL Gate Approval (the only manual steps)
Gates are rows in Supabase `gates` table. Approve via:
```bash
# CLI helper (created by session 1.2)
uv run python -m console.gate approve --proposal <id> --gate 1
# or via Streamlit console (after session 4.1):
streamlit run console/app.py
```

## 10. Emergency Stop
```bash
tmux kill-session -t pp
pkill -f "claude --dangerously-skip-permissions" || true
```

## 11. Cost Watchdog
```bash
# Total token usage estimate
awk '{s+=$NF} END {print s}' /tmp/pp_guard.log
# Or query MiMo dashboard at https://platform.xiaomimimo.com/console
```

## 12. First Real Proposal (after build complete)
```bash
uv run python -m graph.run --intent \
  "Build EL Tester for 6\" mono-PERC cells, indoor lab, India delivery, budget 8 lakh INR"
```
The graph will pause at each of 5 gates; approve via console.
