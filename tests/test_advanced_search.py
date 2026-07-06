"""Tests for advanced search scraping and parsing."""

from pathlib import Path

import pytest

from mek_mcp.clients.advanced_search import search_advanced
from mek_mcp.parsers.results import parse_advanced_results, parse_total_hits
from mek_mcp.urls import ADVANCED_SEARCH_URL

FIXTURES = Path(__file__).parent / "fixtures"


def test_advanced_search_url_constant():
    assert ADVANCED_SEARCH_URL == "https://www.mek.oszk.hu/hu/search/detailed/"


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
    result = await search_advanced(field="author", query="Arany", page_size=5)
    assert result.search_url == ADVANCED_SEARCH_URL
    assert result.total_hits is not None and result.total_hits >= 40
    assert len(result.documents) == 5
    assert result.documents[0].mek_id
