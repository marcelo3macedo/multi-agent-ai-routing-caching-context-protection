import asyncio
import json
import time
from typing import Optional
from src.domain.interfaces.intent_classifier import IIntentClassifier
from src.domain.entities.intent import IntentCategory, IntentResult
from src.infrastructure.config.settings import Settings

class LightweightIntentClassifier(IIntentClassifier):
    """
    Classificador de Intenções Ultrarrápido baseado no modelo Gemini 1.5 Flash 8B.
    
    Categoriza a requisição em GREETING, INSTITUTIONAL, MOVIE_SEARCH ou UNKNOWN
    com latência mínima antes de decidir se aciona o Google ADK ou responde diretamente.
    """
    def __init__(self, model_name: str = None):
        self.model_name = model_name or Settings.get_effective_classifier_model()
        self._is_mock = self.model_name.startswith("mock-")

    async def classify(self, text: str) -> IntentResult:
        query_lower = text.lower().strip()
        
        # Heurística ultrarrápida (sub-2ms) para saudações óbvias
        greeting_words = {"bom dia", "boa tarde", "boa noite", "olá", "ola", "oi", "e ai", "tudo bem"}
        if query_lower in greeting_words or any(query_lower.startswith(w) for w in greeting_words if len(query_lower) < 15):
            return IntentResult(
                category=IntentCategory.GREETING,
                confidence=0.99,
                reasoning="Correspondência direta de saudação de alta velocidade."
            )

        if "empresa" in query_lower or "quem é" in query_lower or "techcorp" in query_lower:
            return IntentResult(
                category=IntentCategory.INSTITUTIONAL,
                confidence=0.95,
                reasoning="Consulta de informações institucionais sobre a empresa."
            )

        if "filme" in query_lower or "cinema" in query_lower or "recomende" in query_lower or "indique" in query_lower:
            return IntentResult(
                category=IntentCategory.MOVIE_SEARCH,
                confidence=0.95,
                reasoning="Solicitação de recomendação de filme/entretenimento."
            )

        # Se tivermos API Key e não for mock, podemos chamar o Gemini 1.5 Flash 8b real via API
        if Settings.is_api_key_available() and not self._is_mock:
            try:
                from google import genai
                client = genai.Client(api_key=Settings.GEMINI_API_KEY)
                prompt = (
                    "Classifique a intenção da mensagem abaixo em EXATAMENTE uma das categorias: "
                    "GREETING, INSTITUTIONAL, MOVIE_SEARCH ou UNKNOWN.\n"
                    f"Mensagem: '{text}'\n"
                    "Responda apenas com a categoria."
                )
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                raw_cat = response.text.strip().upper() if response.text else "UNKNOWN"
                if raw_cat in [e.value for e in IntentCategory]:
                    return IntentResult(category=IntentCategory(raw_cat), confidence=0.90)
            except Exception:
                pass

        return IntentResult(
            category=IntentCategory.UNKNOWN,
            confidence=0.50,
            reasoning="Intenção genérica ou não categorizada especificamente."
        )
