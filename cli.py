#!/usr/bin/env python3
"""
CLI Terminal Client - Agente Monolítico (Google ADK) & Servidor FastAPI

Interface REPL interativa no terminal usando Typer e Rich para conversação contínua,
exibição de streaming de respostas e diagnóstico de consumo de tokens e latência.
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
from rich.live import Live

from src.runner import MonolithicAgentRunner
from src.config import Config

app = typer.Typer(
    help="CLI REPL & Servidor do Agente Monolítico Google ADK",
    add_completion=False
)
console = Console()

def render_header():
    console.print(Panel.fit(
        "[bold cyan]🤖 Cliente Terminal CLI - Agente Monolítico Google ADK[/bold cyan]\n"
        "[dim]Sessão de conversação contínua (REPL). Digite '/exit' para sair ou '/help' para ajuda.[/dim]",
        border_style="cyan"
    ))

@app.command()
def repl(
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL do servidor FastAPI (ex: http://127.0.0.1:8000). Se omitido, executa via ADK Runner local."),
    user_id: str = typer.Option("cli_user", "--user", "-usr", help="ID do usuário para manter sessão.")
):
    """
    Inicia a interface REPL interativa no terminal para conversação contínua.
    """
    asyncio.run(_run_repl(url, user_id))

async def _run_repl(url: Optional[str], user_id: str):
    render_header()
    
    mode_str = f"API FastAPI ([bold]{url}[/bold])" if url else "Runner Google ADK Local"
    console.print(f"[green]✓ Modo de Operação: [bold]{mode_str}[/bold][/green]\n")

    runner = MonolithicAgentRunner() if not url else None
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
                console.print("[yellow]Encerrando REPL... Atégotando![/yellow]")
                break

            if user_input.lower() == "/help":
                console.print(Panel(
                    "Comandos disponíveis:\n"
                    "  • [bold]/exit[/bold] ou [bold]/quit[/bold]: Sair do chat\n"
                    "  • [bold]/clear[/bold]: Limpar tela\n"
                    "  • [bold]/help[/bold]: Mostrar esta ajuda",
                    title="Ajuda CLI", border_style="blue"
                ))
                continue

            if user_input.lower() == "/clear":
                console.clear()
                render_header()
                continue

            console.print("[dim]🤖 Agente processando (Google ADK LLM Round-trip)...[/dim]")

            response_text = ""
            metrics_data = None

            if url and client:
                # Executa via FastAPI Server
                try:
                    payload = {"message": user_input, "user_id": user_id, "session_id": session_id}
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
                # Executa localmente via ADK Runner
                metrics = await runner.execute_query(
                    user_query=user_input,
                    user_id=user_id,
                    session_id=session_id
                )
                session_id = runner._default_session_id or "local_session"
                response_text = metrics.response
                metrics_data = {
                    "latency_ms": round(metrics.latency_ms, 2),
                    "prompt_tokens": metrics.prompt_tokens,
                    "completion_tokens": metrics.completion_tokens,
                    "total_tokens": metrics.total_tokens,
                    "is_mock": metrics.is_mock,
                    "problem_tags": metrics.problem_tags
                }

            # Renderiza resposta do Agente
            console.print(Panel(
                Text(response_text, style="bold white"),
                title="[bold cyan]BaseRootAgent (Google ADK)[/bold cyan]",
                border_style="cyan"
            ))

            # Exibe painel de métricas e problemas evidenciados
            if metrics_data:
                lat = metrics_data["latency_ms"]
                pt = metrics_data["prompt_tokens"]
                ct = metrics_data["completion_tokens"]
                tt = metrics_data["total_tokens"]

                metrics_str = f"⏱️  Latência: [bold yellow]{lat} ms[/bold yellow]  |  📥 Prompt Tokens: [bold cyan]{pt}[/bold cyan]  |  📤 Comp. Tokens: [bold cyan]{ct}[/bold cyan]  |  📊 Total: [bold bright_cyan]{tt}[/bold bright_cyan]"
                console.print(metrics_str)

                # Alerta sobre o problema de consumo no cenário monolítico
                if any(tag.startswith("ALTO_CONSUMO") for tag in metrics_data.get("problem_tags", [])):
                    console.print(
                        f"[bold red]⚠️ ALERTA ARQUITETURAL:[/bold red] Esta saudação simples consumiu "
                        f"[bold red]{pt} tokens de prompt[/bold red] e demorou [bold yellow]{lat}ms[/bold yellow] "
                        f"por falta de roteamento/cache prévio!"
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
    Envia uma única mensagem ao agente monolítico e exibe a resposta e métricas.
    """
    async def _ask():
        if url:
            async with httpx.AsyncClient(base_url=url, timeout=30.0) as client:
                resp = await client.post("/api/v1/chat", json={"message": message})
                data = resp.json()
                console.print(f"[bold cyan]Resposta:[/bold cyan] {data['response']}")
                console.print(f"[dim]Métricas: {data['metrics']}[/dim]")
        else:
            runner = MonolithicAgentRunner()
            metrics = await runner.execute_query(message)
            console.print(f"[bold cyan]Resposta:[/bold cyan] {metrics.response}")
            console.print(f"[dim]Latência: {metrics.latency_ms:.1f}ms | Tokens: {metrics.total_tokens}[/dim]")
    
    asyncio.run(_ask())

@app.command()
def server(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host do servidor FastAPI"),
    port: int = typer.Option(8000, "--port", "-p", help="Porta do servidor FastAPI")
):
    """
    Inicia o servidor FastAPI (Uvicorn) com os endpoints /api/v1/chat e /ws/chat.
    """
    import uvicorn
    console.print(f"[bold green]Iniciando servidor FastAPI em http://{host}:{port}...[/bold green]")
    uvicorn.run("src.server:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    # Se nenhum comando for fornecido, executa o REPL interativo por padrão
    if len(sys.argv) == 1:
        app(["repl"])
    else:
        app()
