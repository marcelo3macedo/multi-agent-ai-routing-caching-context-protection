import pytest
from src.agent import create_base_root_agent, MONOLITHIC_SYSTEM_INSTRUCTION
from src.runner import MonolithicAgentRunner
from src.metrics import BenchmarkTracker, QueryMetrics
from src.config import Config

def test_agent_creation():
    agent = create_base_root_agent()
    assert agent.name == "BaseRootAgent"
    assert len(agent.instruction) > 100
    assert agent.tools == []

@pytest.mark.asyncio
async def test_monolithic_runner_execution():
    runner = MonolithicAgentRunner()
    metrics = await runner.execute_query("Bom dia")
    
    assert isinstance(metrics, QueryMetrics)
    assert metrics.query == "Bom dia"
    assert len(metrics.response) > 0
    assert metrics.prompt_tokens > 0
    assert metrics.total_tokens > metrics.prompt_tokens
    assert len(metrics.problem_tags) > 0

@pytest.mark.asyncio
async def test_benchmark_tracker():
    tracker = BenchmarkTracker()
    runner = MonolithicAgentRunner()
    
    m1 = await runner.execute_query("Bom dia")
    m2 = await runner.execute_query("Quem é a empresa?")
    
    tracker.add_record(m1)
    tracker.add_record(m2)
    
    summary = tracker.get_summary()
    assert summary["total_queries"] == 2
    assert summary["total_tokens"] > 0
    assert summary["avg_latency_ms"] > 0
