"""MEK advanced bibliographic search via the detailed search page."""

from __future__ import annotations

from mek_mcp.clients.detailed_scraper import DetailedSearchParams, scrape_detailed_search
from mek_mcp.models import SearchResult
from mek_mcp.parsers.results import parse_advanced_results, parse_total_hits
from mek_mcp.urls import ADVANCED_SEARCH_URL

# Human-friendly field names → MEK catalog field values (s1–s5 options).
FIELD_ALIASES: dict[str, str] = {
    "title": "dc_title main",
    "subtitle": "dc_title subtitle",
    "author": "dc_creator_o FamilyGivenName",
    "contributor": "dc_contributor_o FamilyGivenName",
    "subject": "dc_subject keyword",
    "geographic": "dc_subject geographic",
    "period": "dc_subject period",
    "type": "dc_type dc_type",
    "format": "dc_format format_name",
    "language": "dc_language m_lang",
    "original_language": "dc_language original",
    "publisher": "dc_publisher pub_name",
    "series": "dc_title series",
    "rights": "dc_rights dc_cc",
}

SORT_ALIASES = {
    "title": "cimsz",
    "author": "szerzosz",
    "date": "idorend",
    "id": "idsz",
}


def search_advanced(
    *,
    field: str = "author",
    query: str = "",
    field2: str = "",
    query2: str = "",
    operator: str = "and",
    sort_by: str = "author",
    accent_insensitive: bool = False,
    page_size: int = 25,
) -> SearchResult:
    if not query.strip():
        raise ValueError("query is required")

    mek_field = FIELD_ALIASES.get(field, field)
    mek_field2 = FIELD_ALIASES.get(field2, field2) if field2 else ""

    html = scrape_detailed_search(
        DetailedSearchParams(
            field=mek_field,
            query=query,
            field2=mek_field2,
            query2=query2,
            operator=operator if operator in ("and", "or", "not") else "and",
            sort_by=SORT_ALIASES.get(sort_by, sort_by),
            accent_insensitive=accent_insensitive,
        )
    )

    documents = parse_advanced_results(html)
    return SearchResult(
        total_hits=parse_total_hits(html),
        page=1,
        page_size=page_size,
        documents=documents[:page_size],
        search_url=ADVANCED_SEARCH_URL,
    )
