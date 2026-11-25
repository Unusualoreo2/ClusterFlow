"""Per-user reports show the cluster average (v0.21). Written by the architect; implementation must pass it unchanged.
- In --split-by-user reports, each user's result gets result["cluster"] = {"avg_cpu_efficiency",
  "avg_memory_efficiency", "users"} from the whole file, and the text report shows, right after the memory line:
  "Cluster average:       CPU 53%, memory 42% (5 users)". Normal reports have no such line.
- Wording fix: per-job CPU advice reads "request --cpus-per-task=12 instead of 32" (no stray "CPUs")."""
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
CLI = os.path.join(ROOT, "backend", "clusterflow_cli.py")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402


def run(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, CLI, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env, timeout=60)


def test_report_line_after_memory():
    r = analysis.analyze(clusterflow_cli.DEMO_SACCT, user="amurphy")
    r["cluster"] = {"avg_cpu_efficiency": 53.2, "avg_memory_efficiency": 41.6, "users": 5}
    lines = clusterflow_cli.report(r, 5).splitlines()
    i = [n for n, l in enumerate(lines) if l.startswith("Avg memory efficiency:")][0]
    assert lines[i + 1] == "Cluster average:       CPU 53%, memory 42% (5 users)"


def test_no_line_in_normal_report():
    assert "Cluster average" not in run("--demo").stdout


def test_split_reports_show_cluster_average(tmp_path):
    out = tmp_path / "r"
    assert run("--demo", "--split-by-user", str(out)).returncode == 0
    page = (out / "amurphy.html").read_text(encoding="utf-8")
    assert "<th>Cluster average</th><td>CPU 53%, memory 42% (5 users)</td>" in page


def test_cpu_advice_wording():
    recs = [r for j in analysis.analyze(clusterflow_cli.DEMO_SACCT)["jobs"] for r in j["recommendations"]
            if "--cpus-per-task=" in r]
    assert recs
    for r in recs:
        assert " CPUs instead of" not in r
    assert any("request --cpus-per-task=12 instead of 32" in r for r in recs)
