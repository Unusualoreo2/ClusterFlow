"""Acceptance tests for backend/main.py (written by the architect; implementation must pass them unchanged)."""
import os
import sys

from fastapi.testclient import TestClient

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import main  # noqa: E402

client = TestClient(main.app)
EXAMPLE = open(os.path.join(ROOT, "data", "example_sacct.txt"), "rb").read()


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_index_serves_frontend():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "HPCFlow" in r.text


def test_fastapi_docs_still_work():
    assert client.get("/docs").status_code == 200


def test_analyze_upload():
    r = client.post("/api/analyze", files={"file": ("jobs.txt", EXAMPLE, "text/plain")})
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["job_count"] == 5 and body["skipped"] == 1
    assert body["jobs"][0]["job_id"] == "4471201"


def test_analyze_accepts_csv_name_and_comma_delimiter():
    data = EXAMPLE.decode().replace("|", ",").encode()
    r = client.post("/api/analyze", files={"file": ("jobs.csv", data, "text/csv")})
    assert r.status_code == 200 and r.json()["summary"]["job_count"] == 5


def test_analyze_pasted_text():
    r = client.post("/api/analyze-text", json={"text": EXAMPLE.decode()})
    assert r.status_code == 200 and r.json()["summary"]["job_count"] == 5


def test_bad_columns_give_400_with_message():
    r = client.post("/api/analyze", files={"file": ("x.csv", b"JobID|Elapsed\n1|00:10:00\n", "text/csv")})
    assert r.status_code == 400
    assert "missing" in r.json()["detail"].lower()


def test_empty_and_binary_files_give_400():
    assert client.post("/api/analyze", files={"file": ("e.csv", b"", "text/csv")}).status_code == 400
    assert client.post("/api/analyze", files={"file": ("b.bin", b"\xff\xfe\x00\x01\x02", "application/octet-stream")}).status_code == 400


def test_too_large_file_gives_413():
    big = b"JobID|State|Elapsed|AllocCPUS|TotalCPU\n" + b"1|COMPLETED|00:10:00|1|00:10:00\n" * 400000  # > 10 MB
    assert client.post("/api/analyze", files={"file": ("big.txt", big, "text/plain")}).status_code == 413
