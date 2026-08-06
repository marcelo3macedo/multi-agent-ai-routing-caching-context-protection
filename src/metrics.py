from src.domain.entities.metrics import QueryMetrics, CacheStatus
from typing import List

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
        total_saved = sum(getattr(r, "tokens_saved", 0) for r in self.records)

        return {
            "total_queries": total_queries,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "tokens_saved": total_saved,
            "avg_latency_ms": avg_latency_ms
        }
