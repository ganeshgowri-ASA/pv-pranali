# PV-Pranali — Product Requirements Document (PRD)

## 1. Vision
A self-driving multi-agent system that takes a single line of intent (e.g., "Build IEC 61215 Sun Simulator Class AAA, 2m×1.3m") and produces a customer-ready proposal: BoM, CAD, PCB, SLD, pitch deck, landing page, and LinkedIn campaign — by orchestrating 30+ existing ganeshgowri-ASA repos via MCP, running on Claude Code + MiMo in WSL/tmux.

## 2. Goals
- G1: End-to-end proposal in <= 6 hours of agent runtime
- G2: Reuse >= 80% of existing repos (no rewrites)
- G3: Run unattended in WSL/tmux on MiMo with hard credit caps
- G4: HITL only at 5 named gates: BoM-Freeze, PCB-DRC, RFQ-Send, Public-Post, Customer-Send
- G5: India-deliverable component sourcing (Mouser / DigiKey / Element14 / Robu / RS Components)
- G6: Free-tier infra only (Supabase + Railway $5 + Vercel Hobby)
- G7: Token budget per proposal <= 8M MiMo tokens

## 3. Non-Goals
- No auto-sending of customer or supplier emails (drafts only)
- No auto-publishing to LinkedIn / website (drafts only, gated)
- No auto-placing of component purchase orders

## 4. Personas
- P1 Operator (you): kicks off proposals, reviews 5 gates
- P2 Customer Engineer: receives final proposal & datasheet
- P3 Supplier Sales: receives RFQ drafts after gate approval

## 5. Success Metrics
| KPI | Target |
|---|---|
| Time intent → draft proposal | < 6 h |
| MiMo tokens / proposal | < 8M |
| Repos reused | >= 25 |
| Manual interventions | <= 5 gates |
| Component price accuracy vs API | >= 95% |
| First-pass proposal acceptance | >= 70% |

## 6. Architecture — 7 Layers
```
L7 Presentation: Streamlit Console + Vercel Landing Page
L6 Output:       vidyalaya-office (DOCX/XLSX/PPTX/PDF)
L5 Domain:       Research, Sourcing, SWOT, Risk, Outreach, Pitch, Marketing
L4 Engineering:  ShilpaSutra (CAD), vidyut-srishti (PCB), eCAD-Plumbing, suraksha
L3 Knowledge:    antaryami-os RAG + SuryaPrajna + Supabase pgvector
L2 Orchestration: LangGraph state machine + MCP bus
L1 Runtime:      WSL Ubuntu + tmux + Claude Code + MiMo V2.5
```

## 7. MCP Server Inventory
| MCP | Wraps | Key Tools |
|---|---|---|
| mcp-shilpasutra | ShilpaSutra | cad_generate, step_export, cfd_run |
| mcp-antaryami | antaryami-os | rag_query, rag_ingest, kb_compare |
| mcp-vidyalaya | vidyalaya-office | docx, xlsx, pptx, pdf |
| mcp-suryaprajna | SuryaPrajna | iec_lookup, fmea, reliability |
| mcp-vidyut-srishti | vidyut-srishti-prd | schematic, layout, drc |
| mcp-photoniq | PhotonIQ | bom_impact, ctm |
| mcp-spanda-daq | spanda-daq | daq_acquire |
| mcp-karaveda | karaveda | gst_calc, customs_calc |
| mcp-karmadhara | karmadhara | workflow_create, gate_request |
| mcp-mouser (NEW) | Mouser API | search, quote, india_deliverable |
| mcp-digikey (NEW) | DigiKey API | search, quote |
| mcp-skyvern (NEW) | Skyvern | fill_contact_form |

## 8. Workflow (LangGraph)
intent → research → standards_lookup → component_select
→ [GATE 1: BoM Freeze] → cad → ecad → pcb
→ [GATE 2: DRC pass] → bom_impact → risk_swot
→ supplier_rfq_draft → [GATE 3: RFQ-Send approval]
→ proposal_assemble → pitch_deck
→ [GATE 4: Public-Post approval] → landing_page + linkedin_draft
→ [GATE 5: Customer-Send] → done

Each gate writes to Supabase `gates` table. tmux agents poll for status='approved' → continue. No interactive prompts → no wasted MiMo credits.

## 9. 24 Bite-Sized Sessions
See `docs/SESSIONS.md` for full table. Phases:
- Phase 0 Bootstrap (3 sessions)
- Phase 1 Foundations (3)
- Phase 2 Wrap Existing Repos as MCP (7)
- Phase 3 New Domain Agents (7)
- Phase 4 UX & Glue (2)
- Phase 5 E2E Test + Hardening (2)

## 10. Database
- Primary: Supabase (free tier) — Postgres + pgvector + Auth + Storage + Realtime
- Workers only: Railway ($5 credit) — Skyvern, Celery queue
- Tables: proposals, gates, boms, suppliers, runs, docs, embeddings

## 11. MiMo Token Strategy
- MiMo V2.5 with off-peak 20% discount for heavy reasoning
- Cheaper models for deterministic tasks (form-fill, schema validation)
- Aggressive caching in antaryami pgvector
- Hard per-session token caps via `infra/token_guard.sh`
- Schedule >300k-token sessions during 23:00–08:00 IST (off-peak)

## 12. Credit-Saving Rules (enforced in every prompt)
1. Cache-first: rag_query antaryami before generating
2. Per-session token caps
3. Off-peak only for heavy sessions
4. Reuse over rewrite — import via MCP, never re-implement
5. No infinite loops — EXIT 0 on blockers, write `./blockers/{id}.md`
6. Diff-only commits, not full files
7. Model routing: small model for deterministic, MiMo V2.5 for reasoning

## 13. HITL Gates (the only 5 places humans must act)
1. BoM Freeze
2. PCB DRC pass
3. Supplier RFQ send
4. Public post (LinkedIn / website)
5. Customer proposal send

## 14. First Product to Build (E2E test)
**EL (Electroluminescence) Tester** — smaller scope than sun simulator, leverages surya-yantra + suraksha + PV-TestEquip-PowerSupply. Target: full pipeline in one off-peak overnight run.

## 15. Open-Source Repos to Combine
- langchain-ai/langgraph (orchestration)
- modelcontextprotocol/servers (MCP reference)
- Skyvern-AI/skyvern (supplier contact forms)
- browser-use/browser-use (supplier site nav)
- atopile/atopile + KiCad Python API (PCB-as-code)
- CadQuery/cadquery (parametric CAD)
- mouser-api, digikey-api (PyPI)
- unipile-node-sdk (LinkedIn drafts)
- microsoft/markitdown + unstructured-io/unstructured (RAG ingest)

## 16. Risks
- MiMo rate limits during peak → mitigate with off-peak cron
- Supplier API quotas → cache + dedupe
- KiCad CLI version drift → pin in Docker
- Long-running tmux loops → token_guard.sh + EXIT 0 discipline

## 17. Status
Repo bootstrapped: 2026-05-03. Awaiting Phase 0 dispatch.
