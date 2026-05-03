# PV-Pranali Pipeline Hardening Runbook

> Session 5.2 — token-cap enforcement, retry policy, circuit breaker config.

---

## 1. Token Cap Enforcement

### Script
`infra/token_guard.sh` — hard-stops any session that exceeds its credit budget.

### How it works
1. Each agent session is assigned a **SESSION_ID** and a **TOKEN_CAP**.
2. A counter file `/tmp/pp_tokens_<SESSION_ID>` tracks cumulative token usage.
3. On every invocation the script reads the counter and compares it to the cap.
4. If `used >= cap` the script writes `blockers/<SESSION_ID>.md` and exits 0 (clean stop).

### Example invocation
```bash
# Check / enforce before starting a heavy LLM call:
bash infra/token_guard.sh session_5_2 200000

# Increment counter after each call (add tokens used):
echo $(($(cat /tmp/pp_tokens_session_5_2) + 4200)) > /tmp/pp_tokens_session_5_2
bash infra/token_guard.sh session_5_2 200000
```

### Recommended caps by phase
| Phase | SESSION_ID pattern | Cap (tokens) |
|---|---|---|
| Bootstrap / light | `session_0_*` | 50 000 |
| Foundation / medium | `session_1_*`–`session_2_*` | 100 000 |
| Domain agents / heavy | `session_3_*`–`session_4_*` | 150 000 |
| E2E / hardening | `session_5_*` | 200 000 |

---

## 2. Retry Policy

All external LLM calls are wrapped with the `@retry` decorator defined in
`observability/langfuse.py`.

| Parameter | Value |
|---|---|
| Max attempts | 3 |
| Backoff delays | 2 s → 4 s → 8 s (exponential) |
| Exceptions retried | Any `Exception` raised by the wrapped function |
| Behaviour on exhaustion | Re-raises the last exception |

### Usage
```python
from observability.langfuse import retry

@retry(max_attempts=3, backoff=(2.0, 4.0, 8.0))
def call_llm(prompt: str) -> str:
    ...
```

---

## 3. Circuit Breaker

The `CircuitBreaker` class in `observability/langfuse.py` protects every
external API call (LLM provider, MCP servers, Supabase).

| Parameter | Value |
|---|---|
| Failure threshold | 3 consecutive failures → OPEN |
| Recovery timeout | 60 s → transitions to HALF_OPEN |
| Success in HALF_OPEN | Resets to CLOSED |
| Failure in HALF_OPEN | Returns to OPEN (timer reset) |

### State machine
```
CLOSED ──(3 failures)──► OPEN ──(60 s)──► HALF_OPEN
   ▲                                          │
   └──────────(success)──────────────────────┘
```

### Log messages emitted
| Event | Level | Message pattern |
|---|---|---|
| Opens | ERROR | `[circuit_breaker:<name>] OPEN after N consecutive failures` |
| Half-opens | INFO | `[circuit_breaker:<name>] -> HALF_OPEN after Xs` |
| Closes | INFO | `[circuit_breaker:<name>] -> CLOSED` |
| Call rejected | RuntimeError raised | `[circuit_breaker:<name>] OPEN — call rejected` |

### Usage
```python
from observability.langfuse import CircuitBreaker

cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0, name="mouser-api")
result = cb.call(requests.get, url, timeout=10)
```

---

## 4. LangfuseTracer — Observability

Every LLM call should be routed through `LangfuseTracer.trace_llm_call()`.

### Logged per call
| Field | Source |
|---|---|
| `trace_id` | Langfuse-assigned UUID |
| `model` | Caller-supplied string (e.g. `claude-sonnet-4-6`) |
| `tokens_used` | `input_tokens + output_tokens` |
| `latency_ms` | Wall-clock ms from call start to return |

### Quick start
```python
from observability.langfuse import LangfuseTracer

tracer = LangfuseTracer()  # reads LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY from env
result = tracer.trace_llm_call(
    fn=my_llm_fn,
    model="claude-sonnet-4-6",
    input_tokens=1200,
    session_id="session_5_2",
    kwargs={"prompt": "Summarise the BoM for EL Tester"},
)
```

### Required environment variables
```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"  # optional; defaults to cloud
```

---

## 5. Integration Checklist

- [ ] `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` set in `.env` / Railway secrets.
- [ ] `pip install langfuse` added to `requirements.txt`.
- [ ] Each agent session calls `bash infra/token_guard.sh <SESSION_ID> <CAP>` before starting.
- [ ] All LLM calls routed through `LangfuseTracer.trace_llm_call()`.
- [ ] `CircuitBreaker` instantiated per external service (one per MCP server / API).
- [ ] Retry decorator applied to every outbound HTTP / LLM call.
