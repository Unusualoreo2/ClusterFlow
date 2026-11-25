"""Web demo (v0.14). Written by the architect; implementation must pass it unchanged.
The web page's example button loads the same built-in sample as `clusterflow --demo`."""
import os
import sys

from fastapi.testclient import TestClient

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import clusterflow_cli  # noqa: E402
import main  # noqa: E402

client = TestClient(main.app)


def test_example_endpoint_serves_demo_sample():
    r = client.get("/api/example")
    assert r.status_code == 200
    assert r.text == clusterflow_cli.DEMO_SACCT


def test_demo_sample_analyses_through_the_api():
    r = client.post("/api/analyze-text", json={"text": client.get("/api/example").text})
    assert r.status_code == 200
    assert r.json()["summary"]["job_count"] == 32


def test_button_says_data_is_made_up():
    with open(os.path.join(ROOT, "frontend", "index.html"), encoding="utf-8") as f:
        page = f.read()
    assert "Try the demo (made-up data)" in page
    assert "Try example data" not in page


def test_readme_describes_endpoint():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        readme = f.read()
    assert "`GET /api/example` returns the built-in demo sample (the same data as `--demo`)" in readme
