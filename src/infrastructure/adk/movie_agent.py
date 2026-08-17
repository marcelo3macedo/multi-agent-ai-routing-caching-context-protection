from datetime import date

from google.adk.agents import LlmAgent
from src.infrastructure.config.settings import Settings
from src.infrastructure.adk.prompts import build_movie_catalog_instruction
from src.infrastructure.adk.tmdb_tool import tmdb_movie_tool
from src.infrastructure.adk.tool_logging import log_after_tool_call, log_before_tool_call, log_tool_error


def create_movie_catalog_agent(model_name: str = None, current_date: date = None) -> LlmAgent:
    """
    Cria o MovieCatalogAgent: sub-agente ADK especializado em busca e recomendação
    de filmes, apoiado pela TMDBMovieTool (integração real com a API do TMDB).
    """
    effective_model = model_name or Settings.get_effective_model()
    effective_date = current_date or date.today()

    return LlmAgent(
        name="MovieCatalogAgent",
        model=effective_model,
        instruction=build_movie_catalog_instruction(effective_date).strip(),
        description=(
            "Especialista em busca e recomendação de filmes via catálogo real do TMDB "
            "(The Movie Database)."
        ),
        tools=[tmdb_movie_tool],
        before_tool_callback=log_before_tool_call,
        after_tool_callback=log_after_tool_call,
        on_tool_error_callback=log_tool_error,
    )
