"""Tests for MEK form discovery helpers."""

from scripts.discover_forms import (
    DiscoveredForm,
    FormField,
    _analyze_probe_html,
    _parse_form,
    _resolve_submit_url,
)
from bs4 import BeautifulSoup


def test_resolve_submit_url_same_page_for_hash():
    assert (
        _resolve_submit_url("https://www.mek.oszk.hu/hu/search/elfull/", "#sealist")
        == "https://www.mek.oszk.hu/hu/search/elfull/"
    )


def test_resolve_submit_url_relative():
    assert (
        _resolve_submit_url("https://www.mek.oszk.hu/hu/search/detailed/", "/katalog/kataluj.php3")
        == "https://www.mek.oszk.hu/katalog/kataluj.php3"
    )


def test_parse_simple_form_fields():
    html = """
    <form name="elfullform" action="#sealist" method="post">
      <input type="text" name="dc_creator" value="">
      <input type="hidden" name="from" value="">
      <select name="size"><option value="10">10</option></select>
    </form>
    """
    soup = BeautifulSoup(html, "lxml")
    form = _parse_form(soup.find("form"), "https://example/elfull/", "simple")
    names = {f.name for f in form.fields}
    assert names == {"dc_creator", "from", "size"}
    assert form.method == "POST"


def test_analyze_probe_html_finds_urls_and_classes():
    html = """
    <div class="rlistb numberofhits">
      <a href="https://mek.oszk.hu/07100/07128">Ady</a>
    </div>
    <script>pageNextPrev('10')</script>
    """
    probe = _analyze_probe_html(html, {"from", "size"})
    assert "rlistb" in probe.result_classes_found
    assert probe.sample_urls == ["https://mek.oszk.hu/07100/07128"]
    assert probe.pagination is not None
    assert probe.pagination.field == "from"
