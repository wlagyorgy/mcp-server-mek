"""HTTP client base for MEK requests."""

from __future__ import annotations

import os
import time

import httpx

DEFAULT_USER_AGENT = "MEK-MCP/0.1 (research; +https://github.com)"
DEFAULT_DELAY_MS = 1000


def build_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": os.getenv("MEK_USER_AGENT", DEFAULT_USER_AGENT),
        },
        follow_redirects=True,
        timeout=float(os.getenv("MEK_TIMEOUT_SEC", "60")),
    )


def request_delay() -> None:
    delay_ms = int(os.getenv("MEK_REQUEST_DELAY_MS", str(DEFAULT_DELAY_MS)))
    if delay_ms > 0:
        time.sleep(delay_ms / 1000.0)


def decode_response(response: httpx.Response) -> str:
    raw = response.content
    for encoding in ("utf-8", "iso-8859-2", "latin-2", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")
