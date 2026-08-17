import logging

from google.genai import errors as genai_errors

logger = logging.getLogger("adk.runner")

# Códigos HTTP tipicamente transitórios (sobrecarga/rate-limit) do provedor do modelo.
_TRANSIENT_API_CODES = {429, 500, 502, 503, 504}

_BUSY_MESSAGE = (
    "🎬 Nosso sistema de recomendações está passando por um pico de demanda no momento. "
    "Pode tentar novamente em alguns instantes?"
)
_GENERIC_MESSAGE = (
    "Desculpe, tive um problema técnico ao processar seu pedido. Pode tentar novamente, "
    "por favor?"
)


def build_friendly_error_message(error: Exception) -> str:
    """
    Converte uma exceção técnica do ADK/Gemini (ex: 503 UNAVAILABLE, timeouts,
    falhas de sub-agente) numa mensagem amigável e no tom da TechCorp Solutions,
    sem expor stack traces ou payloads de erro brutos ao usuário.
    """
    if isinstance(error, genai_errors.APIError) and error.code in _TRANSIENT_API_CODES:
        return _BUSY_MESSAGE
    return _GENERIC_MESSAGE


def log_adk_execution_error(error: Exception) -> None:
    """Loga o erro técnico completo — visível apenas onde o logger `adk` for configurado."""
    logger.error("adk_execution_error=%r", error, exc_info=error)
