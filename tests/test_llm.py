import json
import threading
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest

from polytoken import llm
from polytoken.llm import GenerationAborted, LLMError, NvidiaGenerator, ProtocolError, SlidingWindowLimiter


def completion(usage=True):
    body = {"choices": [{"message": {"content": "సరే"}, "finish_reason": "stop"}]}
    if usage:
        body["usage"] = {"prompt_tokens": 13, "completion_tokens": 4, "total_tokens": 17}
    return body


def make_generator(settings, logger, clock, handler, **kwargs):
    return NvidiaGenerator(
        settings, logger=logger, client=httpx.Client(transport=httpx.MockTransport(handler)),
        limiter=SlidingWindowLimiter(40, clock=clock, sleep=clock.sleep),
        clock=clock, sleep=clock.sleep, jitter=lambda: 0, **kwargs,
    )


def rows(logger):
    return [json.loads(line) for line in (logger.directory / "llm_calls.jsonl").read_text().splitlines()]


def test_saturated_three_minutes_obeys_every_rolling_window(clock):
    limiter = SlidingWindowLimiter(40, clock=clock, sleep=clock.sleep)
    starts = [limiter.acquire() for _ in range(3 * limiter.limit)]
    assert limiter.limit == 38
    for t in starts:
        assert sum(t - 60 < start <= t for start in starts) <= limiter.limit
    for minute in range(3):
        assert sum(60 * minute <= start < 60 * (minute + 1) for start in starts) >= 0.95 * limiter.limit
    assert starts[-1] == 120
    assert limiter.acquire() == 180


def test_window_boundary_and_abort(clock):
    limiter = SlidingWindowLimiter(3, clock=clock, sleep=clock.sleep)
    assert limiter.acquire() == 0
    abort = threading.Event()
    original_sleep = clock.sleep
    def cancel(seconds):
        original_sleep(seconds)
        abort.set()
    limiter._sleep = cancel
    with pytest.raises(GenerationAborted):
        limiter.acquire(abort)
    assert len(limiter._starts) == 1
    clock.now = 59.999
    limiter._sleep = clock.sleep
    assert limiter.acquire() == pytest.approx(60)


def test_concurrent_callers_share_window(clock):
    from concurrent.futures import ThreadPoolExecutor
    limiter = SlidingWindowLimiter(40, clock=clock, sleep=clock.sleep)
    with ThreadPoolExecutor(max_workers=8) as pool:
        starts = sorted(pool.map(lambda _: limiter.acquire(), range(114)))
    for t in starts:
        assert sum(t - 60 < start <= t for start in starts) <= 38


def test_process_wide_limiter_is_shared(settings, logger, monkeypatch):
    monkeypatch.setattr(llm, "_SHARED_LIMITER", None)
    with NvidiaGenerator(settings, logger=logger) as first, NvidiaGenerator(settings, logger=logger) as second:
        assert first.limiter is second.limiter
    with pytest.raises(ValueError, match="NVIDIA_RPM"):
        llm.shared_limiter(20)


def test_429_retry_after_then_success(settings, logger, clock):
    requests = []

    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        return httpx.Response(200, json=completion())

    generate = make_generator(settings, logger, clock, handler, max_tokens=8).generate
    result = generate("private prompt", system_prompt="private system")
    assert result == {"text": "సరే", "usage": completion()["usage"], "latency_s": 3, "model": settings.agent_model, "finish_reason": "stop"}
    assert clock.sleeps == [3]
    body = json.loads(requests[-1].content)
    assert body["max_tokens"] == 8
    assert body["model"] == settings.agent_model
    assert body["messages"] == [{"role": "system", "content": "private system"}, {"role": "user", "content": "private prompt"}]
    assert requests[-1].headers["Authorization"] == "Bearer " + settings.nvidia_api_key
    assert requests[-1].extensions["timeout"]["read"] == 60
    audit = rows(logger)
    assert [r["attempt"] for r in audit] == [1, 2]
    assert [r["ok"] for r in audit] == [False, True]
    assert audit[0]["prompt_tokens"] is None
    assert audit[1]["prompt_tokens"] == 13
    raw = (logger.directory / "llm_calls.jsonl").read_text()
    assert "private prompt" not in raw and "private system" not in raw
    assert settings.nvidia_api_key not in raw


def test_four_503s_fail_after_three_retries(settings, logger, clock):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503, text=settings.nvidia_api_key)

    generator = make_generator(settings, logger, clock, handler)
    with pytest.raises(LLMError, match="HTTP 503") as exc:
        generator.generate("hello")
    assert len(calls) == 4
    assert clock.sleeps == [1, 2, 4]
    assert len(rows(logger)) == 4
    assert all(not row["ok"] for row in rows(logger))
    assert settings.nvidia_api_key not in str(exc.value)


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_other_statuses_never_retry(settings, logger, clock, status):
    generator = make_generator(settings, logger, clock, lambda request: httpx.Response(status))
    with pytest.raises(LLMError):
        generator.generate("hello")
    assert clock.sleeps == []
    assert len(rows(logger)) == 1


def test_missing_usage_remains_missing(settings, logger, clock):
    generator = make_generator(settings, logger, clock, lambda request: httpx.Response(200, json=completion(False)))
    assert generator.generate("hello")["usage"] == {}
    assert rows(logger)[0]["prompt_tokens"] is None
    assert rows(logger)[0]["completion_tokens"] is None


def test_timeout_is_a_logged_failure(settings, logger, clock):
    def timeout(request):
        raise httpx.ReadTimeout("must not echo " + settings.nvidia_api_key)

    with pytest.raises(LLMError, match="ReadTimeout") as exc:
        make_generator(settings, logger, clock, timeout).generate("hello")
    assert settings.nvidia_api_key not in str(exc.value)
    assert rows(logger)[0]["error_class"] == "ReadTimeout"
    assert len(rows(logger)) == 1


@pytest.mark.parametrize("body", [{"error": {"message": "private"}}, {"choices": []}, {"choices": [{"message": {"content": [1]}}]}])
def test_invalid_response_is_logged(settings, logger, clock, body):
    with pytest.raises(ProtocolError):
        make_generator(settings, logger, clock, lambda r: httpx.Response(200, json=body)).generate("hello")
    assert rows(logger)[0]["ok"] is False


def sse(*chunks):
    return "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks) + "data: [DONE]\n\n"


def test_streaming_attachments_and_usage(settings, logger, clock):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, text=sse(
            {"choices": [{"delta": {"content": "హలో"}}]},
            {"choices": [{"delta": {"content": "!"}, "finish_reason": "stop"}]},
            {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 2}},
        ), headers={"Content-Type": "text/event-stream"})

    chunks = []
    attachment = {"type": "image_url", "image_url": {"url": "https://example.com/image.png"}}
    result = make_generator(settings, logger, clock, handler).generate("hello", attachments=[attachment], on_stream=chunks.append)
    assert chunks == ["హలో", "!"]
    assert result["text"] == "హలో!"
    assert result["usage"]["completion_tokens"] == 2
    body = json.loads(requests[0].content)
    assert body["stream"] is True
    assert body["stream_options"] == {"include_usage": True}
    assert body["messages"][0]["content"] == [{"type": "text", "text": "hello"}, attachment]


def test_truncated_stream_is_failure(settings, logger, clock):
    body = sse({"choices": [{"delta": {"content": "partial"}}]})
    with pytest.raises(ProtocolError, match="finish_reason"):
        make_generator(settings, logger, clock, lambda r: httpx.Response(200, text=body)).generate("hello", on_stream=lambda x: None)
    assert rows(logger)[0]["ok"] is False


def test_abort_before_request_never_calls_transport(settings, logger, clock):
    def forbidden(request):
        pytest.fail("Aborted generation reached the network")

    abort = threading.Event()
    abort.set()
    with pytest.raises(GenerationAborted):
        make_generator(settings, logger, clock, forbidden).generate("hello", abort=abort)
    assert rows(logger)[0]["error_class"] == "GenerationAborted"


def test_abort_during_stream(settings, logger, clock):
    abort = threading.Event()
    body = sse({"choices": [{"delta": {"content": "part"}}]})
    with pytest.raises(GenerationAborted):
        make_generator(settings, logger, clock, lambda r: httpx.Response(200, text=body)).generate("hello", on_stream=lambda text: abort.set(), abort=abort)
    assert len(rows(logger)) == 1
    assert rows(logger)[0]["ok"] is False


def test_retry_after_date_and_invalid_values():
    future = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=30))
    assert 28 <= llm._retry_after(future) <= 30
    for value in (None, "junk", "nan", "inf", "-1"):
        assert llm._retry_after(value) == 0


def test_full_conversation_and_finish_reason_preserved(settings, logger, clock):
    requests = []
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, text=sse({'choices': [{'delta': {'content': 'unfinished'}, 'finish_reason': 'length'}]}))
    history = [{'role': 'user', 'content': 'first'}, {'role': 'assistant', 'content': 'reply'}, {'role': 'user', 'content': 'last'}]
    result = make_generator(settings, logger, clock, handler).generate('last', system_prompt='policy', conversation=history,
                                                                      reasoning_effort='low', max_tokens=1024, on_stream=lambda _: None)
    assert requests[0]['messages'] == [{'role': 'system', 'content': 'policy'}] + history
    assert requests[0]['reasoning_effort'] == 'low'
    assert result['finish_reason'] == rows(logger)[0]['finish_reason'] == 'length'
