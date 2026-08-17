from dataclasses import dataclass
from typing import Optional, Dict, Any
from src.domain.entities.metrics import QueryMetrics, CacheStatus

@dataclass
class ChatMessage:
    content: str
    user_id: str = "default_user"
    session_id: Optional[str] = None

@dataclass
class ChatResponse:
    text: str
    session_id: str
    user_id: str
    metrics: QueryMetrics
