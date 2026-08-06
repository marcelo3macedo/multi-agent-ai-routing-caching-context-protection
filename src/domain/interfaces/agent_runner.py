from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, Dict, Any
from src.domain.entities.metrics import QueryMetrics

class IAgentRunner(ABC):
    @abstractmethod
    async def execute_query(
        self, user_query: str, user_id: str = "default_user", session_id: Optional[str] = None
    ) -> QueryMetrics:
        """Executa consulta no runner e retorna métricas acumuladas."""
        pass

    @abstractmethod
    async def stream_query(
        self, user_query: str, user_id: str = "default_user", session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Transmite deltas e evento de conclusão."""
        pass
