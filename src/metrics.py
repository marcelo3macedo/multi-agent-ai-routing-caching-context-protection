import time
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class QueryMetrics:
    query: str
    response: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    is_mock: bool = False
    problem_tags: List[str] = field(default_factory=list)

    def analyze_problems(self):
        """Identifica e categoriza os problemas evidenciados no cenário monolítico."""
        tags = []
        query_lower = self.query.lower()
        
        # 1. Alto consumo de tokens para saudações simples
        if any(w in query_lower for w in ["bom dia", "olá", "oi", "boa tarde", "boa noite"]):
            if self.prompt_tokens > 100:
                tags.append("ALTO_CONSUMO_TOKENS_SAUDACAO (Prompt Bloqueado enviado inteiro)")
        
        # 2. Latência desnecessária de round-trip da LLM
        if self.latency_ms > 200:  # Qualquer chamada LLM para saudação/estática > 200ms é desnecessária
            tags.append(f"LATENCIA_ROUNDTRIP_LLM ({self.latency_ms:.1f}ms)")
            
        # 3. Falta de especialização de contexto
        tags.append("SEM_ESPECIALIZACAO_CONTEXTO (Agente genérico processou sem roteador)")
        
        self.problem_tags = tags

class BenchmarkTracker:
    def __init__(self):
        self.records: List[QueryMetrics] = []

    def add_record(self, metrics: QueryMetrics):
        metrics.analyze_problems()
        self.records.append(metrics)

    def get_summary(self) -> dict:
        total_queries = len(self.records)
        if total_queries == 0:
            return {}

        total_prompt_tokens = sum(r.prompt_tokens for r in self.records)
        total_completion_tokens = sum(r.completion_tokens for r in self.records)
        total_tokens = sum(r.total_tokens for r in self.records)
        avg_latency_ms = sum(r.latency_ms for r in self.records) / total_queries

        return {
            "total_queries": total_queries,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "avg_latency_ms": avg_latency_ms
        }
