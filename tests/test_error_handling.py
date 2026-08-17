import logging

import pytest
from google.genai import errors as genai_errors

from src.infrastructure.adk.error_handling import build_friendly_error_message, log_adk_execution_error
from src.infrastructure.adk.runner import MonolithicAgentRunner


def _api_error(code: int, message: str = "boom") -> genai_errors.APIError:
    return genai_errors.APIError(code, {"error": {"code": code, "message": message, "status": "X"}})


@pytest.mark.parametrize("code", [429, 500, 502, 503, 504])
def test_transient_api_errors_get_the_busy_message(code):
    message = build_friendly_error_message(_api_error(code, "This model is currently experiencing high demand"))
    assert "demanda" in message.lower()
    assert "high demand" not in message
    assert str(code) not in message


def test_non_transient_api_error_gets_generic_message():
    message = build_friendly_error_message(_api_error(400, "invalid argument"))
    assert "problema técnico" in message.lower()
    assert "invalid argument" not in message


def test_unexpected_exception_gets_generic_message_without_leaking_details():
    message = build_friendly_error_message(RuntimeError("some internal stack trace detail"))
    assert "problema técnico" in message.lower()
    assert "stack trace" not in message


def test_log_adk_execution_error_emits_error_level_with_exc_info(caplog):
    with caplog.at_level(logging.ERROR, logger="adk.runner"):
        log_adk_execution_error(_api_error(503, "high demand"))

    assert any(r.levelno == logging.ERROR and r.exc_info for r in caplog.records)


@pytest.mark.asyncio
async def test_stream_query_yields_friendly_message_instead_of_raw_exception(monkeypatch):
    """
    Reproduz o cenário relatado: o ADK falha internamente (ex: 503 UNAVAILABLE do
    Gemini) e o usuário via a exceção crua na resposta. Após o tratamento, a
    resposta final deve ser a mensagem amigável, sem o payload técnico do erro.
    """
    runner_instance = MonolithicAgentRunner()

    async def fake_run_async(*args, **kwargs):
        if False:  # pragma: no cover - torna a função um async generator
            yield
        raise _api_error(503, "This model is currently experiencing high demand")

    monkeypatch.setattr(runner_instance.runner, "run_async", fake_run_async)

    events = [event async for event in runner_instance.stream_query("Homem aranha")]
    complete_event = next(e for e in events if e["type"] == "complete")

    assert "demanda" in complete_event["text"].lower()
    assert "UNAVAILABLE" not in complete_event["text"]
    assert "503" not in complete_event["text"]
