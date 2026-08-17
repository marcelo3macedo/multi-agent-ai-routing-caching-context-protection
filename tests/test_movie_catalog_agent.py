from datetime import date
from unittest.mock import AsyncMock

import httpx
import pytest

from src.infrastructure.adk.tmdb_tool import (
    RELEVANT_MOVIE_FIELDS,
    resolve_genre_id,
    search_movies,
    truncate_movie_payload,
)
from src.infrastructure.adk.movie_agent import create_movie_catalog_agent
from src.infrastructure.adk.agent import create_root_agent
from src.infrastructure.config.settings import Settings


RAW_TMDB_MOVIE = {
    "id": 603,
    "title": "The Matrix",
    "overview": "Um hacker descobre a verdade sobre sua realidade.",
    "release_date": "1999-03-30",
    "vote_average": 8.2,
    # Campos que devem ser descartados pela truncagem inteligente:
    "popularity": 123.456,
    "backdrop_path": "/some_backdrop.jpg",
    "adult": False,
    "genre_ids": [28, 878],
    "original_language": "en",
    "poster_path": "/some_poster.jpg",
    "video": False,
    "vote_count": 25000,
    "original_title": "The Matrix",
}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_truncate_movie_payload_keeps_only_relevant_fields():
    truncated = truncate_movie_payload([RAW_TMDB_MOVIE])
    assert len(truncated) == 1
    movie = truncated[0]

    assert set(movie.keys()) == set(RELEVANT_MOVIE_FIELDS)
    assert movie["id"] == 603
    assert movie["title"] == "The Matrix"
    assert movie["vote_average"] == 8.2

    for irrelevant_field in ("popularity", "backdrop_path", "adult", "genre_ids", "poster_path", "vote_count"):
        assert irrelevant_field not in movie


def test_resolve_genre_id_handles_accents_and_unknown_genres():
    assert resolve_genre_id("Ficção Científica") == 878
    assert resolve_genre_id("ficcao cientifica") == 878
    assert resolve_genre_id("acao") == 28
    assert resolve_genre_id("gênero inexistente") is None


@pytest.mark.asyncio
async def test_search_movies_without_api_key_returns_clear_message(monkeypatch):
    monkeypatch.setattr(Settings, "TMDB_API_KEY", "")
    get_mock = AsyncMock()
    monkeypatch.setattr(httpx.AsyncClient, "get", get_mock)

    result = await search_movies(query="Matrix")

    assert isinstance(result, str)
    assert "TMDB_API_KEY" in result
    get_mock.assert_not_called()


@pytest.mark.asyncio
async def test_search_movies_by_query_hits_search_endpoint_and_truncates(monkeypatch):
    monkeypatch.setattr(Settings, "TMDB_API_KEY", "fake-tmdb-key")
    get_mock = AsyncMock(return_value=FakeResponse({"results": [RAW_TMDB_MOVIE]}))
    monkeypatch.setattr(httpx.AsyncClient, "get", get_mock)

    result = await search_movies(query="Matrix")

    endpoint, kwargs = get_mock.call_args.args[0], get_mock.call_args.kwargs
    assert endpoint == "/search/movie"
    assert kwargs["params"]["query"] == "Matrix"
    assert result == [{
        "id": 603,
        "title": "The Matrix",
        "overview": "Um hacker descobre a verdade sobre sua realidade.",
        "release_date": "1999-03-30",
        "vote_average": 8.2,
    }]


@pytest.mark.asyncio
async def test_search_movies_by_genre_and_year_hits_discover_endpoint(monkeypatch):
    monkeypatch.setattr(Settings, "TMDB_API_KEY", "fake-tmdb-key")
    get_mock = AsyncMock(return_value=FakeResponse({"results": [RAW_TMDB_MOVIE]}))
    monkeypatch.setattr(httpx.AsyncClient, "get", get_mock)

    result = await search_movies(genre="ficção científica", year=1999)

    endpoint, kwargs = get_mock.call_args.args[0], get_mock.call_args.kwargs
    assert endpoint == "/discover/movie"
    assert kwargs["params"]["with_genres"] == 878
    assert kwargs["params"]["primary_release_year"] == 1999
    assert len(result) == 1


@pytest.mark.asyncio
async def test_search_movies_unknown_genre_short_circuits_without_network_call(monkeypatch):
    monkeypatch.setattr(Settings, "TMDB_API_KEY", "fake-tmdb-key")
    get_mock = AsyncMock()
    monkeypatch.setattr(httpx.AsyncClient, "get", get_mock)

    result = await search_movies(genre="gênero que não existe")

    assert isinstance(result, str)
    assert "não reconhecido" in result
    get_mock.assert_not_called()


def test_create_movie_catalog_agent_is_scoped_and_tooled():
    agent = create_movie_catalog_agent(model_name="mock-model-gemini-3.6-flash")
    assert agent.name == "MovieCatalogAgent"
    assert len(agent.tools) == 1
    assert agent.tools[0].name == "search_movies"


def test_create_movie_catalog_agent_instruction_embeds_current_date_for_release_awareness():
    agent = create_movie_catalog_agent(
        model_name="mock-model-gemini-3.6-flash", current_date=date(2026, 8, 17)
    )
    assert "2026-08-17" in agent.instruction
    assert "já foi lançado" in agent.instruction.lower()
    assert "mais bem avaliado" in agent.instruction.lower()


def test_create_root_agent_delegates_to_institutional_and_movie_subagents():
    root_agent = create_root_agent(model_name="mock-model-gemini-3.6-flash")
    sub_agent_names = {sub.name for sub in root_agent.sub_agents}
    assert sub_agent_names == {"InstitutionalAgent", "MovieCatalogAgent"}
