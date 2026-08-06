from pydantic import BaseModel, Field
from typing import Optional, List

class ChatRequestDTO(BaseModel):
    message: str = Field(..., description="Mensagem do usuário", json_schema_extra={"example": "Bom dia"})
    user_id: str = Field(default="user_default", description="Identificador do usuário")
    session_id: Optional[str] = Field(default=None, description="ID da sessão")
    enable_cache: bool = Field(default=True, description="Habilitar busca em cache")
    enable_routing: bool = Field(default=True, description="Habilitar roteamento por classificador de intenção")

class MetricsDTO(BaseModel):
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    intent: str
    cache_status: str
    is_mock: bool
    tokens_saved: int
    problem_tags: List[str]

class ChatResponseDTO(BaseModel):
    response: str
    session_id: str
    user_id: str
    metrics: MetricsDTO
