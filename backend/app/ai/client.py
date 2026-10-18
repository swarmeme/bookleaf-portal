"""Thin wrapper around the Gemini API.

Everything the rest of the app needs to know about the LLM provider lives here:
- one `generate()` call returning text,
- a request timeout,
- retries with backoff for rate limits (429) and server errors (5xx) only,
- a circuit breaker: after repeated failures, calls fail fast for a cooldown
  period instead of making every ticket wait on a dead API.

Any failure surfaces as `AIUnavailableError`, which callers treat as "use the
fallback path". Swapping providers means writing another class with the same
`generate()` signature.
"""

import logging
import random
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_FAILURES_BEFORE_COOLDOWN = 3


class AIUnavailableError(Exception):
    """The AI could not produce a usable answer. `reason` is short and safe to show admins."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str


class LLMClient(Protocol):
    def generate(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        max_output_tokens: int,
        temperature: float,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResult: ...


class _CircuitBreaker:
    def __init__(self, cooldown_seconds: int):
        self._cooldown = cooldown_seconds
        self._failures = 0
        self._open_until = 0.0
        self._lock = threading.Lock()

    def check(self) -> None:
        with self._lock:
            if time.monotonic() < self._open_until:
                raise AIUnavailableError("AI service is cooling down after repeated failures")

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= _FAILURES_BEFORE_COOLDOWN:
                self._open_until = time.monotonic() + self._cooldown
                self._failures = 0
                logger.warning("AI circuit breaker open for %ss", self._cooldown)


class GeminiClient:
    def __init__(self, settings: Settings):
        self._client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.ai_timeout_seconds * 1000)),
        )
        self._max_retries = settings.ai_max_retries
        self._breaker = _CircuitBreaker(settings.ai_cooldown_seconds)

    def generate(
        self,
        *,
        model: str,
        system: str,
        prompt: str,
        max_output_tokens: int,
        temperature: float,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResult:
        self._breaker.check()
        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            response_mime_type="application/json" if response_schema else None,
            response_schema=response_schema,
            # Gemini 2.5 models "think" by default, which adds hidden output tokens and
            # latency. These tasks are well specified, so turn it off.
            thinking_config=types.ThinkingConfig(thinking_budget=0) if model.startswith("gemini-2.5") else None,
        )

        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.models.generate_content(model=model, contents=prompt, config=config)
                text = response.text
                if not text:
                    # Usually a safety block or the token limit being hit before any text.
                    raise AIUnavailableError("AI returned an empty response")
                self._breaker.record_success()
                return LLMResult(text=text.strip(), model=model)
            except errors.APIError as exc:
                retryable = exc.code == 429 or exc.code >= 500
                if retryable and attempt < self._max_retries:
                    _backoff(attempt)
                    continue
                reason = "AI rate limit reached" if exc.code == 429 else f"AI service error ({exc.code})"
                failure = AIUnavailableError(reason)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt < self._max_retries:
                    _backoff(attempt)
                    continue
                failure = AIUnavailableError(f"AI service unreachable ({type(exc).__name__})")
            except AIUnavailableError as exc:
                failure = exc
            except Exception as exc:  # SDK bugs, unexpected payloads: still degrade, never crash a request
                logger.exception("Unexpected error calling Gemini")
                failure = AIUnavailableError(f"Unexpected AI error ({type(exc).__name__})")

            self._breaker.record_failure()
            logger.warning("Gemini call failed (%s): %s", model, failure.reason)
            raise failure

        raise AssertionError("unreachable")


def _backoff(attempt: int) -> None:
    # 1s, 2s, ... plus jitter so concurrent retries don't arrive together.
    time.sleep(2**attempt + random.uniform(0, 0.5))



@lru_cache
def _gemini_client() -> GeminiClient:
    return GeminiClient(get_settings())


def get_llm() -> LLMClient | None:
    """The configured LLM client, or None when no API key is set (fallback mode)."""
    return _gemini_client() if get_settings().ai_enabled else None
