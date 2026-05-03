# PV-Pranali — 24 Bite-Sized Sessions

Each session = one tmux window = one focused Claude Code prompt with hard token cap. Run sequentially or some in parallel. Total budget ~6M MiMo tokens.

## Phase 0 — Bootstrap
| # | Session | tmux | Goal | Tokens |
|---|---|---|---|---|
| 0.1 | repo-init | pp:init | Scaffold dirs, README, LICENSE, .gitignore | 50k |
| 0.2 | env-setup | pp:env | .env.example, Supabase project, Railway worker | 30k |
| 0.3 | mimo-config | pp:mimo | Verify MiMo via Claude Code, set rate limits | 20k |

## Phase 1 — Foundations
| # | Session | tmux | Goal | Tokens |
|---|---|---|---|---|
| 1.1 | langgraph-skeleton | pp:graph | State machine stub with 5 gates | 200k |
| 1.2 | supabase-schema | pp:db | Tables: proposals, gates, boms, suppliers, runs, docs, embeddings | 100k |
| 1.3 | mcp-bus | pp:mcp | Generic MCP client + registry | 200k |

## Phase 2 — Wrap Existing Repos as MCP
| # | Session | tmux | Goal | Tokens |
|---|---|---|---|---|
| 2.1 | mcp-vidyalaya | pp:mcp-vid | DOCX/XLSX/PPTX/PDF endpoints | 250k |
| 2.2 | mcp-antaryami | pp:mcp-ant | RAG query/ingest into Supabase pgvector | 300k |
| 2.3 | mcp-shilpasutra | pp:mcp-shi | CAD generate + STEP export | 300k |
| 2.4 | mcp-suryaprajna | pp:mcp-sur | IEC + FMEA endpoints | 200k |
| 2.5 | mcp-vidyut-srishti | pp:mcp-vyt | KiCad CLI bridge | 300k |
| 2.6 | mcp-photoniq | pp:mcp-pho | BoM impact | 200k |
| 2.7 | mcp-karaveda | pp:mcp-kar | GST/customs calc | 150k |

## Phase 3 — New Domain Agents
| # | Session | tmux | Goal | Tokens |
|---|---|---|---|---|
| 3.1 | research-agent | pp:a-res | Scrape Pasan/h.a.l.m/Sinton/Spire/Wavelabs | 400k |
| 3.2 | sourcing-agent | pp:a-src | Mouser+DigiKey India filter | 400k |
| 3.3 | ecad-plumbing-agent | pp:a-ec | KiCad SLD + PlantUML P&ID | 400k |
| 3.4 | swot-competitor-agent | pp:a-sw | Competitor SWOT | 300k |
| 3.5 | risk-finance-agent | pp:a-rf | Risk register + landed cost | 250k |
| 3.6 | outreach-agent | pp:a-out | Skyvern contact-form drafts | 350k |
| 3.7 | pitch-marketing-agent | pp:a-pm | Vercel page + LinkedIn drafts | 350k |

## Phase 4 — UX & Glue
| # | Session | tmux | Goal | Tokens |
|---|---|---|---|---|
| 4.1 | streamlit-console | pp:ui | Operator console + gate approvals | 250k |
| 4.2 | vercel-landing-tpl | pp:web | Auto-deploy product page template | 200k |

## Phase 5 — E2E + Hardening
| # | Session | tmux | Goal | Tokens |
|---|---|---|---|---|
| 5.1 | e2e-el-tester | pp:e2e | Run full pipeline for EL Tester | 600k |
| 5.2 | hardening | pp:harden | Token caps, retry logic, observability | 200k |

## Per-Session Prompt Template (`prompts/X.Y_*.md`)
```
ROLE: You are the PV-Pranali builder for session {ID}.
GOAL: {one sentence}.
CONSTRAINTS:
  - Do NOT exceed {N} tokens.
  - Write code under ./{path} only.
  - Commit with message "[{ID}] {summary}".
  - If blocked, write ./blockers/{ID}.md and EXIT 0 (do not loop).
ACCEPTANCE:
  - {checklist}
EXISTING REPOS TO REUSE: {list}
DELIVERABLES: {files}
```

## Off-Peak Cron (saves 20% per MiMo pricing)
```
0 23 * * * cd ~/work/pv-pranali && ./infra/launch.sh >> /tmp/pp_cron.log 2>&1
0 8  * * * tmux kill-session -t pp 2>/dev/null
```
