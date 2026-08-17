import logging
from typing import Any, Dict

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

# Namespace raiz compartilhado por todos os loggers internos do projeto relacionados
# ao ADK (ex: "adk.tools", "adk.runner") — configurar/silenciar "adk" propaga para
# todos os filhos de uma vez.
_ADK_LOGGER_NAME = "adk"
logger = logging.getLogger("adk.tools")


def log_before_tool_call(tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext) -> None:
    """Callback ADK `before_tool_callback`: loga toda chamada de tool antes da execução."""
    logger.info("🔧 tool_call=%s args=%s", tool.name, args)
    return None


def log_after_tool_call(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Any
) -> None:
    """Callback ADK `after_tool_callback`: loga o resultado (resumido) de cada chamada de tool."""
    summary = repr(tool_response)
    if len(summary) > 200:
        summary = summary[:200] + "…"

    logger.info("✅ tool_result=%s result=%s", tool.name, summary)
    return None


def log_tool_error(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, error: Exception
) -> None:
    """Callback ADK `on_tool_error_callback`: loga falhas de execução de tool."""
    logger.error("❌ tool_error=%s args=%s error=%s", tool.name, args, error)
    return None


def configure_tool_logging(level: int = logging.INFO, use_rich: bool = True) -> None:
    """
    Configura o namespace `adk` (chamadas de tool em `adk.tools`, erros de execução
    em `adk.runner`, etc.) para exibir uma linha por evento.

    Usa RichHandler (quando disponível) para saída colorida e legível no terminal;
    cai para um handler padrão de `logging` caso contrário.
    """
    adk_logger = logging.getLogger(_ADK_LOGGER_NAME)
    adk_logger.setLevel(level)
    adk_logger.propagate = False
    if adk_logger.handlers:
        return

    if use_rich:
        try:
            from rich.logging import RichHandler

            handler = RichHandler(show_time=False, show_path=False, markup=False)
            handler.setFormatter(logging.Formatter("%(message)s"))
            adk_logger.addHandler(handler)
            return
        except ImportError:
            pass

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    adk_logger.addHandler(handler)


def silence_tool_logging() -> None:
    """
    Garante que os logs do namespace `adk` (chamadas de tool, erros de execução do
    ADK) NÃO apareçam nesta saída (ex: CLI interativo) — eles devem ser visíveis
    apenas onde `configure_tool_logging` for chamado explicitamente (ex:
    processo/container do servidor).
    """
    adk_logger = logging.getLogger(_ADK_LOGGER_NAME)
    adk_logger.setLevel(logging.CRITICAL + 1)
    adk_logger.propagate = False
    if not adk_logger.handlers:
        adk_logger.addHandler(logging.NullHandler())


def silence_adk_library_logging() -> None:
    """
    Silencia os logs INTERNOS da biblioteca google-adk (namespace `google_adk`),
    que por padrão imprime tracebacks completos (ex: falhas de sub-agente, erros
    de LLM) diretamente no stderr. O CLI trata esses erros e mostra uma mensagem
    amigável ao usuário (ver `error_handling.py`); o traceback bruto deve ficar
    restrito aos logs do processo/container do servidor.
    """
    google_adk_logger = logging.getLogger("google_adk")
    google_adk_logger.setLevel(logging.CRITICAL + 1)
    google_adk_logger.propagate = False
    if not google_adk_logger.handlers:
        google_adk_logger.addHandler(logging.NullHandler())
