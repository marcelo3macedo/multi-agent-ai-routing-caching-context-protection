import pytest
from fastapi.testclient import TestClient
from src.domain.entities.intent import IntentCategory
from src.domain.entities.metrics import CacheStatus
from src.domain.entities.chat_message import ChatMessage
from src.infrastructure.cache.redis_cache import DualModeRedisCache
from src.infrastructure.classifiers.lightweight_classifier import LightweightIntentClassifier
from src.infrastructure.adk.runner import MonolithicAgentRunner
from src.application.use_cases.process_chat_message import ProcessChatMessageUseCase
from src.presentation.api.server import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_dual_mode_redis_cache():
    cache = DualModeRedisCache()
    await cache.set("bom dia", "Olá! Bom dia!", ttl_seconds=300)
    
    exact_res = await cache.get_exact("bom dia")
    assert exact_res == "Olá! Bom dia!"
    
    semantic_res = await cache.find_semantic("bom dia!")
    assert semantic_res is not None
    val, _ = semantic_res
    assert val == "Olá! Bom dia!"
    
    stats = await cache.get_stats()
    assert stats["hits_exact"] > 0 or stats["hits_semantic"] > 0

@pytest.mark.asyncio
async def test_lightweight_intent_classifier():
    classifier = LightweightIntentClassifier()
    
    res_greeting = await classifier.classify("Bom dia")
    assert res_greeting.category == IntentCategory.GREETING
    
    res_inst = await classifier.classify("Quem é a empresa?")
    assert res_inst.category == IntentCategory.INSTITUTIONAL
    
    res_movie = await classifier.classify("Me recomende um filme")
    assert res_movie.category == IntentCategory.MOVIE_SEARCH

@pytest.mark.asyncio
async def test_process_chat_message_use_case_routing_and_cache():
    cache = DualModeRedisCache()
    classifier = LightweightIntentClassifier()
    runner = MonolithicAgentRunner()
    
    use_case = ProcessChatMessageUseCase(cache_repo=cache, classifier=classifier, agent_runner=runner)
    
    # 1. Primeira chamada (Saudação Roteada): Latência baixa, 0 tokens ADK
    msg1 = ChatMessage(content="Bom dia", user_id="test_user")
    res1 = await use_case.execute(msg1)
    
    assert res1.metrics.intent == "GREETING"
    assert res1.metrics.prompt_tokens == 0
    assert res1.metrics.latency_ms < 50.0  # Sub-50ms para saudação estática
    
    # 2. Segunda chamada idêntica (Cache Hit): Retorno imediato
    res2 = await use_case.execute(msg1)
    assert res2.metrics.cache_status in (CacheStatus.HIT_EXACT, CacheStatus.HIT_SEMANTIC)
    assert res2.metrics.prompt_tokens == 0
    assert res2.metrics.latency_ms < 20.0

def test_fastapi_cache_stats_and_routing():
    response = client.get("/api/v1/cache/stats")
    assert response.status_code == 200
    data = response.json()
    assert "hits_exact" in data
    assert "mode" in data

    chat_res = client.post("/api/v1/chat", json={"message": "Bom dia"})
    assert chat_res.status_code == 200
    res_data = chat_res.json()
    assert res_data["metrics"]["intent"] == "GREETING"
    assert res_data["metrics"]["prompt_tokens"] == 0
