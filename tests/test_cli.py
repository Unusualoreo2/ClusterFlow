"""Acceptance tests for backend/clusterflow_cli.py (v0.4). Written by the architect; implementation must pass them unchanged."""
import ast
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
BACKEND = os.path.join(ROOT, "backend")
CLI = os.path.join(BACKEND, "clusterflow_cli.py")
EXAMPLE = os.path.join(ROOT, "data", "example_sacct.txt")
sys.path.insert(0, BACKEND)


def run(*args, stdin=None, env=None):
    e = dict(os.environ, **(env or {}))
    e["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, CLI, *args], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", env=e, timeout=60)


# ---- compatibility: clusters often run old Python -------------------------
@pytest.mark.parametrize("name", ["analysis.py", "clusterflow_cli.py"])
def test_syntax_works_on_python_37(name):
    src = open(os.path.join(BACKEND, name), encoding="utf-8").read()
    ast.parse(src, feature_version=(3, 7))


def test_cli_uses_only_stdlib():
    src = open(CLI, encoding="utf-8").read()
    for mod in ("fastapi", "pandas", "numpy", "requests", "pydantic"):
        assert "import " + mod not in src and "from " + mod not in src


# ---- reading input ----------------------------------------------------------
def test_report_from_file():
    r = run(EXAMPLE)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "5 jobs analysed (1 running/pending skipped)" in out
    assert "Avg CPU efficiency" in out and "67%" in out
    assert "Avg memory efficiency" in out and "51%" in out
    assert "Wasted core-hours" in out and "83.8" in out


def test_report_from_stdin():
    data = open(EXAMPLE, encoding="utf-8").read()
    r = run("-", stdin=data)
    assert r.returncode == 0, r.stderr
    assert "5 jobs analysed" in r.stdout


def test_group_tables_and_top_jobs():
    out = run(EXAMPLE).stdout
    assert "By user" in out and "By partition" in out
    lines = out.splitlines()
    user_rows = [l for l in lines if l.strip().startswith(("amurphy", "jkelly", "sobrien"))]
    assert user_rows[0].strip().startswith("amurphy")  # most waste first
    assert "Top 5 jobs by wasted core-hours" in out
    assert "--cpus-per-task=14" in out and "--mem=14050M" in out


def test_top_option_limits_jobs():
    out = run(EXAMPLE, "--top", "2").stdout
    assert "Top 2 jobs by wasted core-hours" in out
    assert "4471201" in out and "4471388" in out
    assert "4471502" not in out


def test_no_group_tables_without_columns(tmp_path):
    f = tmp_path / "plain.txt"
    f.write_text("JobID|State|Elapsed|AllocCPUS|TotalCPU\n1|COMPLETED|01:00:00|2|01:00:00\n", encoding="utf-8")
    out = run(str(f)).stdout
    assert "1 job analysed" in out
    assert "By user" not in out and "By partition" not in out


def test_json_output():
    r = run(EXAMPLE, "--json")
    data = json.loads(r.stdout)
    assert data["summary"]["job_count"] == 5 and len(data["jobs"]) == 5


def test_csv_output(tmp_path):
    out = tmp_path / "report.csv"
    r = run(EXAMPLE, "--csv", str(out))
    assert r.returncode == 0, r.stderr
    import csv
    rows = list(csv.reader(open(out, encoding="utf-8", newline="")))
    assert rows[0][:3] == ["job_id", "name", "state"] and len(rows) == 6
    assert any("--cpus-per-task=14" in c for c in rows[1])


# ---- errors -----------------------------------------------------------------
def test_missing_file_exit_2():
    r = run("does_not_exist.txt")
    assert r.returncode == 2 and "not found" in r.stderr.lower()


def test_bad_columns_exit_2(tmp_path):
    f = tmp_path / "bad.txt"
    f.write_text("JobID|Elapsed\n1|00:10:00\n", encoding="utf-8")
    r = run(str(f))
    assert r.returncode == 2 and "missing" in r.stderr.lower()


# ---- running sacct directly -------------------------------------------------
def test_sacct_command_is_built_correctly():
    import clusterflow_cli
    cmd = clusterflow_cli.sacct_command(days=3)
    assert cmd[0] == "sacct" and "-P" in cmd and "--units=M" in cmd and "-X" not in cmd
    assert "-S" in cmd and cmd[cmd.index("-S") + 1] == "now-3days"
    fmt = [c for c in cmd if c.startswith("--format=")][0]
    for col in ("JobID", "User", "Partition", "State", "Elapsed", "Timelimit", "AllocCPUS", "TotalCPU", "ReqMem", "MaxRSS"):
        assert col in fmt
    assert "-a" not in clusterflow_cli.sacct_command(days=1)
    assert "-a" in clusterflow_cli.sacct_command(days=1, all_users=True)


def test_days_without_sacct_gives_clear_error():
    r = run("--days", "7", env={"PATH": ""})
    assert r.returncode == 2 and "sacct" in r.stderr.lower()
