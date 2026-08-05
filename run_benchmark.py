#!/usr/bin/env python3
"""
Benchmark Runner - Cenário Base: Agente Monolítico com Google ADK Sem Otimização

Executa os testes para evidenciar os problemas de custo, latência e falta de especialização
no processamento de mensagens heterogêneas por um único agente monolítico.
"""

import asyncio
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.runner import MonolithicAgentRunner
from src.metrics import BenchmarkTracker
from src.config import Config

console = Console()

TEST_QUERIES = [
    "Bom dia",
    "Quem é a empresa?",
    "Me recomende um filme"
]

async def run_benchmark():
    console.print(Panel.fit(
        "[bold cyan]Cenário Base: Agente Monolítico com Google ADK (Sem Otimização)[/bold cyan]\n"
        "[dim]Instanciando BaseRootAgent e processando mensagens pelo Runner do Google ADK[/dim]",
        border_style="cyan"
    ))

    is_api_available = Config.is_api_key_available()
    effective_model = Config.get_effective_model()

    if not is_api_available:
        console.print(
            "[yellow]⚠️ GEMINI_API_KEY não detectada. Executando em modo Mock LLM para validação de arquitetura.[/yellow]\n"
            "[dim]Para testar contra a API real do Gemini, defina GEMINI_API_KEY no arquivo .env[/dim]\n"
        )
    else:
        console.print(f"[green]✓ Chave da API Gemini detectada. Modelo em uso: [bold]{effective_model}[/bold][/green]\n")

    runner = MonolithicAgentRunner()
    tracker = BenchmarkTracker()

    table = Table(title="Resultados da Execução - Agente Monolítico BaseRootAgent", show_lines=True)
    table.add_column("ID", justify="center", style="bold", width=4)
    table.add_column("Mensagem (Query)", style="magenta")
    table.add_column("Latência (ms)", justify="right", style="yellow")
    table.add_column("Prompt Tokens", justify="right", style="cyan")
    table.add_column("Comp. Tokens", justify="right", style="cyan")
    table.add_column("Total Tokens", justify="right", style="bold cyan")
    table.add_column("Resposta do Agente (Snippet)", style="white")

    for idx, query in enumerate(TEST_QUERIES, start=1):
        console.print(f"[dim]Processando ({idx}/{len(TEST_QUERIES)}): '{query}'...[/dim]")
        metrics = await runner.execute_query(query)
        tracker.add_record(metrics)

        snippet = metrics.response[:70] + "..." if len(metrics.response) > 70 else metrics.response
        table.add_row(
            str(idx),
            metrics.query,
            f"{metrics.latency_ms:.1f} ms",
            str(metrics.prompt_tokens),
            str(metrics.completion_tokens),
            str(metrics.total_tokens),
            snippet
        )

    console.print(table)
    console.print()

    # Relatório de Diagnóstico dos Problemas Evidenciados
    summary = tracker.get_summary()

    diag_text = Text()
    diag_text.append("📊 RESUMO DE EXECUÇÃO E PROBLEMAS EVIDENCIADOS\n\n", style="bold red")
    diag_text.append(f"• Total de Consultas: {summary.get('total_queries')}\n")
    diag_text.append(f"• Média de Latência: {summary.get('avg_latency_ms'):.1f} ms por mensagem\n")
    diag_text.append(f"• Consumo Total de Tokens: {summary.get('total_tokens')} (Prompt: {summary.get('total_prompt_tokens')} | Resposta: {summary.get('total_completion_tokens')})\n\n")

    diag_text.append("❌ PROBLEMAS EVIDENCIADOS NO CENÁRIO MONOLÍTICO:\n\n", style="bold yellow")
    
    greeting_record = tracker.records[0] if tracker.records else None
    if greeting_record:
        diag_text.append(
            f"1. ALTO CONSUMO DE TOKENS EM SAUDAÇÕES SIMPLES:\n"
            f"   A mensagem '{greeting_record.query}' consumiu {greeting_record.prompt_tokens} tokens de prompt "
            f"apenas para carregar as instruções completas do agente monolítico.\n\n",
            style="red"
        )
    
    diag_text.append(
        f"2. LATÊNCIA DESNECESSÁRIA NO ROUND-TRIP DA LLM:\n"
        f"   Cada mensagem simples (ex: saudações) exige uma chamada completa à rede ({summary.get('avg_latency_ms'):.1f}ms em média), "
        f"sem reaproveitamento ou resposta rápida determinística.\n\n",
        style="red"
    )

    diag_text.append(
        "3. FALTA DE ESPECIALIZAÇÃO DE CONTEXTO:\n"
        "   Todas as requisições (saudações, dados corporativos, recomendações de filmes) passam pelo "
        "mesmo agente genérico (BaseRootAgent), aumentando a ambiguidade do sistema e a sobrecarga de instrução.\n",
        style="red"
    )

    console.print(Panel(diag_text, title="Diagnóstico de Arquitetura", border_style="red"))

if __name__ == "__main__":
    asyncio.run(run_benchmark())
