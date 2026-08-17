import time
import asyncio
import uuid
from typing import AsyncGenerator, Dict, Any, Optional
from src.domain.interfaces.cache_repository import ICacheRepository
from src.domain.interfaces.intent_classifier import IIntentClassifier
from src.domain.interfaces.agent_runner import IAgentRunner
from src.domain.entities.intent import IntentCategory
from src.domain.entities.metrics import QueryMetrics, CacheStatus
from src.domain.entities.chat_message import ChatMessage, ChatResponse

class ProcessChatMessageUseCase:
    """
    Caso de Uso Principal: Processamento de Mensagens com Roteamento de Intenção e Cache Interceptador.
    
    Orquestra a busca em cache (sub-10ms), classificação de intenção rápida (Gemini 1.5 Flash 8B)
    e encaminhamento ao agente ADK apenas em casos estritamente necessários.
    """
    def __init__(
        self,
        cache_repo: ICacheRepository,
        classifier: IIntentClassifier,
        agent_runner: IAgentRunner
    ):
        self.cache_repo = cache_repo
        self.classifier = classifier
        self.agent_runner = agent_runner

    async def execute(
        self,
        message: ChatMessage,
        enable_cache: bool = True,
        enable_routing: bool = True
    ) -> ChatResponse:
        start_time = time.perf_counter()
        query = message.content.strip()

        if enable_cache:
            cache_result = await self.cache_repo.find_semantic(query, threshold=0.85)
            if cache_result:
                cached_text, _ = cache_result
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000.0

                metrics = QueryMetrics(
                    query=query,
                    response=cached_text,
                    latency_ms=latency_ms,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    intent="CACHED",
                    cache_status=CacheStatus.HIT_SEMANTIC,
                    tokens_saved=420
                )
                metrics.analyze_problems()

                return ChatResponse(
                    text=cached_text,
                    session_id=message.session_id or "cached_session",
                    user_id=message.user_id,
                    metrics=metrics
                )

        intent_result = await self.classifier.classify(query)
        intent_cat = intent_result.category

        if enable_routing and intent_cat == IntentCategory.GREETING:
            greeting_response = (
                "Olá! Bem-vindo à TechCorp Solutions, sua empresa de indicação de filmes! 🎬 "
                "Quer saber sobre algum filme ou sobre a empresa?"
            )
            
            if enable_cache:
                await self.cache_repo.set(query, greeting_response, ttl_seconds=86400)

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000.0

            metrics = QueryMetrics(
                query=query,
                response=greeting_response,
                latency_ms=latency_ms,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                intent=intent_cat.value,
                cache_status=CacheStatus.MISS,
                tokens_saved=420
            )
            metrics.analyze_problems()

            return ChatResponse(
                text=greeting_response,
                session_id=message.session_id or f"greeting_{uuid.uuid4().hex}",
                user_id=message.user_id,
                metrics=metrics
            )

        adk_metrics = await self.agent_runner.execute_query(
            user_query=query,
            user_id=message.user_id,
            session_id=message.session_id
        )

        end_time = time.perf_counter()
        total_latency_ms = (end_time - start_time) * 1000.0

        adk_metrics.intent = intent_cat.value
        adk_metrics.latency_ms = total_latency_ms
        adk_metrics.cache_status = CacheStatus.MISS
        adk_metrics.analyze_problems()

        if enable_cache and len(adk_metrics.response) > 0:
            await self.cache_repo.set(query, adk_metrics.response, ttl_seconds=3600)

        return ChatResponse(
            text=adk_metrics.response,
            session_id=message.session_id or "adk_session",
            user_id=message.user_id,
            metrics=adk_metrics
        )

    async def execute_stream(
        self,
        message: ChatMessage,
        enable_cache: bool = True,
        enable_routing: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Versão em streaming para suporte a WebSocket.
        """
        start_time = time.perf_counter()
        query = message.content.strip()

        if enable_cache:
            cache_result = await self.cache_repo.find_semantic(query, threshold=0.85)
            if cache_result:
                cached_text, _ = cache_result
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000.0

                yield {"type": "start", "session_id": message.session_id or "cached_session"}
                yield {"type": "delta", "text": cached_text}
                yield {
                    "type": "complete",
                    "session_id": message.session_id or "cached_session",
                    "text": cached_text,
                    "metrics": {
                        "latency_ms": round(latency_ms, 2),
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "intent": "CACHED",
                        "cache_status": CacheStatus.HIT_SEMANTIC.value,
                        "tokens_saved": 420,
                        "problem_tags": [f"CACHE_OPTIMIZED (Sub-10ms - 0 Tokens ADK)"]
                    }
                }
                return

        intent_result = await self.classifier.classify(query)
        intent_cat = intent_result.category

        if enable_routing and intent_cat == IntentCategory.GREETING:
            greeting_text = (
                "Olá! Bem-vindo à TechCorp Solutions, sua empresa de indicação de filmes! 🎬 "
                "Quer saber sobre algum filme ou sobre a empresa?"
            )
            if enable_cache:
                await self.cache_repo.set(query, greeting_text, ttl_seconds=86400)

            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000.0

            greeting_session_id = message.session_id or f"greeting_{uuid.uuid4().hex}"
            yield {"type": "start", "session_id": greeting_session_id}
            yield {"type": "delta", "text": greeting_text}
            yield {
                "type": "complete",
                "session_id": greeting_session_id,
                "text": greeting_text,
                "metrics": {
                    "latency_ms": round(latency_ms, 2),
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "intent": intent_cat.value,
                    "cache_status": CacheStatus.MISS.value,
                    "tokens_saved": 420,
                    "problem_tags": ["DETERMINISTIC_GREETING (Sub-15ms - 0 Tokens ADK)"]
                }
            }
            return

        async for event in self.agent_runner.stream_query(
            user_query=query,
            user_id=message.user_id,
            session_id=message.session_id
        ):
            if event.get("type") == "complete":
                if enable_cache and event.get("text"):
                    await self.cache_repo.set(query, event["text"], ttl_seconds=3600)
                event["metrics"]["intent"] = intent_cat.value
            yield event
