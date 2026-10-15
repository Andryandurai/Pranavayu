from apps.rag.templatetags.rag_render import evidence_markdown


def test_evidence_renderer_escapes_html_and_rejects_script_urls():
    html = evidence_markdown("<img src=x onerror=alert(1)>\n\n[unsafe](javascript:alert(1))")
    assert "<img" not in html and "&lt;img" in html
    assert 'href="javascript:' not in html


def test_evidence_renderer_preserves_numeric_table_cells():
    html = evidence_markdown("| Field | Value |\n| --- | --- |\n| peak | 15.641839027404785 |")
    assert "<table>" in html and "<td>15.641839027404785</td>" in html
