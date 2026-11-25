"""Web app: download the HTML report (v0.19). Written by the architect; implementation must pass it unchanged.
POST /api/report-html {"text": ...} runs the same checks as /api/analyze-text and returns
clusterflow_cli.html_report(result, 10) as text/html. The page has a "Download report (HTML)" button (id htmlBtn)
next to the CSV one that posts the last analysed text and saves clusterflow_report.html."""
import os
import re
import sys

from fastapi.testclient import TestClient

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import clusterflow_cli  # noqa: E402
import main  # noqa: E402

client = TestClient(main.app)


def test_returns_html_report():
    r = client.post("/api/report-html", json={"text": clusterflow_cli.DEMO_SACCT})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert r.text.lstrip().lower().startswith("<!doctype html>")
    assert "32 jobs analysed" in r.text and "What to fix first" in r.text


def test_same_checks_as_analyse():
    assert client.post("/api/report-html", json={"text": ""}).status_code == 400
    assert client.post("/api/report-html", json={"text": "Hello|World\n1|2\n"}).status_code == 400
    big = "x" * (main.MAX_BYTES + 1)
    assert client.post("/api/report-html", json={"text": big}).status_code == 413


def page():
    with open(os.path.join(ROOT, "frontend", "index.html"), encoding="utf-8") as f:
        return f.read()


def test_button_next_to_csv():
    html = page()
    assert re.search(r'<button[^>]*id="htmlBtn"[^>]*>Download report \(HTML\)</button>', html)
    assert html.index('id="downloadBtn"') < html.index('id="htmlBtn"')


def test_button_posts_last_text_and_saves_file():
    html = page()
    assert "'/api/report-html'" in html
    assert "clusterflow_report.html" in html
    assert "text/html" in html
