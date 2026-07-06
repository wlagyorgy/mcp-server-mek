"""Pydantic models for MEK search results."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MekDocument(BaseModel):
    mek_id: str | None = None
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    url: str
    snippet: str | None = None
    date: str | None = None


class SearchResult(BaseModel):
    total_hits: int | None = None
    page: int = 1
    page_size: int = 10
    documents: list[MekDocument] = Field(default_factory=list)
    search_url: str = ""
