from typing import Tuple

CACHE_HIT_STATUSES = ("HIT_EXACT", "HIT_SEMANTIC")

# (label, estilo Rich) por rota de atendimento. A ordem de avaliação em
# `resolve_routing_badge` prioriza cache > roteamento leve > sub-agentes > genérico.
_BADGES = {
    "CACHE_HIT": ("⚡ CACHE HIT", "bold black on green"),
    "GREETING": ("💬 SAUDAÇÃO (ROTEAMENTO LEVE)", "bold black on cyan"),
    "INSTITUTIONAL": ("🏢 INSTITUCIONAL → InstitutionalAgent", "bold white on blue"),
    "MOVIE_SEARCH": ("🎬 FILMES → MovieCatalogAgent (TMDB)", "bold white on magenta"),
    "GENERIC": ("🤖 ADK GENÉRICO", "bold white on grey37"),
}


def resolve_routing_badge(intent: str, cache_status: str) -> Tuple[str, str]:
    """
    Resolve o badge de roteamento (label, estilo Rich) para uma resposta,
    dado o `intent` classificado e o `cache_status` da requisição.
    """
    if cache_status in CACHE_HIT_STATUSES:
        return _BADGES["CACHE_HIT"]
    if intent in ("GREETING", "INSTITUTIONAL", "MOVIE_SEARCH"):
        return _BADGES[intent]
    return _BADGES["GENERIC"]


def render_routing_badge(intent: str, cache_status: str) -> str:
    """Renderiza o badge de roteamento como markup Rich pronto para `console.print`."""
    label, style = resolve_routing_badge(intent, cache_status)
    return f"[{style}] {label} [/{style}]"


def render_metrics_line(metrics_data: dict) -> str:
    """Renderiza a linha de métricas (latência, intenção, cache, tokens) em markup Rich."""
    lat = metrics_data.get("latency_ms", 0.0)
    tt = metrics_data.get("total_tokens", 0)
    intent = metrics_data.get("intent", "UNKNOWN")
    cache_st = metrics_data.get("cache_status", "MISS")

    return (
        f"⏱️  Latência: [bold yellow]{lat} ms[/bold yellow]  |  "
        f"🎯 Intenção: [bold green]{intent}[/bold green]  |  "
        f"📦 Cache: [bold blue]{cache_st}[/bold blue]  |  "
        f"📊 ADK Tokens: [bold cyan]{tt}[/bold cyan]"
    )
