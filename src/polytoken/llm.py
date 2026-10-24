"""The single injectable Nemotron generator; no agent loop lives here."""

from __future__ import annotations

import hashlib
import json
import math
import random
import threading
import time
from collections import deque
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable

import httpx

from .config import Settings
from .logs import JsonlLogger


class LLMError(RuntimeError):
    """A failed completion, with a safe message and an audited attempt."""


class GenerationAborted(LLMError):
    pass


class ProtocolError(LLMError):
    pass


def _check_abort(abort) -> None:
    if abort is not None and (abort.is_set() if hasattr(abort, "is_set") else abort()):
        raise GenerationAborted("Generation aborted")


def _wait(seconds: float, sleep: Callable, abort=None) -> None:
    _check_abort(abort)
    if abort is None:
        sleep(seconds)
        return
    while seconds > 0:
        step = min(seconds, 0.1)
        sleep(step)
        seconds -= step
        _check_abort(abort)


class SlidingWindowLimiter:
    """At most RPM minus two starts in any half-open rolling 60-second window."""

    def __init__(self, rpm: float, *, clock=time.monotonic, sleep=time.sleep):
        if not math.isfinite(rpm) or rpm < 3 or int(rpm) != rpm:
            raise ValueError("NVIDIA_RPM must be an integer of at least 3")
        self.rpm = rpm
        self.limit = int(rpm) - 2
        self._starts = deque()
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()

    def acquire(self, abort=None) -> float:
        while True:
            _check_abort(abort)
            with self._lock:
                _check_abort(abort)
                now = self._clock()
                while self._starts and self._starts[0] <= now - 60.0:
                    self._starts.popleft()
                if len(self._starts) < self.limit:
                    self._starts.append(now)
                    return now
                delay = max(0.0, self._starts[0] + 60.0 - now)
            _wait(delay, self._sleep, abort)


_SHARED_LOCK = threading.Lock()
_SHARED_LIMITER: SlidingWindowLimiter | None = None


def shared_limiter(rpm: float) -> SlidingWindowLimiter:
    global _SHARED_LIMITER
    with _SHARED_LOCK:
        if _SHARED_LIMITER is None:
            _SHARED_LIMITER = SlidingWindowLimiter(rpm)
        elif _SHARED_LIMITER.rpm != rpm:
            raise ValueError("NVIDIA_RPM cannot change within a process")
        return _SHARED_LIMITER


def _retry_after(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            seconds = (when - datetime.now(timezone.utc)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return 0.0
    return max(0.0, seconds) if math.isfinite(seconds) else 0.0


class NvidiaGenerator:
    """Inject `generator.generate` wherever model text is needed.

    Every physical HTTP attempt consumes a rate-limit permit and writes a row.
    The default path uses JSON completions; on_stream opts into real SSE chunks.
    Attachments are OpenAI-compatible content parts, never implicit local files.
    """

    def __init__(
        self, settings: Settings, *, logger: JsonlLogger | None = None,
        client: httpx.Client | None = None, limiter: SlidingWindowLimiter | None = None,
        max_tokens: int = 512, timeout_s: float = 60.0,
        clock=time.monotonic, sleep=time.sleep, jitter=random.random,
    ) -> None:
        if max_tokens <= 0 or not math.isfinite(timeout_s) or timeout_s <= 0:
            raise ValueError("max_tokens and timeout_s must be positive")
        self.settings = settings
        self.logger = logger or JsonlLogger(secrets=settings.secrets)
        self.logger.add_secrets(*settings.secrets)
        self.limiter = limiter or shared_limiter(settings.nvidia_rpm)
        self.max_tokens = max_tokens
        self.timeout = httpx.Timeout(timeout_s, connect=min(10.0, timeout_s))
        self._client = client or httpx.Client()
        self._owns_client = client is None
        self._clock, self._sleep, self._jitter = clock, sleep, jitter

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def generate(self, prompt, system_prompt=None, attachments=None, on_stream=None, abort=None,
                 *, model=None, temperature=None, before_attempt=None, remaining=None,
                 enable_thinking=None) -> dict:
        messages = []
        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})
        content = [{"type": "text", "text": prompt}, *attachments] if attachments else prompt
        messages.append({"role": "user", "content": content})
        body = {
            "model": model or self.settings.agent_model, "messages": messages,
            "max_tokens": self.max_tokens, "stream": on_stream is not None,
        }
        if temperature is not None:
            body["temperature"] = temperature
        if enable_thinking is not None:
            body["chat_template_kwargs"] = {"enable_thinking": bool(enable_thinking)}
        if on_stream is not None:
            body["stream_options"] = {"include_usage": True}
        metadata = {
            "model": body["model"], "prompt_length": len(prompt),
            "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12],
            "system_prompt_length": len(system_prompt or ""),
            "attachments_count": len(attachments or []),
            "enable_thinking": enable_thinking,
        }
        total_start = self._clock()
        for attempt in range(1, 5):  # One initial request and at most three retries.
            usage = {}
            first_token = None
            attempted = False
            start = self._clock()
            try:
                self.limiter.acquire(abort)
                _check_abort(abort)
                if before_attempt:
                    before_attempt()
                start = self._clock()
                attempted = True
                with self._client.stream(
                    "POST", self.settings.nvidia_base_url + "/chat/completions",
                    headers={"Authorization": "Bearer " + self.settings.nvidia_api_key},
                    json=body, timeout=min(self.timeout.read, max(.01, remaining())) if remaining else self.timeout,
                ) as response:
                    response.raise_for_status()
                    if on_stream is not None:
                        def receive(text):
                            nonlocal first_token
                            if first_token is None:
                                first_token = self._clock()
                            on_stream(text)
                        text, usage = self._read_stream(response, receive, abort)
                    else:
                        response.read()
                        _check_abort(abort)
                        data = response.json()
                        if data.get("error") or not data.get("choices"):
                            raise ProtocolError("Completion response has no valid choices")
                        text = data["choices"][0]["message"].get("content") or ""
                        if not isinstance(text, str):
                            raise ProtocolError("Completion content is not text")
                        usage = data.get("usage") or {}
                if not isinstance(usage, dict):
                    raise ProtocolError("Completion usage is not an object")
                self._log(metadata, usage, start, attempt, True, None, attempted=attempted)
                result = {"text": text, "usage": usage,
                          "latency_s": self._clock() - total_start, "model": body["model"]}
                if on_stream is not None:
                    result.update(request_latency_s=self._clock() - start,
                                  ttft_s=first_token - start if first_token is not None else None)
                return result
            except Exception as exc:
                error_detail = None
                if isinstance(exc, httpx.HTTPStatusError):
                    try:
                        exc.response.read()
                        error_detail = self.logger.redact(exc.response.text)[:500]
                    except Exception:
                        pass
                    self.logger.write('llm_errors', 'http_error', **metadata,
                                      status_code=exc.response.status_code, detail=error_detail,
                                      attempt=attempt, attempted=attempted, ok=False)
                self._log(metadata, usage, start, attempt, False, type(exc).__name__, attempted=attempted)
                retryable = isinstance(exc, httpx.HTTPStatusError) and (
                    exc.response.status_code == 429 or 500 <= exc.response.status_code <= 599
                )
                if retryable and attempt < 4:
                    delay = max(2 ** (attempt - 1) + self._jitter(), _retry_after(exc.response.headers.get("Retry-After")))
                    try:
                        _wait(delay, self._sleep, abort)
                    except GenerationAborted:
                        self.logger.write("llm_calls", "generation_aborted", **metadata,
                                          attempt=attempt, ok=False, error_class="GenerationAborted",
                                          prompt_tokens=None, completion_tokens=None,
                                          latency_s=self._clock() - total_start)
                        raise
                    continue
                if isinstance(exc, LLMError):
                    raise
                status = f" HTTP {exc.response.status_code}" if isinstance(exc, httpx.HTTPStatusError) else ""
                raise LLMError(f"NVIDIA completion failed:{status} {type(exc).__name__}" +
                               (f": {error_detail}" if error_detail else "")) from None
        raise AssertionError("unreachable")

    def _log(self, metadata, usage, start, attempt, ok, error_class, *, attempted=True):
        self.logger.write(
            "llm_calls", "completion", **metadata,
            prompt_tokens=usage.get("prompt_tokens") if isinstance(usage, dict) else None,
            completion_tokens=usage.get("completion_tokens") if isinstance(usage, dict) else None,
            latency_s=self._clock() - start, attempt=attempt, attempted=attempted, ok=ok, error_class=error_class,
        )

    @staticmethod
    def _read_stream(response, on_stream, abort):
        parts, usage = [], {}
        finished = False
        for line in response.iter_lines():
            _check_abort(abort)
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            chunk = json.loads(payload)
            if chunk.get("error"):
                raise ProtocolError("NVIDIA reported an error in the stream")
            if chunk.get("usage"):
                usage = chunk["usage"]
            for choice in chunk.get("choices") or []:
                text = (choice.get("delta") or {}).get("content") or ""
                if not isinstance(text, str):
                    raise ProtocolError("Stream content is not text")
                if text:
                    parts.append(text)
                    on_stream(text)
                    _check_abort(abort)
                if choice.get("finish_reason"):
                    finished = True
        if not finished:
            raise ProtocolError("NVIDIA stream ended without finish_reason")
        return "".join(parts), usage
