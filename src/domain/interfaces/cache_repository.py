from abc import ABC, abstractmethod
from typing import Optional, Tuple
from src.domain.entities.metrics import CacheStatus

class ICacheRepository(ABC):
    @abstractmethod
    async def get_exact(self, key: str) -> Optional[str]:
        """Recupera valor por chave exata."""
        pass

    @abstractmethod
    async def find_semantic(self, query: str, threshold: float = 0.85) -> Optional[Tuple[str, str]]:
        """Recupera resposta por similaridade semântica se disponível."""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl_seconds: int = 3600) -> None:
        """Armazena par chave-valor no cache."""
        pass

    @abstractmethod
    async def get_stats(self) -> dict:
        """Retorna estatísticas de cache hits e miss."""
        pass
