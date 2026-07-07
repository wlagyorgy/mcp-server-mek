"""Tests for advanced search scraping and parsing."""

from pathlib import Path

import pytest

from mek_mcp.clients.advanced_search import (
    FIELD_ALIASES,
    FIELD_VALUES,
    build_detailed_search_params,
    build_search_operators,
    build_search_rows,
    resolve_field,
    search_advanced,
)
from mek_mcp.parsers.results import parse_advanced_results, parse_total_hits
from mek_mcp.urls import ADVANCED_SEARCH_URL

FIXTURES = Path(__file__).parent / "fixtures"


def test_advanced_search_url_constant():
    assert ADVANCED_SEARCH_URL == "https://www.mek.oszk.hu/hu/search/detailed/"


def test_field_aliases_cover_all_mek_select_options():
    assert len(FIELD_VALUES) == 24
    assert resolve_field("summary_title") == "dc_title PartOf"
    assert resolve_field("corporate_author") == "CorporateAuthor Cauth_name"
    assert resolve_field("copyright_owner") == "dc_rights owner"
    assert resolve_field("dc_title main") == "dc_title main"


def test_build_search_rows_legacy_and_criteria():
    rows = build_search_rows(field="author", query="Arany", field2="subject", query2="költészet")
    assert len(rows) == 2
    assert rows[0].field == FIELD_ALIASES["author"]
    assert rows[1].field == FIELD_ALIASES["subject"]

    criteria_rows = build_search_rows(
        criteria=[
            {"field": "title", "query": "Toldi"},
            {"field": "author", "query": "Arany"},
            {"field": "language", "query": "magyar"},
        ]
    )
    assert len(criteria_rows) == 3
    assert criteria_rows[2].field == FIELD_ALIASES["language"]


def test_build_search_operators_defaults_and_custom():
    assert build_search_operators(1) == []
    assert build_search_operators(3) == ["and", "and"]
    assert build_search_operators(3, operator="or", operator2="not") == ["or", "not"]
    assert build_search_operators(4, operators=["or", "and"]) == ["or", "and", "and"]


def test_build_detailed_search_params_full_form():
    params = build_detailed_search_params(
        field="author",
        query="Arany",
        field2="subject",
        query2="ballada",
        field3="language",
        query3="magyar",
        operator="and",
        operator2="or",
        sort_by="title",
        accent_insensitive=True,
        include_processing=True,
    )
    assert len(params.rows) == 3
    assert params.operators == ["and", "or"]
    assert params.sort_by == "cimsz"
    assert params.accent_insensitive is True
    assert params.include_processing is True


def test_build_search_rows_requires_query():
    with pytest.raises(ValueError, match="At least one"):
        build_search_rows(field="author", query="")


def test_parse_advanced_fixture():
    html = (FIXTURES / "advanced_arany_result.html").read_text(encoding="utf-8")
    total = parse_total_hits(html)
    documents = parse_advanced_results(html)
    assert total == 48
    assert len(documents) >= 20
    assert any("Arany" in (doc.title or "") for doc in documents)


@pytest.mark.network
@pytest.mark.asyncio
async def test_live_advanced_search_scrape():
    result = await search_advanced(field="author", query="Arany", max_results=5)
    assert result.search_url == ADVANCED_SEARCH_URL
    assert result.total_hits is not None and result.total_hits >= 40
    assert len(result.documents) == 5
    assert result.documents[0].mek_id
