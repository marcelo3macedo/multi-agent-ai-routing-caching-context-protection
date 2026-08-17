import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env se existir
load_dotenv()

class Config:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    USE_MOCK_LLM: bool = os.getenv("USE_MOCK_LLM", "false").lower() in ("true", "1", "yes")

    @classmethod
    def is_api_key_available(cls) -> bool:
        return bool(cls.GEMINI_API_KEY and cls.GEMINI_API_KEY != "your_gemini_api_key_here")

    @classmethod
    def get_effective_model(cls) -> str:
        if cls.USE_MOCK_LLM or not cls.is_api_key_available():
            return "mock-model-gemini-2.5-flash"
        return cls.GEMINI_MODEL
