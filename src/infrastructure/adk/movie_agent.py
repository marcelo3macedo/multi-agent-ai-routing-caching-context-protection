from google.adk.agents import LlmAgent
from src.infrastructure.config.settings import Settings
from src.infrastructure.adk.prompts import MOVIE_CATALOG_SYSTEM_INSTRUCTION
from src.infrastructure.adk.tmdb_tool import tmdb_movie_tool


def create_movie_catalog_agent(model_name: str = None) -> LlmAgent:
    """
    Cria o MovieCatalogAgent: sub-agente ADK especializado em busca e recomendação
    de filmes, apoiado pela TMDBMovieTool (integração real com a API do TMDB).
    """
    effective_model = model_name or Settings.get_effective_model()

    return LlmAgent(
        name="MovieCatalogAgent",
        model=effective_model,
        instruction=MOVIE_CATALOG_SYSTEM_INSTRUCTION.strip(),
        description=(
            "Especialista em busca e recomendação de filmes via catálogo real do TMDB "
            "(The Movie Database)."
        ),
        tools=[tmdb_movie_tool],
    )
