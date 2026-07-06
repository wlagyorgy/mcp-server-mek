"""MEK simple (elfull) bibliographic search."""

from __future__ import annotations

from mek_mcp.clients.base import build_client, decode_response, request_delay
from mek_mcp.models import SearchResult
from mek_mcp.parsers.results import parse_simple_or_fulltext_results, parse_total_hits

from mek_mcp.urls import SIMPLE_SEARCH_URL as SIMPLE_URL


def search_simple(
    *,
    title: str = "",
    subject: str = "",
    creator: str = "",
    mek_id: str = "",
    page_size: int = 10,
    page: int = 1,
) -> SearchResult:
    if not any((title, subject, creator, mek_id)):
        raise ValueError("At least one of title, subject, creator, or mek_id is required")

    page_size = max(1, min(page_size, 100))
    offset = (max(1, page) - 1) * page_size

    data = {
        "dc_title": title,
        "dc_subject": subject,
        "dc_creator": creator,
        "id": mek_id,
        "size": str(page_size),
        "sort": "",
        "from": str(offset) if offset else "",
    }

    request_delay()
    with build_client() as client:
        response = client.post(SIMPLE_URL, data=data)
        response.raise_for_status()
        html = decode_response(response)

    documents = parse_simple_or_fulltext_results(html)
    return SearchResult(
        total_hits=parse_total_hits(html),
        page=page,
        page_size=page_size,
        documents=documents[:page_size],
        search_url=SIMPLE_URL,
    )
