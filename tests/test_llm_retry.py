from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import httpx
import pytest
from google.genai import types
from google.genai.errors import ClientError, ServerError

import crew_builder


def _make_gemini_503_error(headers: dict[str, str] | None = None) -> ServerError:
    payload = {
        "error": {
            "code": 503,
            "message": (
                "This model is currently experiencing high demand. "
                "Spikes in demand are usually temporary. Please try again later."
            ),
            "status": "UNAVAILABLE",
        }
    }
    resp = httpx.Response(503, json=payload, headers=headers or {})
    return ServerError(503, payload, resp)


def _make_gemini_401_error() -> ClientError:
    payload = {
        "error": {
            "code": 401,
            "message": "API key not valid. Please pass a valid API key.",
            "status": "UNAUTHENTICATED",
        }
    }
    resp = httpx.Response(401, json=payload)
    return ClientError(401, payload, resp)


def _make_gemini_text_response(text: str) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=text)],
                ),
                finish_reason=types.FinishReason.STOP,
            )
        ]
    )


def test_make_llm_retries_gemini_503_unavailable_and_succeeds(monkeypatch):
    monkeypatch.setenv("MODEL", "gemini/gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("LLM_MAX_ATTEMPTS", "4")
    monkeypatch.setenv("LLM_RETRY_INITIAL_DELAY", "1.5")

    llm = crew_builder._make_llm()
    client = llm._get_sync_client()

    calls = 0

    def fake_generate_content(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise _make_gemini_503_error()
        return _make_gemini_text_response('{"project_title": "Recovered"}')

    sleeps: list[float] = []
    monkeypatch.setattr(client.models, "generate_content", fake_generate_content)
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    result = llm.call("Generate spec")

    assert '{"project_title": "Recovered"}' in result
    assert calls == 3
    assert len(sleeps) == 2
    assert sleeps[0] > 0
    assert sleeps[1] > sleeps[0]


def test_make_llm_does_not_retry_non_transient_401_error(monkeypatch):
    monkeypatch.setenv("MODEL", "gemini/gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "bad-key")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("LLM_MAX_ATTEMPTS", "5")

    llm = crew_builder._make_llm()
    client = llm._get_sync_client()

    calls = 0

    def fake_generate_content(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise _make_gemini_401_error()

    sleeps: list[float] = []
    monkeypatch.setattr(client.models, "generate_content", fake_generate_content)
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    with pytest.raises(ClientError):
        llm.call("Generate spec")

    assert calls == 1
    assert sleeps == []


def test_end_to_end_stage_stops_at_max_attempts_without_multiplying_retries(monkeypatch):
    monkeypatch.setenv("MODEL", "gemini/gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("LLM_MAX_ATTEMPTS", "3")

    calls = 0
    real_make_llm = crew_builder._make_llm

    def instrumented_make_llm():
        llm = real_make_llm()
        client = llm._get_sync_client()

        def always_503(*args, **kwargs):
            nonlocal calls
            calls += 1
            raise _make_gemini_503_error()

        monkeypatch.setattr(client.models, "generate_content", always_503)
        return llm

    sleeps: list[float] = []
    monkeypatch.setattr(crew_builder, "_make_llm", instrumented_make_llm)
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    with pytest.raises(ServerError):
        crew_builder.run_planning_stage("Build a personal portfolio")

    # Exactly 3 total attempts (1 initial + 2 retries), NOT 1 and NOT 3*3=9
    assert calls == 3
    assert len(sleeps) == 2


def test_stage_kickoff_retries_transient_503_raised_at_crew_boundary(monkeypatch):
    monkeypatch.setenv("MODEL", "gemini/gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("LLM_MAX_ATTEMPTS", "3")

    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    attempts = 0

    def flaky_kickoff(self, *args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError(
                "503 UNAVAILABLE. {'error': {'code': 503, 'message': "
                "'This model is currently experiencing high demand.', 'status': 'UNAVAILABLE'}}"
            )
        return '{"project_title": "Boundary Recovered"}'

    with patch.object(crew_builder.Crew, "kickoff", flaky_kickoff):
        spec = crew_builder.run_planning_stage("Build a SaaS page")

    assert spec == {"project_title": "Boundary Recovered"}
    assert attempts == 2
    assert len(sleeps) == 1


def test_async_acall_retries_transient_503_unavailable(monkeypatch):
    monkeypatch.setenv("MODEL", "gemini/gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("LLM_MAX_ATTEMPTS", "3")

    llm = crew_builder._make_llm()
    calls = 0

    async def fake_ahandle_completion(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _make_gemini_503_error()
        return "async recovered"

    async_sleeps: list[float] = []

    async def fake_async_sleep(delay: float) -> None:
        async_sleeps.append(delay)

    monkeypatch.setattr(llm, "_ahandle_completion", fake_ahandle_completion)
    monkeypatch.setattr(asyncio, "sleep", fake_async_sleep)

    result = asyncio.run(llm.acall("Hello async"))

    assert result == "async recovered"
    assert calls == 2
    assert len(async_sleeps) == 1


def test_retry_honors_retry_after_header(monkeypatch):
    monkeypatch.setenv("MODEL", "gemini/gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("LLM_MAX_ATTEMPTS", "3")

    llm = crew_builder._make_llm()
    client = llm._get_sync_client()

    calls = 0

    def fake_generate_content(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _make_gemini_503_error(headers={"Retry-After": "7"})
        return _make_gemini_text_response("ok")

    sleeps: list[float] = []
    monkeypatch.setattr(client.models, "generate_content", fake_generate_content)
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    assert llm.call("Ping") == "ok"
    assert calls == 2
    assert sleeps == [7.0]


def test_end_to_end_stage_recovers_from_503_in_call_llm_and_parse(monkeypatch):
    monkeypatch.setenv("MODEL", "gemini/gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("LLM_MAX_ATTEMPTS", "4")

    calls = 0
    real_make_llm = crew_builder._make_llm

    def instrumented_make_llm():
        llm = real_make_llm()
        client = llm._get_sync_client()

        def flaky_503_then_json(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls < 3:
                raise _make_gemini_503_error()
            return _make_gemini_text_response(
                '{"project_title": "Recovered Portfolio", "sections": []}'
            )

        monkeypatch.setattr(client.models, "generate_content", flaky_503_then_json)
        return llm

    sleeps: list[float] = []
    monkeypatch.setattr(crew_builder, "_make_llm", instrumented_make_llm)
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    spec = crew_builder.run_planning_stage("Build a portfolio")

    assert spec["project_title"] == "Recovered Portfolio"
    assert calls == 3
    assert len(sleeps) == 2


def test_non_http_value_error_mentioning_number_503_is_not_retried(monkeypatch):
    monkeypatch.setenv("LLM_MAX_ATTEMPTS", "4")
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    calls = 0

    def parse_failure():
        nonlocal calls
        calls += 1
        raise ValueError("Invalid JSON syntax near line 503 column 8")

    with pytest.raises(ValueError, match="line 503"):
        crew_builder.run_with_llm_retry(parse_failure)

    assert calls == 1
    assert sleeps == []

