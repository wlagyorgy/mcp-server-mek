"""MEK advanced bibliographic search via the detailed search page."""

from __future__ import annotations

from mek_mcp.clients.detailed_scraper import (
    DetailedSearchParams,
    SearchRow,
    scrape_detailed_search,
)
from mek_mcp.models import SearchResult
from mek_mcp.parsers.results import parse_advanced_results, parse_total_hits
from mek_mcp.urls import ADVANCED_SEARCH_URL

FIELD_ALIASES: dict[str, str] = {
    "title": "dc_title main",
    "subtitle": "dc_title subtitle",
    "summary_title": "dc_title PartOf",
    "part_title": "dc_title parts",
    "parallel_title": "dc_title alternative",
    "original_title": "dc_title original",
    "series": "dc_title series",
    "author": "dc_creator_o FamilyGivenName",
    "author_role": "dc_creator_o role",
    "corporate_author": "CorporateAuthor Cauth_name",
    "contributor": "dc_contributor_o FamilyGivenName",
    "contributor_role": "dc_contributor_o role",
    "publisher": "dc_publisher pub_name",
    "subject": "dc_subject keyword",
    "geographic": "dc_subject geographic",
    "period": "dc_subject period",
    "type": "dc_type dc_type",
    "format": "dc_format format_name",
    "language": "dc_language m_lang",
    "original_language": "dc_language original",
    "printed_source": "PrintedSource PrintedSource",
    "copyright_owner": "dc_rights owner",
    "legal_note": "dc_rights other",
    "rights": "dc_rights dc_cc",
    "creative_commons": "dc_rights dc_cc",
}

FIELD_VALUES: frozenset[str] = frozenset(FIELD_ALIASES.values())

SORT_ALIASES = {
    "title": "cimsz",
    "author": "szerzosz",
    "date": "idorend",
    "id": "idsz",
}

VALID_OPERATORS = frozenset({"and", "or", "not"})
MAX_ROWS = 5


def resolve_field(field: str) -> str:
    return FIELD_ALIASES.get(field, field)


def normalize_operator(operator: str) -> str:
    return operator if operator in VALID_OPERATORS else "and"


def build_search_rows(
    *,
    field: str = "author",
    query: str = "",
    field2: str = "",
    query2: str = "",
    field3: str = "",
    query3: str = "",
    field4: str = "",
    query4: str = "",
    field5: str = "",
    query5: str = "",
    criteria: list[dict[str, str]] | None = None,
) -> list[SearchRow]:
    """Build up to five search rows from explicit criteria or legacy row params."""
    if criteria is not None:
        rows = [
            SearchRow(field=resolve_field(item["field"]), query=item["query"].strip())
            for item in criteria
            if item.get("query", "").strip()
        ]
    else:
        legacy = [
            (field, query),
            (field2, query2),
            (field3, query3),
            (field4, query4),
            (field5, query5),
        ]
        rows = []
        for index, (row_field, row_query) in enumerate(legacy):
            if not row_query.strip():
                continue
            default_field = "author" if index == 0 else field
            rows.append(
                SearchRow(
                    field=resolve_field(row_field or default_field),
                    query=row_query.strip(),
                )
            )

    if not rows:
        raise ValueError("At least one search row with a non-empty query is required")
    if len(rows) > MAX_ROWS:
        raise ValueError(f"Advanced search supports at most {MAX_ROWS} criteria rows")
    return rows


def build_search_operators(
    row_count: int,
    *,
    operator: str = "and",
    operator2: str = "and",
    operator3: str = "and",
    operator4: str = "and",
    operators: list[str] | None = None,
) -> list[str]:
    """Return operators between rows (muv1..muv4), defaulting to AND."""
    if row_count < 1:
        raise ValueError("row_count must be at least 1")

    needed = row_count - 1
    if needed == 0:
        return []

    if operators is not None:
        normalized = [normalize_operator(op) for op in operators[:needed]]
    else:
        normalized = [
            normalize_operator(op)
            for op in (operator, operator2, operator3, operator4)[:needed]
        ]

    while len(normalized) < needed:
        normalized.append("and")
    return normalized


def build_detailed_search_params(
    *,
    field: str = "author",
    query: str = "",
    field2: str = "",
    query2: str = "",
    field3: str = "",
    query3: str = "",
    field4: str = "",
    query4: str = "",
    field5: str = "",
    query5: str = "",
    operator: str = "and",
    operator2: str = "and",
    operator3: str = "and",
    operator4: str = "and",
    criteria: list[dict[str, str]] | None = None,
    operators: list[str] | None = None,
    sort_by: str = "author",
    accent_insensitive: bool = False,
    include_processing: bool = False,
) -> DetailedSearchParams:
    rows = build_search_rows(
        field=field,
        query=query,
        field2=field2,
        query2=query2,
        field3=field3,
        query3=query3,
        field4=field4,
        query4=query4,
        field5=field5,
        query5=query5,
        criteria=criteria,
    )
    return DetailedSearchParams(
        rows=rows,
        operators=build_search_operators(
            len(rows),
            operator=operator,
            operator2=operator2,
            operator3=operator3,
            operator4=operator4,
            operators=operators,
        ),
        sort_by=SORT_ALIASES.get(sort_by, sort_by),
        accent_insensitive=accent_insensitive,
        include_processing=include_processing,
    )


async def search_advanced(
    *,
    field: str = "author",
    query: str = "",
    field2: str = "",
    query2: str = "",
    field3: str = "",
    query3: str = "",
    field4: str = "",
    query4: str = "",
    field5: str = "",
    query5: str = "",
    operator: str = "and",
    operator2: str = "and",
    operator3: str = "and",
    operator4: str = "and",
    criteria: list[dict[str, str]] | None = None,
    operators: list[str] | None = None,
    sort_by: str = "author",
    accent_insensitive: bool = False,
    include_processing: bool = False,
    max_results: int = 50,
) -> SearchResult:
    """Run advanced search; max_results only limits the returned list (MEK has no paging)."""
    params = build_detailed_search_params(
        field=field,
        query=query,
        field2=field2,
        query2=query2,
        field3=field3,
        query3=query3,
        field4=field4,
        query4=query4,
        field5=field5,
        query5=query5,
        operator=operator,
        operator2=operator2,
        operator3=operator3,
        operator4=operator4,
        criteria=criteria,
        operators=operators,
        sort_by=sort_by,
        accent_insensitive=accent_insensitive,
        include_processing=include_processing,
    )

    html = await scrape_detailed_search(params)
    documents = parse_advanced_results(html)
    max_results = max(1, max_results)
    return SearchResult(
        total_hits=parse_total_hits(html),
        page=1,
        page_size=max_results,
        documents=documents[:max_results],
        search_url=ADVANCED_SEARCH_URL,
    )
