import logging

from src.infrastructure.adk.institutional_agent import create_institutional_agent
from src.infrastructure.adk.movie_agent import create_movie_catalog_agent
from src.infrastructure.adk.tool_logging import (
    log_after_tool_call,
    log_before_tool_call,
    log_tool_error,
    logger,
)


class FakeTool:
    name = "fake_tool"


def test_log_before_tool_call_emits_info_with_tool_name_and_args(caplog):
    with caplog.at_level(logging.INFO, logger="adk.tools"):
        log_before_tool_call(FakeTool(), {"topic": "quem somos"}, tool_context=None)

    assert any("fake_tool" in r.message and "quem somos" in r.message for r in caplog.records)


def test_log_after_tool_call_emits_info_with_result_summary(caplog):
    with caplog.at_level(logging.INFO, logger="adk.tools"):
        log_after_tool_call(FakeTool(), {}, tool_context=None, tool_response={"title": "Matrix"})

    assert any("fake_tool" in r.message and "Matrix" in r.message for r in caplog.records)


def test_log_after_tool_call_truncates_large_results(caplog):
    huge_result = [{"title": f"Filme {i}"} for i in range(50)]
    with caplog.at_level(logging.INFO, logger="adk.tools"):
        log_after_tool_call(FakeTool(), {}, tool_context=None, tool_response=huge_result)

    message = next(r.message for r in caplog.records)
    assert len(message) < len(repr(huge_result))
    assert message.endswith("…")


def test_log_tool_error_emits_error_level(caplog):
    with caplog.at_level(logging.ERROR, logger="adk.tools"):
        log_tool_error(FakeTool(), {}, tool_context=None, error=RuntimeError("boom"))

    assert any(r.levelno == logging.ERROR and "boom" in r.message for r in caplog.records)


def test_institutional_agent_wires_tool_logging_callbacks():
    agent = create_institutional_agent(model_name="mock-model-gemini-3.6-flash")
    assert agent.before_tool_callback is log_before_tool_call
    assert agent.after_tool_callback is log_after_tool_call
    assert agent.on_tool_error_callback is log_tool_error


def test_movie_catalog_agent_wires_tool_logging_callbacks():
    agent = create_movie_catalog_agent(model_name="mock-model-gemini-3.6-flash")
    assert agent.before_tool_callback is log_before_tool_call
    assert agent.after_tool_callback is log_after_tool_call
    assert agent.on_tool_error_callback is log_tool_error
