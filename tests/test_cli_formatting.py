from src.presentation.cli.formatting import render_metrics_line, render_routing_badge, resolve_routing_badge


def test_cache_hit_badge_takes_priority_over_intent():
    label, style = resolve_routing_badge(intent="INSTITUTIONAL", cache_status="HIT_EXACT")
    assert "CACHE HIT" in label
    assert "green" in style


def test_greeting_badge_for_light_routing():
    label, _ = resolve_routing_badge(intent="GREETING", cache_status="MISS")
    assert "SAUDAÇÃO" in label


def test_institutional_badge_names_the_subagent():
    label, _ = resolve_routing_badge(intent="INSTITUTIONAL", cache_status="MISS")
    assert "InstitutionalAgent" in label


def test_movie_search_badge_names_the_subagent_and_tmdb():
    label, _ = resolve_routing_badge(intent="MOVIE_SEARCH", cache_status="MISS")
    assert "MovieCatalogAgent" in label
    assert "TMDB" in label


def test_unknown_intent_falls_back_to_generic_badge():
    label, _ = resolve_routing_badge(intent="UNKNOWN", cache_status="MISS")
    assert "GENÉRICO" in label


def test_render_routing_badge_wraps_label_in_rich_markup():
    markup = render_routing_badge("GREETING", "MISS")
    assert markup.startswith("[")
    assert "SAUDAÇÃO" in markup


def test_render_metrics_line_includes_all_fields():
    line = render_metrics_line({
        "latency_ms": 12.34,
        "total_tokens": 420,
        "intent": "MOVIE_SEARCH",
        "cache_status": "MISS",
    })
    assert "12.34" in line
    assert "420" in line
    assert "MOVIE_SEARCH" in line
    assert "MISS" in line
