from abc import ABC, abstractmethod
from src.domain.entities.intent import IntentResult

class IIntentClassifier(ABC):
    @abstractmethod
    async def classify(self, text: str) -> IntentResult:
        """Classifica a intenção do texto em GREETING, INSTITUTIONAL, MOVIE_SEARCH ou UNKNOWN."""
        pass
