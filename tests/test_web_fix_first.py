"""Web page shows 'What to fix first' (v0.27). Written by the architect; implementation must pass it unchanged.
The API adds result["fix_first"] = the CLI's fix_first lines, stripped; the page lists them first (textContent)."""
import os
import re
import sys

from fastapi.testclient import TestClient

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402
import main  # noqa: E402

client = TestClient(main.app)


def test_api_includes_fix_first():
    data = client.post("/api/analyze-text", json={"text": clusterflow_cli.DEMO_SACCT}).json()
    expected = [l.strip() for l in clusterflow_cli.fix_first(analysis.analyze(clusterflow_cli.DEMO_SACCT)["jobs"])]
    assert data["fix_first"] == expected and expected


def test_page_lists_fix_first_before_tables():
    with open(os.path.join(ROOT, "frontend", "index.html"), encoding="utf-8") as f:
        page = f.read()
    body = re.search(r"function renderFixFirst\(items\) \{(.*?)\n        \}", page, re.S).group(1)
    assert "'What to fix first'" in body and "textContent" in body and "innerHTML" not in body
    assert "items.length" in body
    call = page.index("renderFixFirst(data.fix_first || [])")
    assert call < page.index("renderGroups('By user'")
