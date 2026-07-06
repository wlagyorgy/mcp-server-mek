"""MEK full-text search (elfulltext)."""

from __future__ import annotations

from mek_mcp.clients.base import build_client, decode_response, request_delay
from mek_mcp.models import SearchResult
from mek_mcp.parsers.results import parse_simple_or_fulltext_results, parse_total_hits

from mek_mcp.urls import FULLTEXT_SEARCH_URL as FULLTEXT_URL

BROADTOPIC_ALIASES: dict[str, str] = {
    "": "",
    "all": "",
    "science": "természettudományok és matematika",
    "technical": "műszaki tudományok, gazdasági ágazatok",
    "social": "társadalomtudományok",
    "humanities": "humán területek, kultúra, irodalom",
    "reference": "kézikönyvek és egyéb műfajok",
}


def search_fulltext(
    *,
    query: str,
    broadtopic: str = "",
    page_size: int = 10,
    page: int = 1,
) -> SearchResult:
    if not query.strip():
        raise ValueError("query is required")

    page_size = max(1, min(page_size, 100))
    offset = (max(1, page) - 1) * page_size
    topic = BROADTOPIC_ALIASES.get(broadtopic, broadtopic)

    data = {
        "body": query,
        "broadtopic": topic,
        "size": str(page_size),
        "sort": "",
        "from": str(offset) if offset else "",
    }

    request_delay()
    with build_client() as client:
        response = client.post(FULLTEXT_URL, data=data)
        response.raise_for_status()
        html = decode_response(response)

    documents = parse_simple_or_fulltext_results(html)
    return SearchResult(
        total_hits=parse_total_hits(html),
        page=page,
        page_size=page_size,
        documents=documents[:page_size],
        search_url=FULLTEXT_URL,
    )
