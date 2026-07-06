"""MEK MCP server — search tools for the Hungarian Electronic Library."""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from mek_mcp.clients.advanced_search import FIELD_ALIASES, search_advanced
from mek_mcp.clients.fulltext_search import BROADTOPIC_ALIASES, search_fulltext
from mek_mcp.clients.simple_search import search_simple

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8000
_DEFAULT_SSE_PATH = "/sse"
_DEFAULT_MESSAGE_PATH = "/messages/"

mcp = FastMCP(
    "mek",
    instructions=(
        "Search the Hungarian Electronic Library (MEK, mek.oszk.hu). "
        "Use mek_search_simple for author/title/subject lookups. "
        "Use mek_search_fulltext to search inside document text (HTML/PDF). "
        "Use mek_search_advanced for field-specific queries with AND/OR/NOT "
        "(uses browser scraping on the detailed search page)."
    ),
    host=os.getenv("HOST", _DEFAULT_HOST),
    port=int(os.getenv("PORT", str(_DEFAULT_PORT))),
    sse_path=os.getenv("MCP_SSE_PATH", _DEFAULT_SSE_PATH),
    message_path=os.getenv("MCP_MESSAGE_PATH", _DEFAULT_MESSAGE_PATH),
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    """Render health check endpoint."""
    return JSONResponse({"status": "ok", "service": "mek-mcp"})


def _dump(result) -> dict:
    return result.model_dump()


@mcp.tool()
def mek_search_simple(
    creator: str = "",
    title: str = "",
    subject: str = "",
    mek_id: str = "",
    page_size: int = 10,
    page: int = 1,
) -> dict:
    """Search MEK bibliographic metadata (simple search).

    All provided fields are combined with AND logic. Supports wildcards with *.
    At least one of creator, title, subject, or mek_id must be provided.

    Args:
        creator: Author, editor, or translator name (e.g. "Ady", "Petőfi").
        title: Book title or part of title.
        subject: Theme, keyword, or topic.
        mek_id: MEK document ID number.
        page_size: Results per page (10, 50, or 100).
        page: Page number (1-based).
    """
    return _dump(
        search_simple(
            creator=creator,
            title=title,
            subject=subject,
            mek_id=mek_id,
            page_size=page_size,
            page=page,
        )
    )


@mcp.tool()
def mek_search_fulltext(
    query: str,
    broadtopic: str = "",
    page_size: int = 10,
    page: int = 1,
) -> dict:
    """Search inside MEK document full text (HTML and PDF).

    Args:
        query: Words or phrase to find in document bodies. Use quotes for exact phrases.
        broadtopic: Optional collection filter: "", "science", "technical", "social",
            "humanities", "reference", or the full Hungarian topic string.
        page_size: Results per page (10, 50, or 100).
        page: Page number (1-based).
    """
    return _dump(
        search_fulltext(
            query=query,
            broadtopic=broadtopic,
            page_size=page_size,
            page=page,
        )
    )


@mcp.tool()
def mek_search_advanced(
    query: str,
    field: str = "author",
    field2: str = "",
    query2: str = "",
    operator: str = "and",
    sort_by: str = "author",
    accent_insensitive: bool = False,
) -> dict:
    """Advanced MEK bibliographic search with field selection and boolean logic.

    Args:
        query: Search term for the primary field.
        field: Primary field — one of: title, author, subject, language, format,
            type, publisher, series, rights, geographic, period, contributor,
            or a raw MEK field value.
        field2: Optional second field name (same options as field).
        query2: Optional second search term (combined with operator).
        operator: How to combine rows: "and", "or", or "not".
        sort_by: Sort results by "title", "author", "date", or "id".
        accent_insensitive: Search without Hungarian accents when True.
    """
    return _dump(
        search_advanced(
            field=field,
            query=query,
            field2=field2,
            query2=query2,
            operator=operator,
            sort_by=sort_by,
            accent_insensitive=accent_insensitive,
        )
    )


@mcp.tool()
def mek_list_search_fields() -> dict:
    """List available field names for mek_search_advanced and fulltext topic filters."""
    return {
        "advanced_fields": sorted(FIELD_ALIASES.keys()),
        "fulltext_topics": sorted(BROADTOPIC_ALIASES.keys()),
    }


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()

    if transport == "stdio":
        mcp.run(transport="stdio")
        return

    if transport == "sse":
        mcp.run(transport="sse")
        return

    raise ValueError(
        f"Unsupported MCP_TRANSPORT={transport!r}. Use 'stdio' (local) or 'sse' (Render/remote)."
    )


if __name__ == "__main__":
    main()
