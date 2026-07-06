"""HTML parsers for MEK search result pages."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from mek_mcp.models import MekDocument

MEK_URL_RE = re.compile(
    r"https?://(?:www\.)?mek\.oszk\.hu/(\d+)/(\d+)",
    re.I,
)
HITS_RE = re.compile(r"tal[aá]latok sz[aá]ma:\s*(\d+)", re.I)


def _normalize_url(folder: str, doc_id: str) -> str:
    return f"https://mek.oszk.hu/{folder}/{doc_id}"


def parse_total_hits(html: str) -> int | None:
    match = HITS_RE.search(html)
    return int(match.group(1)) if match else None


def parse_simple_or_fulltext_results(html: str) -> list[MekDocument]:
    """Parse elfull / elfulltext result pages."""
    soup = BeautifulSoup(html, "lxml")
    documents: list[MekDocument] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        match = MEK_URL_RE.search(href) or MEK_URL_RE.search(urljoin("https://mek.oszk.hu", href))
        if not match:
            continue
        url = _normalize_url(match.group(1), match.group(2))
        if url in seen:
            continue
        seen.add(url)
        title = anchor.get_text(" ", strip=True) or None
        documents.append(
            MekDocument(
                mek_id=match.group(2),
                title=title,
                url=url,
            )
        )
    return documents


def parse_advanced_results(html: str) -> list[MekDocument]:
    """Parse kataluj.php3 result list (.hit blocks)."""
    soup = BeautifulSoup(html, "lxml")
    documents: list[MekDocument] = []

    for hit in soup.select(".hit"):
        text = hit.get_text("\n", strip=True)
        url_match = MEK_URL_RE.search(str(hit))
        if not url_match:
            continue
        url = _normalize_url(url_match.group(1), url_match.group(2))
        lines = [line for line in text.splitlines() if line.strip()]
        title = lines[0] if lines else None
        documents.append(
            MekDocument(
                mek_id=url_match.group(2),
                title=title,
                url=url,
                snippet="\n".join(lines[1:3]) if len(lines) > 1 else None,
            )
        )
    return documents
