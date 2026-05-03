"""LangfuseTracer — wraps every LLM call with trace/span/score logging.

Requires: pip install langfuse
Env vars:  LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST (optional)
"""
from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional

try:
    from langfuse import Langfuse
except ImportError as exc:  # pragma: no cover
    raise ImportError("Install langfuse: pip install langfuse") from exc

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

def retry(max_attempts: int = 3, backoff: tuple[float, ...] = (2.0, 4.0, 8.0)):
    """Retry up to *max_attempts* times with explicit *backoff* waits (seconds)."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            delays = list(backoff) + [backoff[-1]] * max(0, max_attempts - len(backoff))
            last_exc: Exception | None = None
            for attempt in range(max_attempts):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    wait = delays[attempt] if attempt < len(delays) else delays[-1]
                    logger.warning(
                        "[retry] %s attempt %d/%d failed: %s — retrying in %.0fs",
                        fn.__qualname__, attempt + 1, max_attempts, exc, wait,
                    )
                    time.sleep(wait)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

class _CBState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Opens after *failure_threshold* consecutive failures; half-opens after *recovery_timeout* s."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        name: str = "default",
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self._state = _CBState.CLOSED
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> _CBState:
        with self._lock:
            if self._state is _CBState.OPEN:
                elapsed = time.monotonic() - (self._opened_at or 0)
                if elapsed >= self.recovery_timeout:
                    logger.info("[circuit_breaker:%s] -> HALF_OPEN after %.0fs", self.name, elapsed)
                    self._state = _CBState.HALF_OPEN
            return self._state

    def call(self, fn: Callable, *args, **kwargs):
        state = self.state
        if state is _CBState.OPEN:
            raise RuntimeError(f"[circuit_breaker:{self.name}] OPEN — call rejected")
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        with self._lock:
            self._failures = 0
            if self._state is not _CBState.CLOSED:
                logger.info("[circuit_breaker:%s] -> CLOSED", self.name)
            self._state = _CBState.CLOSED

    def _on_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = _CBState.OPEN
                self._opened_at = time.monotonic()
                logger.error(
                    "[circuit_breaker:%s] OPEN after %d consecutive failures",
                    self.name, self._failures,
                )


# ---------------------------------------------------------------------------
# LangfuseTracer
# ---------------------------------------------------------------------------

@dataclass
class LangfuseTracer:
    """Wraps LLM calls with Langfuse trace/span/score logging.

    Usage::

        tracer = LangfuseTracer()
        result = tracer.trace_llm_call(
            fn=my_llm_fn,
            model="claude-sonnet-4-6",
            input_tokens=500,
            kwargs={"prompt": "..."},
        )
    """

    public_key: Optional[str] = None
    secret_key: Optional[str] = None
    host: Optional[str] = None
    _client: Langfuse = field(init=False, repr=False)
    _circuit_breaker: CircuitBreaker = field(init=False, repr=False)

    def __post_init__(self) -> None:
        kwargs: dict[str, Any] = {}
        if self.public_key:
            kwargs["public_key"] = self.public_key
        if self.secret_key:
            kwargs["secret_key"] = self.secret_key
        if self.host:
            kwargs["host"] = self.host
        self._client = Langfuse(**kwargs)
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60.0,
            name="langfuse",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def trace_llm_call(
        self,
        fn: Callable,
        *,
        model: str,
        input_tokens: int = 0,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        kwargs: Optional[dict] = None,
    ) -> Any:
        """Execute *fn* inside a Langfuse trace and log observability data.

        Returns whatever *fn* returns.
        Raises on failure after retries exhausted.
        """
        kwargs = kwargs or {}
        trace = self._client.trace(
            name=getattr(fn, "__name__", "llm_call"),
            model=model,
            session_id=session_id,
            metadata=metadata or {},
        )

        generation = trace.generation(
            name="llm_generation",
            model=model,
            input=kwargs,
            usage={"input": input_tokens},
        )

        start_ms = time.monotonic() * 1000
        try:
            result = self._circuit_breaker.call(
                self._call_with_retry(fn), **kwargs
            )
        except Exception as exc:
            latency_ms = time.monotonic() * 1000 - start_ms
            generation.end(
                level="ERROR",
                status_message=str(exc),
                usage={"input": input_tokens, "output": 0, "total": input_tokens},
                metadata={"latency_ms": latency_ms},
            )
            trace.update(metadata={"error": str(exc), "latency_ms": latency_ms})
            self._client.flush()
            raise

        latency_ms = time.monotonic() * 1000 - start_ms
        output_tokens = getattr(result, "usage", {}).get("output_tokens", 0) if hasattr(result, "usage") else 0
        tokens_used = input_tokens + output_tokens

        generation.end(
            output=str(result)[:2000],
            usage={
                "input": input_tokens,
                "output": output_tokens,
                "total": tokens_used,
            },
            metadata={"latency_ms": latency_ms},
        )
        trace.score(
            name="latency_ms",
            value=latency_ms,
        )
        trace.update(
            metadata={
                "trace_id": trace.id,
                "model": model,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
            }
        )

        logger.info(
            "[langfuse] trace_id=%s model=%s tokens_used=%d latency_ms=%.1f",
            trace.id, model, tokens_used, latency_ms,
        )
        self._client.flush()
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _call_with_retry(fn: Callable) -> Callable:
        """Return *fn* wrapped with the standard retry policy."""
        return retry(max_attempts=3, backoff=(2.0, 4.0, 8.0))(fn)

    def flush(self) -> None:
        self._client.flush()

    def shutdown(self) -> None:
        self._client.shutdown()
