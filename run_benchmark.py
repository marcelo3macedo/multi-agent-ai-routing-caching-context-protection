#!/usr/bin/env python3
"""
Benchmark Runner - Roteamento de Intenção e Interceptador de Cache vs Agente Monolítico

Compara o desempenho e o consumo de tokens entre a arquitetura monolítica base e a
arquitetura otimizada com Exact/Semantic Cache e Classificador de Intenção (Gemini 1.5 Flash 8B).
"""

import asyncio
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.infrastructure.adk.runner import MonolithicAgentRunner
from src.infrastructure.cache.redis_cache import DualModeRedisCache
from src.infrastructure.classifiers.lightweight_classifier import LightweightIntentClassifier
from src.application.use_cases.process_chat_message import ProcessChatMessageUseCase
from src.domain.entities.chat_message import ChatMessage
from src.infrastructure.config.settings import Settings

console = Console()

TEST_QUERIES = [
    "Bom dia",                  # 1. Saudação (Roteada/Cache sub-15ms)
    "Quem é a empresa?",        # 2. Institucional (Cache Miss na primeira, Hit na repetição)
    "Me recomende um filme",    # 3. Recomendação
    "Bom dia"                   # 4. Segunda Saudação (Exact/Semantic Cache Hit sub-10ms)
]

async def run_benchmark():
    console.print(Panel.fit(
        "[bold cyan]⚡ Benchmark Comparativo: Monolítico vs Otimizado (Roteamento & Cache)[/bold cyan]\n"
        "[dim]Avaliando redução de latência e economia de tokens via Clean Architecture[/dim]",
        border_style="cyan"
    ))

    # Componentes de infraestrutura
    cache_repo = DualModeRedisCache()
    classifier = LightweightIntentClassifier()
    agent_runner = MonolithicAgentRunner()
    
    use_case = ProcessChatMessageUseCase(
        cache_repo=cache_repo,
        classifier=classifier,
        agent_runner=agent_runner
    )

    table = Table(title="Comparativo de Desempenho - Roteamento & Cache vs Baseline Monolítico", show_lines=True)
    table.add_column("ID", justify="center", style="bold", width=4)
    table.add_column("Mensagem (Query)", style="magenta")
    table.add_column("Intenção", justify="center", style="green")
    table.add_column("Status Cache", justify="center", style="blue")
    table.add_column("Latência Monolítica", justify="right", style="yellow")
    table.add_column("Latência Otimizada", justify="right", style="bold yellow")
    table.add_column("Tokens Monolítico", justify="right", style="red")
    table.add_column("Tokens Otimizados", justify="right", style="bold green")

    total_monolithic_latency = 0.0
    total_optimized_latency = 0.0
    total_monolithic_tokens = 0
    total_optimized_tokens = 0

    for idx, query in enumerate(TEST_QUERIES, start=1):
        console.print(f"[dim]Executando teste ({idx}/{len(TEST_QUERIES)}): '{query}'...[/dim]")

        # 1. Execução Monolítica Direct (sem cache/roteamento)
        mono_metrics = await agent_runner.execute_query(query)
        
        # 2. Execução Otimizada via UseCase
        chat_msg = ChatMessage(content=query, user_id="benchmark_user")
        opt_response = await use_case.execute(chat_msg, enable_cache=True, enable_routing=True)
        opt_metrics = opt_response.metrics

        total_monolithic_latency += mono_metrics.latency_ms
        total_optimized_latency += opt_metrics.latency_ms
        total_monolithic_tokens += mono_metrics.total_tokens
        total_optimized_tokens += opt_metrics.total_tokens

        table.add_row(
            str(idx),
            query,
            opt_metrics.intent,
            opt_metrics.cache_status.value if hasattr(opt_metrics.cache_status, "value") else str(opt_metrics.cache_status),
            f"{mono_metrics.latency_ms:.1f} ms",
            f"[bold green]{opt_metrics.latency_ms:.1f} ms[/bold green]",
            str(mono_metrics.total_tokens),
            f"[bold green]{opt_metrics.total_tokens}[/bold green]"
        )

    console.print(table)
    console.print()

    # Cálculo dos ganhos percentuais
    lat_reduction = ((total_monolithic_latency - total_optimized_latency) / total_monolithic_latency) * 100.0 if total_monolithic_latency > 0 else 0
    token_economy = ((total_monolithic_tokens - total_optimized_tokens) / total_monolithic_tokens) * 100.0 if total_monolithic_tokens > 0 else 0

    diag_text = Text()
    diag_text.append("🚀 GANHOS ARQUITETURAIS E ECONOMIA DE RECURSOS\n\n", style="bold green")
    diag_text.append(f"• Latência Total Monolítica: {total_monolithic_latency:.1f} ms  ➔  Otimizada: {total_optimized_latency:.1f} ms ([bold green]-{lat_reduction:.1f}% de tempo[/bold green])\n")
    diag_text.append(f"• Consumo Total de Tokens ADK: {total_monolithic_tokens}  ➔  Otimizado: {total_optimized_tokens} ([bold green]-{token_economy:.1f}% de economia de tokens[/bold green])\n\n")

    diag_text.append("✅ IMPACTO DOS RECURSOS IMPLEMENTADOS:\n\n", style="bold yellow")
    diag_text.append(
        "1. EXACT / SEMANTIC CACHE (REDIS):\n"
        "   Requisições repetidas ou similares (ex: 'Bom dia') retornam instantaneamente em < 10ms "
        "com ZERO consumo de tokens no Google ADK.\n\n",
        style="white"
    )
    diag_text.append(
        "2. LIGHTWEIGHT INTENT CLASSIFIER (GEMINI 1.5 FLASH 8B):\n"
        "   Classifica requisições em alta velocidade, identificando saudações e FAQ sem sobrecarregar "
        "o agente monolítico pesado.\n\n",
        style="white"
    )
    diag_text.append(
        "3. ESTRUTURA CLEAN ARCHITECTURE:\n"
        "   Camadas desacopladas (Domain, Use Cases, Infrastructure, Presentation) garantem facilidade "
        "para evoluir novos roteadores e estratégias de cache.\n",
        style="white"
    )

    console.print(Panel(diag_text, title="Resumo do Impacto de Desempenho", border_style="green"))

if __name__ == "__main__":
    asyncio.run(run_benchmark())
