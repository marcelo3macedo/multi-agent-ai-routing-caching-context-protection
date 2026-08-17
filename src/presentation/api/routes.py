import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from src.application.dtos.chat_dto import ChatRequestDTO, ChatResponseDTO, MetricsDTO
from src.domain.entities.chat_message import ChatMessage
from src.application.use_cases.process_chat_message import ProcessChatMessageUseCase
from src.infrastructure.cache.redis_cache import DualModeRedisCache
from src.infrastructure.classifiers.lightweight_classifier import LightweightIntentClassifier
from src.infrastructure.adk.runner import MonolithicAgentRunner
from src.infrastructure.config.settings import Settings

router = APIRouter()

# Singletons de infraestrutura para injeção de dependência
cache_repository = DualModeRedisCache()
intent_classifier = LightweightIntentClassifier()
agent_runner = MonolithicAgentRunner()

process_chat_use_case = ProcessChatMessageUseCase(
    cache_repo=cache_repository,
    classifier=intent_classifier,
    agent_runner=agent_runner
)

@router.get("/health")
async def health_check():
    """Retorna status do servidor e do modelo ADK."""
    return {
        "status": "ok",
        "agent": agent_runner.agent.name,
        "model": Settings.get_effective_model(),
        "classifier_model": Settings.get_effective_classifier_model(),
        "is_mock": Settings.get_effective_model().startswith("mock-model")
    }

@router.get("/cache/stats")
async def cache_stats():
    """Retorna estatísticas detalhadas do Cache Interceptador (Redis / In-Memory)."""
    return await cache_repository.get_stats()

@router.post("/chat", response_model=ChatResponseDTO)
async def chat_endpoint(request: ChatRequestDTO):
    """
    Endpoint REST (POST /api/v1/chat) interceptado por Roteamento de Intenção e Cache.
    
    1. Verifica Exact/Semantic Cache (retorna em <10ms se encontrado).
    2. Classifica a intenção via Gemini 1.5 Flash 8B.
    3. Responde saudações determinísticas imediatamente (<15ms).
    4. Encaminha apenas requisições complexas ao Google ADK.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="A mensagem não pode estar vazia.")

    chat_message = ChatMessage(
        content=request.message,
        user_id=request.user_id,
        session_id=request.session_id
    )

    chat_response = await process_chat_use_case.execute(
        message=chat_message,
        enable_cache=request.enable_cache,
        enable_routing=request.enable_routing
    )

    m = chat_response.metrics

    return ChatResponseDTO(
        response=chat_response.text,
        session_id=chat_response.session_id,
        user_id=chat_response.user_id,
        metrics=MetricsDTO(
            latency_ms=round(m.latency_ms, 2),
            prompt_tokens=m.prompt_tokens,
            completion_tokens=m.completion_tokens,
            total_tokens=m.total_tokens,
            intent=m.intent,
            cache_status=m.cache_status.value if hasattr(m.cache_status, "value") else str(m.cache_status),
            is_mock=m.is_mock,
            tokens_saved=m.tokens_saved,
            problem_tags=m.problem_tags
        )
    )

@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket (/ws/chat) com streaming de resposta e suporte a Cache/Roteamento.
    """
    await websocket.accept()
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except Exception:
                data = {"message": raw_data}

            user_message = data.get("message", "")
            user_id = data.get("user_id", "user_ws")
            session_id = data.get("session_id")
            enable_cache = data.get("enable_cache", True)
            enable_routing = data.get("enable_routing", True)

            if not user_message.strip():
                await websocket.send_json({"type": "error", "error": "Mensagem vazia."})
                continue

            chat_msg = ChatMessage(content=user_message, user_id=user_id, session_id=session_id)

            async for event in process_chat_use_case.execute_stream(
                message=chat_msg,
                enable_cache=enable_cache,
                enable_routing=enable_routing
            ):
                await websocket.send_json(event)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass
