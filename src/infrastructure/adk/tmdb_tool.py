import unicodedata
from typing import Any, Dict, List, Optional

import httpx

from google.adk.tools import FunctionTool
from src.infrastructure.config.settings import Settings

# Campos entregues à LLM. Qualquer campo do TMDB fora desta lista é descartado
# na truncagem (ex: popularity, backdrop_path, adult, genre_ids, poster_path,
# vote_count, original_language, video), protegendo o contexto contra overflow.
RELEVANT_MOVIE_FIELDS = ("id", "title", "overview", "release_date", "vote_average")

GENRE_NAME_TO_ID = {
    "acao": 28,
    "aventura": 12,
    "animacao": 16,
    "comedia": 35,
    "crime": 80,
    "documentario": 99,
    "drama": 18,
    "familia": 10751,
    "fantasia": 14,
    "historia": 36,
    "terror": 27,
    "musical": 10402,
    "misterio": 9648,
    "romance": 10749,
    "ficcao cientifica": 878,
    "sci-fi": 878,
    "cinema tv": 10770,
    "suspense": 53,
    "guerra": 10752,
    "faroeste": 37,
}


def _normalize(text: str) -> str:
    """Remove acentos e normaliza para minúsculas (ex: 'Ficção Científica' -> 'ficcao cientifica')."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_accents.lower().strip()


def resolve_genre_id(genre: str) -> Optional[int]:
    """Resolve o nome de um gênero (PT-BR ou EN) para o ID de gênero do TMDB."""
    return GENRE_NAME_TO_ID.get(_normalize(genre))


def truncate_movie_payload(raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Smart Context Truncation: reduz o payload gigante do TMDB apenas aos campos
    relevantes (id, title, overview, release_date, vote_average), protegendo a
    janela de contexto da LLM contra Context Overflow.
    """
    return [
        {field: movie.get(field) for field in RELEVANT_MOVIE_FIELDS if field in movie}
        for movie in raw_results
    ]


async def _tmdb_get(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    request_params = {**params, "api_key": Settings.TMDB_API_KEY, "language": "pt-BR"}
    async with httpx.AsyncClient(base_url=Settings.TMDB_BASE_URL, timeout=10.0) as client:
        response = await client.get(endpoint, params=request_params)
        response.raise_for_status()
        return response.json()


async def search_movies(
    query: Optional[str] = None,
    genre: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 5,
) -> List[Dict[str, Any]] | str:
    """
    Consulta o catálogo real de filmes do TMDB (The Movie Database).

    Use `query` para buscar por nome de filme (endpoint /search/movie). Use `genre`
    e/ou `year` sem `query` para descobrir filmes por gênero e/ou ano de lançamento
    (endpoint /discover/movie). Os resultados retornados já vêm truncados apenas aos
    campos essenciais (id, title, overview, release_date, vote_average).

    Args:
        query: Nome (ou parte do nome) do filme buscado.
        genre: Gênero desejado (ex: "ação", "ficção científica", "comédia").
        year: Ano de lançamento desejado.
        limit: Quantidade máxima de filmes retornados (padrão: 5).

    Returns:
        Lista de filmes truncados, ou uma mensagem de erro/orientação em string.
    """
    if not Settings.is_tmdb_key_available():
        return (
            "TMDB_API_KEY não configurada. Configure a chave em .env para habilitar "
            "consultas reais ao catálogo de filmes."
        )

    try:
        if query:
            payload = await _tmdb_get(
                "/search/movie",
                {"query": query, **({"year": year} if year else {})},
            )
        else:
            genre_id = resolve_genre_id(genre) if genre else None
            if genre and genre_id is None:
                available = ", ".join(sorted(set(GENRE_NAME_TO_ID.keys())))
                return f"Gênero '{genre}' não reconhecido. Gêneros disponíveis: {available}."

            discover_params: Dict[str, Any] = {"sort_by": "popularity.desc"}
            if genre_id:
                discover_params["with_genres"] = genre_id
            if year:
                discover_params["primary_release_year"] = year

            payload = await _tmdb_get("/discover/movie", discover_params)
    except httpx.HTTPError as e:
        return f"Erro ao consultar o TMDB: {e}"

    results = payload.get("results", [])
    return truncate_movie_payload(results[:limit])


# ADK deriva o nome de function-calling exposto à LLM a partir de func.__name__,
# então o tool é registrado (e chamado pela LLM) como "search_movies".
tmdb_movie_tool = FunctionTool(func=search_movies)
