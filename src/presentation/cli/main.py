#!/usr/bin/env python3
"""
CLI Terminal Client - Clean Architecture Presentation Layer

Interface REPL interativa no terminal usando Typer e Rich com exibição de Roteamento de Intenções
e estatísticas de Cache (sub-10ms e economia de tokens).
"""

import sys
import asyncio
import httpx
import json
import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt

from src.application.use_cases.process_chat_message import ProcessChatMessageUseCase
from src.domain.entities.chat_message import ChatMessage
from src.infrastructure.cache.redis_cache import DualModeRedisCache
from src.infrastructure.classifiers.lightweight_classifier import LightweightIntentClassifier
from src.infrastructure.adk.runner import MonolithicAgentRunner
from src.infrastructure.config.settings import Settings

app = typer.Typer(
    help="CLI REPL & Servidor do Sistema de Roteamento e Cache AI",
    add_completion=False
)
console = Console()

def render_header():
    console.print(Panel.fit(
        "[bold cyan]⚡ CLI Terminal - Roteamento de Intenções & Interceptador de Cache[/bold cyan]\n"
        "[dim]Sessão de conversação contínua (Clean Architecture). Digite '/exit' para sair.[/dim]",
        border_style="cyan"
    ))

@app.command()
def repl(
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL do servidor FastAPI (ex: http://127.0.0.1:8000). Se omitido, executa via UseCase local."),
    user_id: str = typer.Option("cli_user", "--user", "-usr", help="ID do usuário para manter sessão."),
    disable_cache: bool = typer.Option(False, "--no-cache", help="Desabilitar interceptador de cache para comparação."),
    disable_routing: bool = typer.Option(False, "--no-routing", help="Desabilitar classificador de intenção para comparação.")
):
    """
    Inicia a interface REPL interativa no terminal.
    """
    asyncio.run(_run_repl(url, user_id, enable_cache=not disable_cache, enable_routing=not disable_routing))

async def _run_repl(url: Optional[str], user_id: str, enable_cache: bool, enable_routing: bool):
    render_header()
    
    mode_str = f"API FastAPI ([bold]{url}[/bold])" if url else "Local Clean Arch UseCase"
    console.print(f"[green]✓ Modo de Operação: [bold]{mode_str}[/bold][/green]")
    console.print(f"[dim]⚡ Cache Habilitado: {enable_cache} | 🎯 Roteamento Habilitado: {enable_routing}[/dim]\n")

    # Iniciliza componentes se for execução local
    use_case = None
    if not url:
        cache_repo = DualModeRedisCache()
        classifier = LightweightIntentClassifier()
        runner = MonolithicAgentRunner()
        use_case = ProcessChatMessageUseCase(cache_repo=cache_repo, classifier=classifier, agent_runner=runner)

    session_id = None
    client = httpx.AsyncClient(base_url=url, timeout=30.0) if url else None

    try:
        while True:
            try:
                user_input = Prompt.ask("\n[bold magenta]Você[/bold magenta]").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Sessão encerrada pelo usuário.[/dim]")
                break

            if not user_input:
                continue

            if user_input.lower() in ["/exit", "/quit", "exit", "quit"]:
                console.print("[yellow]Encerrando REPL... Até logo![/yellow]")
                break

            if user_input.lower() == "/stats":
                if not url and use_case:
                    stats = await use_case.cache_repo.get_stats()
                    console.print(Panel(json.dumps(stats, indent=2), title="Cache Stats", border_style="blue"))
                continue

            if user_input.lower() == "/clear":
                console.clear()
                render_header()
                continue

            console.print("[dim]⚡ Verificando Cache / Classificando Intenção (Gemini 1.5 Flash 8B)...[/dim]")

            response_text = ""
            metrics_data = None

            if url and client:
                try:
                    payload = {
                        "message": user_input,
                        "user_id": user_id,
                        "session_id": session_id,
                        "enable_cache": enable_cache,
                        "enable_routing": enable_routing
                    }
                    resp = await client.post("/api/v1/chat", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    response_text = data["response"]
                    session_id = data["session_id"]
                    metrics_data = data["metrics"]
                except Exception as e:
                    console.print(f"[red]Erro ao comunicar com o servidor FastAPI: {e}[/red]")
                    continue
            else:
                msg = ChatMessage(content=user_input, user_id=user_id, session_id=session_id)
                chat_res = await use_case.execute(msg, enable_cache=enable_cache, enable_routing=enable_routing)
                session_id = chat_res.session_id
                response_text = chat_res.text
                m = chat_res.metrics
                metrics_data = {
                    "latency_ms": round(m.latency_ms, 2),
                    "prompt_tokens": m.prompt_tokens,
                    "completion_tokens": m.completion_tokens,
                    "total_tokens": m.total_tokens,
                    "intent": m.intent,
                    "cache_status": m.cache_status.value if hasattr(m.cache_status, "value") else str(m.cache_status),
                    "is_mock": m.is_mock,
                    "tokens_saved": m.tokens_saved,
                    "problem_tags": m.problem_tags
                }

            # Renderiza resposta do Agente
            console.print(Panel(
                Text(response_text, style="bold white"),
                title="[bold cyan]Resposta do Agente[/bold cyan]",
                border_style="cyan"
            ))

            # Exibe painel de métricas e performance de otimização
            if metrics_data:
                lat = metrics_data["latency_ms"]
                pt = metrics_data["prompt_tokens"]
                ct = metrics_data["completion_tokens"]
                tt = metrics_data["total_tokens"]
                intent = metrics_data.get("intent", "UNKNOWN")
                cache_st = metrics_data.get("cache_status", "MISS")

                metrics_str = (
                    f"⏱️  Latência: [bold yellow]{lat} ms[/bold yellow]  |  "
                    f"🎯 Intenção: [bold green]{intent}[/bold green]  |  "
                    f"📦 Cache: [bold blue]{cache_st}[/bold blue]  |  "
                    f"📊 ADK Tokens: [bold cyan]{tt}[/bold cyan]"
                )
                console.print(metrics_str)

                # Destaca quando o cache ou roteamento otimiza a latência
                if cache_st in ("HIT_EXACT", "HIT_SEMANTIC") or intent == "GREETING":
                    console.print(
                        f"[bold green]✨ OTIMIZAÇÃO ATIVADA:[/bold green] Resposta retornada em "
                        f"[bold yellow]{lat}ms[/bold yellow] ([bold green]0 tokens[/bold green] enviados ao ADK!)."
                    )
    finally:
        if client:
            await client.aclose()

@app.command()
def ask(
    message: str = typer.Argument(..., help="Mensagem para enviar ao agente"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL do servidor FastAPI")
):
    """
    Envia uma única mensagem e exibe o resultado otimizado.
    """
    async def _ask():
        if url:
            async with httpx.AsyncClient(base_url=url, timeout=30.0) as client:
                resp = await client.post("/api/v1/chat", json={"message": message})
                data = resp.json()
                console.print(f"[bold cyan]Resposta:[/bold cyan] {data['response']}")
                console.print(f"[dim]Métricas: {data['metrics']}[/dim]")
        else:
            cache_repo = DualModeRedisCache()
            classifier = LightweightIntentClassifier()
            runner = MonolithicAgentRunner()
            use_case = ProcessChatMessageUseCase(cache_repo=cache_repo, classifier=classifier, agent_runner=runner)
            chat_res = await use_case.execute(ChatMessage(content=message))
            console.print(f"[bold cyan]Resposta:[/bold cyan] {chat_res.text}")
            console.print(f"[dim]Latência: {chat_res.metrics.latency_ms:.2f}ms | Intenção: {chat_res.metrics.intent} | Cache: {chat_res.metrics.cache_status} | ADK Tokens: {chat_res.metrics.total_tokens}[/dim]")

    asyncio.run(_ask())

@app.command()
def server(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host do servidor FastAPI"),
    port: int = typer.Option(8000, "--port", "-p", help="Porta do servidor FastAPI")
):
    """
    Inicia o servidor FastAPI (Uvicorn).
    """
    import uvicorn
    console.print(f"[bold green]Iniciando servidor FastAPI Clean Architecture em http://{host}:{port}...[/bold green]")
    uvicorn.run("src.presentation.api.server:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    if len(sys.argv) == 1:
        app(["repl"])
    else:
        app()
