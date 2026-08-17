import asyncio
import time
from typing import AsyncGenerator
from google.adk.models import BaseLlm, LlmRequest, LlmResponse, LLMRegistry
from google.genai import types
from pydantic import Field

class MockLlm(BaseLlm):
    """
    Mock LLM para o Google ADK.
    Simula respostas do Gemini com métricas realistas para o cenário monolítico
    quando nenhuma chave de API é fornecida ou quando USE_MOCK_LLM=true.
    """
    model: str = Field(default="mock-model-gemini-2.5-flash")

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"^mock-model.*"]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        # Extrai o texto da última mensagem do usuário
        user_query = ""
        if llm_request.contents:
            last_content = llm_request.contents[-1]
            if last_content.parts:
                user_query = last_content.parts[0].text or ""

        query_lower = user_query.lower()

        # Determina a resposta e latência/tokens simulados com base na query
        if "bom dia" in query_lower or "olá" in query_lower or "oi" in query_lower:
            response_text = (
                "Olá! Bom dia! Como posso ajudar você hoje? "
                "Estou à disposição para responder dúvidas sobre nossa empresa, "
                "fazer recomendações de filmes ou tratar de qualquer outro assunto."
            )
            simulated_latency = 0.65  # 650ms round-trip LLM
            prompt_tokens = 385  # Prompt monolítico completo + saudação
            candidates_tokens = 35
        elif "empresa" in query_lower or "quem é" in query_lower:
            response_text = (
                "A TechCorp Solutions é uma empresa fundada em 2020, "
                "especializada em desenvolvimento de software e soluções de Inteligência Artificial "
                "para otimização de processos corporativos."
            )
            simulated_latency = 0.95  # 950ms round-trip LLM
            prompt_tokens = 410
            candidates_tokens = 42
        elif "filme" in query_lower or "recomende" in query_lower:
            response_text = (
                "Com certeza! Recomendo o filme 'A Rede Social' (2010), dirigido por David Fincher, "
                "ou 'Interstellar' (2014) de Christopher Nolan se você curte ficção científica e ciência."
            )
            simulated_latency = 1.15  # 1150ms round-trip LLM
            prompt_tokens = 405
            candidates_tokens = 50
        else:
            response_text = f"Entendi sua solicitação sobre '{user_query}'. Como assistente genérico, posso te ajudar!"
            simulated_latency = 0.85
            prompt_tokens = 390
            candidates_tokens = 30

        # Simula o tempo de inferência e round-trip de rede da LLM
        await asyncio.sleep(simulated_latency)

        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=response_text)]
            ),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=prompt_tokens,
                candidates_token_count=candidates_tokens,
                total_token_count=prompt_tokens + candidates_tokens
            )
        )

def register_mock_llm():
    """Registra o MockLlm no LLMRegistry do Google ADK."""
    try:
        LLMRegistry.register(MockLlm)
    except Exception:
        pass  # Já registrado
