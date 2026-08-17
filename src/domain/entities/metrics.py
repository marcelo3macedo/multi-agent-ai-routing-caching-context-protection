from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional

class CacheStatus(str, Enum):
    HIT_EXACT = "HIT_EXACT"
    HIT_SEMANTIC = "HIT_SEMANTIC"
    MISS = "MISS"

@dataclass
class QueryMetrics:
    query: str
    response: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    intent: str = "UNKNOWN"
    cache_status: CacheStatus = CacheStatus.MISS
    is_mock: bool = False
    tokens_saved: int = 0
    problem_tags: List[str] = field(default_factory=list)

    def analyze_problems(self):
        """Analisa o desempenho e identifica se houve otimização por cache/roteamento."""
        tags = []
        
        if self.cache_status in (CacheStatus.HIT_EXACT, CacheStatus.HIT_SEMANTIC):
            tags.append(f"CACHE_OPTIMIZED ({self.cache_status.value} - Latência {self.latency_ms:.1f}ms - 0 Tokens ADK)")
        elif self.intent == "GREETING" and self.prompt_tokens == 0:
            tags.append(f"DETERMINISTIC_GREETING (Sub-15ms - 0 Tokens ADK)")
        else:
            if self.query.lower() in ["bom dia", "olá", "oi", "boa tarde"]:
                tags.append("ALTO_CONSUMO_TOKENS_SAUDACAO (Encaminhado diretamente ao ADK)")
            tags.append(f"ADK_ROUNDTRIP_LLM ({self.latency_ms:.1f}ms - {self.total_tokens} tokens)")

        self.problem_tags = tags
