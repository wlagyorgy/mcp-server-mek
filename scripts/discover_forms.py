#!/usr/bin/env python3
"""Discover MEK search form parameters and probe response structure."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

USER_AGENT = "MEK-MCP-Discovery/0.1 (+https://github.com; research tool)"
REQUEST_DELAY_SEC = 1.5
MEK_URL_RE = re.compile(r"https?://(?:www\.)?mek\.oszk\.hu/(\d+)/(\d+)", re.I)
RESULT_CLASS_HINTS = ("hit", "rlist", "rlistb", "numberofhits", "results", "oldresult")
PAGINATION_HINTS = re.compile(r"pageNextPrev|name=['\"]from['\"]", re.I)

SEARCH_PAGES: dict[str, str] = {
    "simple": "https://www.mek.oszk.hu/hu/search/elfull/",
    "advanced": "https://www.mek.oszk.hu/hu/search/detailed/",
    "fulltext_new": "https://www.mek.oszk.hu/hu/search/elfulltext/",
    "fulltext_legacy": "https://vmek.oszk.hu/kereses/",
    "legacy_simple_widget": "https://mek.oszk.hu/html/allando/mek2kereso.htm",
}

# Minimal probe payloads per form id (non-invasive test queries).
PROBE_PAYLOADS: dict[str, dict[str, Any]] = {
    "simple": {
        "method_override": "POST",
        "data": {"dc_creator": "Ady", "size": "10"},
    },
    "advanced": {
        "method_override": "POST",
        "submit_url": "https://www.mek.oszk.hu/katalog/kataluj.php3",
        "data": {
            "s1": "dc_creator_o FamilyGivenName",
            "m1": "Ady",
            "muv1": "and",
            "s2": "dc_title main",
            "m2": "",
            "muv2": "and",
            "s3": "dc_subject keyword",
            "m3": "",
            "muv3": "and",
            "s4": "dc_subject keyword",
            "m4": "",
            "muv4": "and",
            "s5": "dc_subject keyword",
            "m5": "",
            "szerint": "szerzosz",
        },
    },
    "fulltext_new": {
        "method_override": "POST",
        "data": {"body": "magyar irodalom", "size": "10"},
    },
    "fulltext_legacy": {
        "method_override": "GET",
        "submit_url": "https://mek.oszk.hu/teljes-eredmeny.mhtml",
        "params": {"body": "magyar", "broadtopic": ""},
    },
}


class FormField(BaseModel):
    name: str
    type: str = "text"
    value: str | None = None
    hidden: bool = False
    options: list[dict[str, str]] = Field(default_factory=list)


class PaginationInfo(BaseModel):
    field: str | None = None
    page_size_field: str | None = None
    detected_in_html: bool = False


class ProbeResult(BaseModel):
    status_code: int | None = None
    content_type: str | None = None
    response_bytes: int | None = None
    result_classes_found: list[str] = Field(default_factory=list)
    sample_urls: list[str] = Field(default_factory=list)
    pagination: PaginationInfo | None = None
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)


class DiscoveredForm(BaseModel):
    id: str
    page_url: str
    form_name: str | None = None
    submit_url: str
    method: str
    enctype: str | None = None
    fields: list[FormField] = Field(default_factory=list)
    probe: ProbeResult | None = None


class FormsReport(BaseModel):
    discovered_at: str
    pages: dict[str, str]
    forms: list[DiscoveredForm] = Field(default_factory=list)


def _resolve_submit_url(page_url: str, action: str | None) -> str:
    if not action or action in ("", "#", "#sealist"):
        return page_url
    return urljoin(page_url, action)


def _parse_form(form: Any, page_url: str, form_id: str) -> DiscoveredForm:
    action = form.get("action")
    method = (form.get("method") or "GET").upper()
    enctype = form.get("enctype")
    fields: list[FormField] = []

    for tag in form.find_all(["input", "select", "textarea"]):
        name = tag.get("name")
        if not name:
            continue
        tag_type = tag.get("type", "text") if tag.name == "input" else tag.name
        hidden = tag_type == "hidden"
        options: list[dict[str, str]] = []
        if tag.name == "select":
            for opt in tag.find_all("option"):
                options.append(
                    {
                        "value": opt.get("value", ""),
                        "label": opt.get_text(strip=True),
                        "selected": str(opt.has_attr("selected")),
                    }
                )
        fields.append(
            FormField(
                name=name,
                type=tag_type,
                value=tag.get("value"),
                hidden=hidden,
                options=options,
            )
        )

    return DiscoveredForm(
        id=form_id,
        page_url=page_url,
        form_name=form.get("name"),
        submit_url=_resolve_submit_url(page_url, action),
        method=method,
        enctype=enctype,
        fields=fields,
    )


def _pick_primary_form(soup: BeautifulSoup, form_id: str) -> Any | None:
    forms = soup.find_all("form")
    if not forms:
        return None
    preferred_names = {
        "simple": "elfullform",
        "advanced": "katal",
        "fulltext_new": "elfulltextf",
        "fulltext_legacy": "teljesszov",
    }
    target = preferred_names.get(form_id)
    if target:
        for form in forms:
            if form.get("name") == target:
                return form
    return forms[0]


def _decode_response(response: httpx.Response) -> str:
    """Best-effort decode for MEK pages (UTF-8 or iso-8859-2)."""
    raw = response.content
    for encoding in ("utf-8", "iso-8859-2", "latin-2", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _analyze_probe_html(html: str, field_names: set[str]) -> ProbeResult:
    result = ProbeResult()
    lower = html.lower()
    result.result_classes_found = sorted(
        {hint for hint in RESULT_CLASS_HINTS if hint in lower}
    )
    urls = MEK_URL_RE.findall(html)
    seen: set[str] = set()
    for folder, doc_id in urls:
        url = f"https://mek.oszk.hu/{folder}/{doc_id}"
        if url not in seen:
            seen.add(url)
            result.sample_urls.append(url)
        if len(result.sample_urls) >= 10:
            break

    pagination = PaginationInfo()
    if "from" in field_names:
        pagination.field = "from"
    if "size" in field_names:
        pagination.page_size_field = "size"
    pagination.detected_in_html = bool(PAGINATION_HINTS.search(html))
    result.pagination = pagination

    if not result.sample_urls and not result.result_classes_found:
        result.warnings.append("No result markers or MEK URLs found in probe response")
    return result


def _probe_form(
    client: httpx.Client,
    form: DiscoveredForm,
    *,
    do_probe: bool,
) -> ProbeResult | None:
    if not do_probe:
        return None
    cfg = PROBE_PAYLOADS.get(form.id)
    if not cfg:
        return ProbeResult(warnings=[f"No probe configuration for form id '{form.id}'"])

    method = cfg.get("method_override", form.method).upper()
    submit_url = cfg.get("submit_url", form.submit_url)
    time.sleep(REQUEST_DELAY_SEC)

    try:
        if method == "GET":
            response = client.get(submit_url, params=cfg.get("params", {}))
        else:
            response = client.post(submit_url, data=cfg.get("data", {}))
        html = _decode_response(response)
        field_names = {f.name for f in form.fields}
        probe = _analyze_probe_html(html, field_names)
        probe.status_code = response.status_code
        probe.content_type = response.headers.get("content-type")
        probe.response_bytes = len(response.content)
        if response.status_code == 404:
            probe.warnings.append(
                "Submit URL returned 404 — endpoint may be deprecated; "
                "see docs/architecture.md"
            )
        return probe
    except httpx.HTTPError as exc:
        return ProbeResult(error=str(exc))


def discover_page(
    client: httpx.Client,
    form_id: str,
    page_url: str,
    *,
    do_probe: bool,
) -> DiscoveredForm | None:
    time.sleep(REQUEST_DELAY_SEC)
    response = client.get(page_url)
    response.raise_for_status()
    html = _decode_response(response)
    soup = BeautifulSoup(html, "lxml")
    form_el = _pick_primary_form(soup, form_id)
    if form_el is None:
        return None
    discovered = _parse_form(form_el, page_url, form_id)
    discovered.probe = _probe_form(client, discovered, do_probe=do_probe)
    return discovered


def run_discovery(*, do_probe: bool = False) -> FormsReport:
    report = FormsReport(
        discovered_at=datetime.now(timezone.utc).isoformat(),
        pages=dict(SEARCH_PAGES),
    )
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client:
        for form_id, page_url in SEARCH_PAGES.items():
            try:
                form = discover_page(client, form_id, page_url, do_probe=do_probe)
                if form:
                    report.forms.append(form)
            except httpx.HTTPError as exc:
                report.forms.append(
                    DiscoveredForm(
                        id=form_id,
                        page_url=page_url,
                        submit_url=page_url,
                        method="GET",
                        probe=ProbeResult(error=f"Failed to fetch page: {exc}"),
                    )
                )
    return report


def _print_summary(report: FormsReport, console: Console) -> None:
    table = Table(title="MEK form discovery summary")
    table.add_column("ID")
    table.add_column("Method")
    table.add_column("Submit URL")
    table.add_column("Fields")
    table.add_column("Probe")
    for form in report.forms:
        probe_status = "-"
        if form.probe:
            if form.probe.error:
                probe_status = f"ERR: {form.probe.error[:40]}"
            elif form.probe.status_code:
                hits = len(form.probe.sample_urls)
                probe_status = f"{form.probe.status_code} / {hits} URLs"
        table.add_row(
            form.id,
            form.method,
            form.submit_url[:60] + ("..." if len(form.submit_url) > 60 else ""),
            str(len(form.fields)),
            probe_status,
        )
    console.print(table)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Discover MEK search form parameters")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Submit minimal test queries to each search endpoint",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("discovery/output/forms_report.json"),
        help="Output JSON report path",
    )
    args = parser.parse_args(argv)
    console = Console()

    console.print("[bold]MEK form discovery[/bold]")
    report = run_discovery(do_probe=args.probe)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    console.print(f"Report written to [green]{args.output}[/green]")
    _print_summary(report, console)
    return 0


if __name__ == "__main__":
    sys.exit(main())
