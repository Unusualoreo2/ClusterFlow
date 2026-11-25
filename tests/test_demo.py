"""One-command demo (v0.14, for CIUK). Written by the architect; implementation must pass it unchanged.

`clusterflow --demo` analyses a built-in sample (the DEMO_SACCT constant in clusterflow_cli.py, so the
single-file bundle carries it too) and prints the normal report, headed by a line saying the data is made up.
The sample is small but shows every kind of finding the report can make."""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
CLI = os.path.join(ROOT, "backend", "clusterflow_cli.py")
BUNDLE = os.path.join(ROOT, "dist", "clusterflow.py")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402

BANNER = "Demo: built-in sample data (made up for illustration, not from a real cluster)"


def run(*args, script=CLI):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, script, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env, timeout=60)


@pytest.fixture(scope="module")
def demo_out():
    p = run("--demo")
    assert p.returncode == 0, p.stderr
    return p.stdout


def test_demo_data_is_a_constant_that_analyses_cleanly():
    result = analysis.analyze(clusterflow_cli.DEMO_SACCT)
    assert 20 <= result["summary"]["job_count"] <= 200
    assert result.get("warnings", []) == []            # complete columns: no "missing column" notes


def test_banner_is_first_line(demo_out):
    assert demo_out.splitlines()[0] == BANNER
    assert demo_out.splitlines()[1].startswith("ClusterFlow report: ")


@pytest.mark.parametrize("label", [
    "request fewer CPUs",
    "request less memory",
    "request a shorter time limit",
    "request fewer GPUs or check GPU use",
    "ran out of memory",
    "hit the time limit",
])
def test_every_main_finding_appears(demo_out, label):
    fix = demo_out.split("What to fix first", 1)[1].split("\n\n", 1)[0]
    assert label in fix


@pytest.mark.parametrize("section", [
    "Avg queue wait:",
    "GPU jobs:",
    "By user",
    "By partition",
    "Trend by ",
    "Typical jobs (sized from repeated runs)",
    "Job arrays (",
    "Top 5 jobs by wasted core-hours",
])
def test_every_section_appears(demo_out, section):
    assert section in demo_out


def test_no_notes_in_demo(demo_out):
    assert "Note: " not in demo_out


def test_several_users_and_partitions():
    s = analysis.analyze(clusterflow_cli.DEMO_SACCT)["summary"]
    assert len(s["by_user"]) >= 3
    assert len(s["by_partition"]) >= 2


def test_demo_with_cost():
    p = run("--demo", "--cpu-hour-cost", "0.02", "--gpu-hour-cost", "0.5")
    assert p.returncode == 0, p.stderr
    assert "Cost of wasted CPU time:" in p.stdout
    assert "Cost of idle GPU time:" in p.stdout


def test_demo_json_has_no_banner():
    p = run("--demo", "--json")
    assert p.returncode == 0, p.stderr
    data = json.loads(p.stdout)                          # banner must not break JSON output
    assert data["summary"]["job_count"] >= 20


def test_demo_anonymise_hides_names():
    users = {j["user"] for j in analysis.analyze(clusterflow_cli.DEMO_SACCT)["jobs"] if j.get("user")}
    assert users
    p = run("--demo", "--anonymise")
    assert p.returncode == 0, p.stderr
    for u in users:
        assert u not in p.stdout


def test_demo_csv(tmp_path):
    out = tmp_path / "demo.csv"
    p = run("--demo", "--csv", str(out))
    assert p.returncode == 0, p.stderr
    assert out.read_text(encoding="utf-8").count("\n") >= 21


@pytest.mark.parametrize("extra", [["some_file.txt"], ["--days", "3"]])
def test_demo_refuses_other_input(extra):
    p = run("--demo", *extra)
    assert p.returncode == 2
    assert "--demo" in p.stderr


def test_bundle_runs_demo():
    p = run("--demo", script=BUNDLE)
    assert p.returncode == 0, p.stderr
    assert p.stdout.splitlines()[0] == BANNER


@pytest.mark.parametrize("doc", ["README.md", os.path.join("docs", "user-guide.md")])
def test_documented(doc):
    with open(os.path.join(ROOT, doc), encoding="utf-8") as f:
        assert "--demo" in f.read()


def test_anonymise_covers_typical_job_profiles():
    """Bug found by the demo: summary["profiles"] kept real user and job names under --anonymise."""
    real = analysis.analyze(clusterflow_cli.DEMO_SACCT)
    names = {j["name"] for j in real["jobs"]} | {j["user"] for j in real["jobs"]}
    out = clusterflow_cli.anonymise(real)
    assert out["summary"]["profiles"]
    for p in out["summary"]["profiles"]:
        assert p["user"] not in names and p["name"] not in names
        assert p["user"].startswith("user") and p["name"].startswith("job")
    # same labels as the jobs table
    jobs_users = {j["user"] for j in out["jobs"]}
    assert {p["user"] for p in out["summary"]["profiles"]} <= jobs_users
