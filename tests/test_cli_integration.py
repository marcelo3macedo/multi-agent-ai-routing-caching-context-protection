import asyncio
from unittest.mock import MagicMock

from typer.testing import CliRunner

from src.infrastructure.cache.redis_cache import DualModeRedisCache
from src.presentation.cli.main import app, Prompt

runner = CliRunner()


def test_ask_greeting_shows_light_routing_badge_and_zero_tokens():
    """`cli.py ask "Bom dia"` deve ser resolvido pelo roteamento leve (sem ADK)."""
    asyncio.run(DualModeRedisCache().clear())
    result = runner.invoke(app, ["ask", "Bom dia"])

    assert result.exit_code == 0
    assert "Resposta:" in result.output
    assert "SAUDAÇÃO" in result.output
    assert "GREETING" in result.output


def test_repl_shows_cache_hit_badge_on_repeated_greeting(monkeypatch):
    """
    Simula uma sessão REPL enviando a mesma saudação duas vezes: a primeira deve
    cair no roteamento leve (GREETING) e a segunda deve ser servida pelo cache
    (CACHE HIT), confirmando visualmente as duas rotas via badges.
    """
    asyncio.run(DualModeRedisCache().clear())
    inputs = iter(["Bom dia", "Bom dia", "/exit"])
    monkeypatch.setattr(Prompt, "ask", MagicMock(side_effect=lambda *a, **k: next(inputs)))

    result = runner.invoke(app, ["repl"])

    assert result.exit_code == 0
    assert result.output.count("SAUDAÇÃO (ROTEAMENTO LEVE)") == 1
    assert result.output.count("CACHE HIT") == 1


def test_repl_exit_command_ends_session_cleanly(monkeypatch):
    monkeypatch.setattr(Prompt, "ask", MagicMock(return_value="/exit"))

    result = runner.invoke(app, ["repl"])

    assert result.exit_code == 0
    assert "Encerrando REPL" in result.output
