import time
import asyncio
from typing import Tuple, Optional, AsyncGenerator, Dict, Any
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from src.agent import create_base_root_agent, MONOLITHIC_SYSTEM_INSTRUCTION
from src.metrics import QueryMetrics
from src.config import Config

class MonolithicAgentRunner:
    """
    Runner para o Agente Monolítico BaseRootAgent utilizando o Google ADK.
    
    Gerencia sessões em memória (InMemorySessionService) e orquestra
    o ciclo de vida da conversa sem roteamento especializado.
    """
    def __init__(self, agent: Optional[LlmAgent] = None):
        self.agent = agent or create_base_root_agent()
        self.runner = InMemoryRunner(agent=self.agent)
        self._default_session_id: Optional[str] = None
        self._default_user_id = "default_benchmark_user"

    async def get_or_create_session(self, user_id: str = "default_user", session_id: Optional[str] = None) -> str:
        """Cria ou recupera uma sessão de conversa no ADK."""
        if session_id:
            try:
                # Verifica se a sessão existe
                await self.runner.session_service.get_session(
                    session_id=session_id,
                    user_id=user_id,
                    app_name=self.runner.app_name
                )
                return session_id
            except Exception:
                # Se não existir, cria com o ID fornecido ou um novo
                pass
        
        session = await self.runner.session_service.create_session(
            user_id=user_id,
            app_name=self.runner.app_name
        )
        return session.id

    async def stream_query(
        self, user_query: str, user_id: str = "default_user", session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Gerador assíncrono para streaming de resposta em tempo real via WebSocket ou SSE,
        emitindo chunks de texto e as métricas finais ao término.
        """
        active_session_id = await self.get_or_create_session(user_id=user_id, session_id=session_id)
        
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_query)]
        )

        start_time = time.perf_counter()
        accumulated_text = ""
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        yield {
            "type": "start",
            "session_id": active_session_id,
            "user_id": user_id
        }

        try:
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=active_session_id,
                new_message=user_message
            ):
                delta_text = ""
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            delta_text += part.text
                elif getattr(event, "output", None):
                    out = event.output
                    if isinstance(out, str):
                        delta_text += out
                    elif hasattr(out, "text"):
                        delta_text += out.text
                
                if delta_text:
                    accumulated_text += delta_text
                    yield {
                        "type": "delta",
                        "text": delta_text
                    }
                
                # Extrai métricas de uso de token do evento ADK
                if hasattr(event, "usage_metadata") and event.usage_metadata:
                    um = event.usage_metadata
                    if getattr(um, "prompt_token_count", None):
                        prompt_tokens = um.prompt_token_count
                    if getattr(um, "candidates_token_count", None):
                        completion_tokens = um.candidates_token_count
                    if getattr(um, "total_token_count", None):
                        total_tokens = um.total_token_count

        except Exception as e:
            error_msg = f"Erro no streaming ADK: {str(e)}"
            accumulated_text += error_msg
            yield {"type": "error", "error": error_msg}

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000.0

        if prompt_tokens == 0:
            system_tokens = len(MONOLITHIC_SYSTEM_INSTRUCTION.split()) * 1.3
            query_tokens = len(user_query.split()) * 1.3
            prompt_tokens = int(system_tokens + query_tokens + 50)
        
        if completion_tokens == 0:
            completion_tokens = int(len(accumulated_text.split()) * 1.3)
            
        if total_tokens == 0:
            total_tokens = prompt_tokens + completion_tokens

        is_mock = Config.get_effective_model().startswith("mock-model")

        metrics = QueryMetrics(
            query=user_query,
            response=accumulated_text.strip(),
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            is_mock=is_mock
        )
        metrics.analyze_problems()

        yield {
            "type": "complete",
            "session_id": active_session_id,
            "text": accumulated_text.strip(),
            "metrics": {
                "latency_ms": round(metrics.latency_ms, 2),
                "prompt_tokens": metrics.prompt_tokens,
                "completion_tokens": metrics.completion_tokens,
                "total_tokens": metrics.total_tokens,
                "is_mock": metrics.is_mock,
                "problem_tags": metrics.problem_tags
            }
        }

    async def execute_query(
        self, user_query: str, user_id: str = "default_user", session_id: Optional[str] = None
    ) -> QueryMetrics:
        """
        Executa uma mensagem do usuário no BaseRootAgent e retorna as métricas acumuladas.
        """
        final_metrics_dict = None
        response_text = ""

        async for event in self.stream_query(user_query, user_id=user_id, session_id=session_id):
            if event["type"] == "delta":
                response_text += event.get("text", "")
            elif event["type"] == "complete":
                m = event["metrics"]
                final_metrics_dict = m
                response_text = event.get("text", response_text)

        metrics = QueryMetrics(
            query=user_query,
            response=response_text,
            latency_ms=final_metrics_dict["latency_ms"] if final_metrics_dict else 0.0,
            prompt_tokens=final_metrics_dict["prompt_tokens"] if final_metrics_dict else 0,
            completion_tokens=final_metrics_dict["completion_tokens"] if final_metrics_dict else 0,
            total_tokens=final_metrics_dict["total_tokens"] if final_metrics_dict else 0,
            is_mock=final_metrics_dict["is_mock"] if final_metrics_dict else False,
            problem_tags=final_metrics_dict["problem_tags"] if final_metrics_dict else []
        )
        return metrics
