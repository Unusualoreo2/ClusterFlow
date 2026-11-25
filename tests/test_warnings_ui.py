"""Column warnings shown to the user (v0.8). Written by the architect."""
import json
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
CLI = os.path.join(ROOT, "backend", "clusterflow_cli.py")
EXAMPLE = os.path.join(ROOT, "data", "example_sacct.txt")
PARTIAL = "JobID|ExitCode|State|MaxRSS|Elapsed\n1|0:0|COMPLETED|500M|00:10:00\n"


def run(path, *args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, CLI, str(path), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env, timeout=60)


def test_cli_lists_warnings_after_the_summary(tmp_path):
    f = tmp_path / "p.txt"
    f.write_text(PARTIAL, encoding="utf-8")
    out = run(f).stdout
    notes = [l for l in out.splitlines() if l.startswith("Note: ")]
    assert any("TotalCPU column missing" in l for l in notes)
    assert any("ReqMem column missing" in l for l in notes)
    assert out.index("Note: ") > out.index("Wasted core-hours")
    assert out.index("Note: ") < out.index("Top ")


def test_cli_no_notes_for_complete_export():
    assert "Note: " not in run(EXAMPLE).stdout


def test_json_includes_warnings(tmp_path):
    f = tmp_path / "p.txt"
    f.write_text(PARTIAL, encoding="utf-8")
    data = json.loads(run(f, "--json").stdout)
    assert data["warnings"] and all(isinstance(w, str) for w in data["warnings"])


def test_api_returns_warnings():
    sys.path.insert(0, os.path.join(ROOT, "backend"))
    from fastapi.testclient import TestClient
    import main
    r = TestClient(main.app).post("/api/analyze-text", json={"text": PARTIAL})
    assert r.status_code == 200 and any("TotalCPU" in w for w in r.json()["warnings"])
