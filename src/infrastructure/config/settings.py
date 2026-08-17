import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    CLASSIFIER_MODEL: str = os.getenv("CLASSIFIER_MODEL", "gemini-3.6-flash")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    USE_MOCK_LLM: bool = os.getenv("USE_MOCK_LLM", "false").lower() in ("true", "1", "yes")

    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
    TMDB_BASE_URL: str = os.getenv("TMDB_BASE_URL", "https://api.themoviedb.org/3")

    @classmethod
    def is_api_key_available(cls) -> bool:
        return bool(cls.GEMINI_API_KEY and cls.GEMINI_API_KEY != "your_gemini_api_key_here")

    @classmethod
    def is_tmdb_key_available(cls) -> bool:
        return bool(cls.TMDB_API_KEY and cls.TMDB_API_KEY != "your_tmdb_api_key_here")

    @classmethod
    def get_effective_model(cls) -> str:
        if cls.USE_MOCK_LLM or not cls.is_api_key_available():
            return "mock-model-gemini-3.6-flash"
        return cls.GEMINI_MODEL

    @classmethod
    def get_effective_classifier_model(cls) -> str:
        if cls.USE_MOCK_LLM or not cls.is_api_key_available():
            return "mock-gemini-3.6-flash"
        return cls.CLASSIFIER_MODEL

