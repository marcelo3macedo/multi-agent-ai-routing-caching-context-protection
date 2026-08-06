import asyncio
import time
import re
import difflib
from typing import Optional, Tuple, Dict
from src.domain.interfaces.cache_repository import ICacheRepository
from src.infrastructure.config.settings import Settings

try:
    import redis.asyncio as aioredis
except ImportError:
    import redis as aioredis  # Fallback

def normalize_key(text: str) -> str:
    """Normaliza texto para chave de cache (lowercase, sem pontuação, sem espaços extras)."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    return ' '.join(text.split())

class DualModeRedisCache(ICacheRepository):
    """
    Repositório de Cache Híbrido (Redis Real + Fallback em Memória de Alta Performance).
    
    Implementa suporte a busca exata (Exact Cache) e similaridade semântica (Semantic Cache)
    com latência sub-10ms.
    """
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or Settings.REDIS_URL
        self._memory_store: Dict[str, Tuple[str, float]] = {}  # key -> (value, expire_at)
        self._raw_queries: Dict[str, str] = {}  # normalized_key -> original_query
        self._redis_client = None
        self._is_redis_available = False
        self._hits_exact = 0
        self._hits_semantic = 0
        self._misses = 0
        self._init_attempted = False

    async def _get_redis(self):
        if not self._init_attempted:
            self._init_attempted = True
            try:
                client = aioredis.from_url(self.redis_url, socket_connect_timeout=1.0)
                await client.ping()
                self._redis_client = client
                self._is_redis_available = True
            except Exception:
                self._is_redis_available = False
                self._redis_client = None
        return self._redis_client

    async def get_exact(self, key: str) -> Optional[str]:
        norm_key = normalize_key(key)
        
        client = await self._get_redis()
        if self._is_redis_available and client:
            try:
                val = await client.get(f"cache:exact:{norm_key}")
                if val:
                    self._hits_exact += 1
                    return val.decode("utf-8") if isinstance(val, bytes) else str(val)
            except Exception:
                pass

        # Fallback para In-Memory Cache
        now = time.time()
        if norm_key in self._memory_store:
            val, expire_at = self._memory_store[norm_key]
            if expire_at > now:
                self._hits_exact += 1
                return val
            else:
                del self._memory_store[norm_key]

        return None

    async def find_semantic(self, query: str, threshold: float = 0.85) -> Optional[Tuple[str, str]]:
        """
        Pesquisa similaridade semântica/léxica avançada entre a query do usuário e as chaves em cache.
        Retorna (resposta_em_cache, chave_similar) se o score for maior que o threshold.
        """
        norm_query = normalize_key(query)
        
        # Primeiro tenta exact match
        exact_res = await self.get_exact(query)
        if exact_res:
            return exact_res, norm_query

        # Tenta semântica fuzzy nos registros armazenados
        best_match = None
        best_ratio = 0.0

        now = time.time()
        for stored_norm_key, (cached_val, expire_at) in list(self._memory_store.items()):
            if expire_at <= now:
                continue
            
            ratio = difflib.SequenceMatcher(None, norm_query, stored_norm_key).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = cached_val

        if best_match and best_ratio >= threshold:
            self._hits_semantic += 1
            return best_match, norm_query

        self._misses += 1
        return None

    async def set(self, key: str, value: str, ttl_seconds: int = 3600) -> None:
        norm_key = normalize_key(key)
        expire_at = time.time() + ttl_seconds
        
        # Armazena na memória interna
        self._memory_store[norm_key] = (value, expire_at)
        self._raw_queries[norm_key] = key

        client = await self._get_redis()
        if self._is_redis_available and client:
            try:
                await client.set(f"cache:exact:{norm_key}", value, ex=ttl_seconds)
            except Exception:
                pass

    async def get_stats(self) -> dict:
        total_queries = self._hits_exact + self._hits_semantic + self._misses
        hit_rate = ((self._hits_exact + self._hits_semantic) / total_queries * 100.0) if total_queries > 0 else 0.0
        
        return {
            "mode": "Redis" if self._is_redis_available else "InMemory (Redis Fallback)",
            "hits_exact": self._hits_exact,
            "hits_semantic": self._hits_semantic,
            "total_hits": self._hits_exact + self._hits_semantic,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cached_entries_count": len(self._memory_store)
        }
