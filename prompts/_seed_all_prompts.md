ROLE: PV-Pranali META-PROMPT GENERATOR (run FIRST, ONE TIME, before parallel dispatch).

GOAL: Read PRD.md and docs/SESSIONS.md, then write the remaining 22 session prompt files under prompts/ so that ./infra/parallel.sh can dispatch all waves.

CONSTRAINTS:
- Token cap: 80,000 total.
- Read-only on existing files; write-only under prompts/.
- One commit at the end: "[seed] generate 22 session prompts".
- If blocked, write blockers/_seed.md and EXIT 0.

FOR EACH SESSION below, create prompts/{ID}_{WIN}.md with this structure:
ROLE: PV-Pranali builder for Session {ID} ({WIN}).
GOAL: {one sentence}.
CONSTRAINTS: token cap {CAP}; read PRD.md first; write only under {ALLOWED_DIRS}; commit "[{ID}] {summary}"; on block write blockers/{ID}.md and EXIT 0; reuse via MCP.
DELIVERABLES: {file list}.
ACCEPTANCE: {checklist}.
EXISTING REPOS TO REUSE: {list}.

SESSION SPECS (ID|WIN|CAP|DIRS|GOAL|FILES|REUSES):

0.2|env|30000|infra/,.env.example|Wire .env.example + setup helpers for Supabase/Railway/Vercel/MiMo/Mouser/DigiKey/Unipile|infra/setup_supabase.sh,infra/setup_railway.sh|n/a
0.3|mimo|20000|infra/|Verify Claude Code uses MiMo; 1-token ping with latency|infra/check_mimo.sh|n/a
1.1|graph|200000|graph/|LangGraph state machine: research,standards,components,gate1,cad,ecad,pcb,gate2,bom_impact,risk_swot,rfq_draft,gate3,proposal,pitch,gate4,landing,linkedin,gate5|graph/state.py,graph/nodes.py,graph/run.py,tests/test_graph.py|n/a
1.2|db|100000|infra/migrations/,console/|Supabase migrations + console/gate.py CLI|infra/migrations/0001_init.sql,console/gate.py|n/a
1.3|mcp|200000|mcp_servers/_lib/|Generic MCP client+registry|mcp_servers/_lib/client.py,registry.py,types.py|modelcontextprotocol/python-sdk
2.1|mcp-vid|250000|mcp_servers/vidyalaya/|MCP wrap vidyalaya-office docx/xlsx/pptx/pdf|server.py,manifest.json|vidyalaya-office
2.2|mcp-ant|300000|mcp_servers/antaryami/|MCP RAG with Supabase pgvector|server.py|antaryami-os
2.3|mcp-shi|300000|mcp_servers/shilpasutra/|MCP cad_generate,step_export,cfd_run|server.py|ShilpaSutra
2.4|mcp-sur|200000|mcp_servers/suryaprajna/|MCP iec_lookup,fmea,reliability|server.py|SuryaPrajna
2.5|mcp-vyt|300000|mcp_servers/vidyut/|MCP schematic,layout,drc via KiCad CLI|server.py|vidyut-srishti-prd
2.6|mcp-pho|200000|mcp_servers/photoniq/|MCP bom_impact,ctm|server.py|PhotonIQ
2.7|mcp-kar|150000|mcp_servers/karaveda/|MCP gst_calc,customs_calc|server.py|karaveda
3.1|a-res|400000|agents/research/|Research scrape Pasan/halm/Sinton/Spire/Wavelabs/Endeas/NISE + ingest antaryami|agent.py,sources.yml|browser-use,antaryami-os
3.2|a-src|400000|agents/sourcing/|Mouser+DigiKey API India filter|mouser.py,digikey.py,india_filter.py|mouser-api,digikey-api
3.3|a-ec|400000|agents/ecad/|KiCad SLD+control wiring+PlantUML P&ID|sld.py,pid.py|KiCad,PlantUML
3.4|a-sw|300000|agents/swot/|Competitor SWOT scraping|agent.py|search_web
3.5|a-rf|250000|agents/risk/|Risk register + landed cost (FOB+freight+7.5% duty+18% GST)|landed_cost.py,register.py|karaveda MCP
3.6|a-out|350000|agents/outreach/|Skyvern contact-form RFQ drafts (gate3)|skyvern_runner.py,templates/|Skyvern
3.7|a-pm|350000|agents/marketing/|Pitch pptx + Vercel landing + LinkedIn drafts|pitch.py,landing.py,linkedin.py|vidyalaya-office,Unipile
4.1|ui|250000|console/|Streamlit kanban + 5 gate buttons + token meter|app.py,components/|vidyut-eee-portal
4.2|web|200000|agents/marketing/landing/|Vercel Next.js landing template per product|template/|n/a
5.1|e2e|600000|tests/e2e/|EL Tester full pipeline with mocked gates|test_el_tester.py|all above
5.2|harden|200000|infra/,observability/|Token caps verify + Langfuse + retry + circuit breaker|hardening.md,langfuse.py|Langfuse

ACCEPTANCE: 22 prompt files under prompts/ each 600-2000 chars; one commit pushed; write "seed OK <sha>" to /tmp/pp_seed.log; EXIT 0.
