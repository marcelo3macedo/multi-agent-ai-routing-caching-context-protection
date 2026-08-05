import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import google.adk as adk
from src.runner import MonolithicAgentRunner
from src.config import Config

app = FastAPI(
    title="Google ADK Monolithic Agent API Server",
    description="Servidor FastAPI com endpoints REST e WebSocket conectados ao BaseRootAgent (Google ADK)",
    version="1.0.0"
)

# Habilita suporte a CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instância global do Runner do Agente Monolítico
runner_instance = MonolithicAgentRunner()

class ChatRequest(BaseModel):
    message: str = Field(..., description="Mensagem do usuário", example="Bom dia")
    user_id: str = Field(default="user_default", description="Identificador do usuário")
    session_id: Optional[str] = Field(default=None, description="ID da sessão no ADK")

class MetricsResponse(BaseModel):
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    is_mock: bool
    problem_tags: List[str]

class ChatResponse(BaseModel):
    response: str
    session_id: str
    user_id: str
    metrics: MetricsResponse

@app.get("/api/v1/health")
async def health_check():
    """Endpoint de verificação de saúde da aplicação e status do agente ADK."""
    return {
        "status": "ok",
        "agent": runner_instance.agent.name,
        "model": Config.get_effective_model(),
        "adk_version": getattr(adk, "__version__", "unknown"),
        "is_mock": Config.get_effective_model().startswith("mock-model")
    }

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Endpoint REST (POST) para interação síncrona com o BaseRootAgent.
    
    Toda mensagem enviada por este endpoint é processada diretamente pelo agente monolítico
    no Google ADK, sem camadas de cache ou roteamento prévio.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="A mensagem não pode estar vazia.")

    active_session_id = await runner_instance.get_or_create_session(
        user_id=request.user_id,
        session_id=request.session_id
    )

    metrics = await runner_instance.execute_query(
        user_query=request.message,
        user_id=request.user_id,
        session_id=active_session_id
    )

    return ChatResponse(
        response=metrics.response,
        session_id=active_session_id,
        user_id=request.user_id,
        metrics=MetricsResponse(
            latency_ms=round(metrics.latency_ms, 2),
            prompt_tokens=metrics.prompt_tokens,
            completion_tokens=metrics.completion_tokens,
            total_tokens=metrics.total_tokens,
            is_mock=metrics.is_mock,
            problem_tags=metrics.problem_tags
        )
    )

@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket (/ws/chat) para conversação em streaming contínuo com o agente monolítico ADK.
    
    Permite enviar mensagens em tempo real e receber chunks de texto (deltas) à medida que o ADK
    gera a resposta, além das métricas de consumo de token ao finalizar a resposta.
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

            if not user_message.strip():
                await websocket.send_json({"type": "error", "error": "Mensagem vazia."})
                continue

            async for event in runner_instance.stream_query(
                user_query=user_message,
                user_id=user_id,
                session_id=session_id
            ):
                await websocket.send_json(event)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.server:app", host="127.0.0.1", port=8000, reload=True)
