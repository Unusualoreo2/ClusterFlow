"""Overview page for per-user reports (v0.28). Written by the architect; implementation must pass it unchanged.
--split-by-user also writes DIR/index.html (clusterflow_cli.users_index_html(per_user, cluster)): a self-contained,
escaped page titled "ClusterFlow per-user reports" with the cluster average and one row per user, sorted by wasted
core-hours (most first): <a href="FILE">user</a>, jobs, CPU, memory, wasted core-hours. A user whose safe file name
would be "index" gets "index_user.html" so the overview is never overwritten."""
import os
import re
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
CLI = os.path.join(ROOT, "backend", "clusterflow_cli.py")
sys.path.insert(0, os.path.join(ROOT, "backend"))

HDR = "JobID|JobName|User|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"


def run(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, CLI, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env, timeout=60)


def test_index_lists_users_by_waste(tmp_path):
    out = tmp_path / "r"
    assert run("--demo", "--split-by-user", str(out)).returncode == 0
    page = (out / "index.html").read_text(encoding="utf-8")
    assert page.lstrip().lower().startswith("<!doctype html>")
    assert "<title>ClusterFlow per-user reports</title>" in page
    assert "<script" not in page.lower() and "background: #fff" in page
    users = re.findall(r'<a href="([^"]+)\.html">([^<]+)</a>', page)
    assert [u for _, u in users] == ["amurphy", "jkelly", "ocallaghan", "rbrennan", "sdoyle"]   # 531, 96, 24, 11, 1
    for f, u in users:
        assert (out / (f + ".html")).exists()
    assert "CPU 53%, memory 42% (5 users)" in page


def test_index_escapes_names(tmp_path):
    data = HDR + ("1|a|<b>x|COMPLETED|01:00:00|02:00:00|2|01:00:00|2G|\n"
                  "1.batch|batch||COMPLETED|01:00:00||2|01:00:00||1G\n")
    f = tmp_path / "x.txt"
    f.write_text(data, encoding="utf-8")
    out = tmp_path / "r"
    assert run(str(f), "--split-by-user", str(out)).returncode == 0
    page = (out / "index.html").read_text(encoding="utf-8")
    assert "<b>x" not in page and "&lt;b&gt;x" in page
    assert 'href="_b_x.html"' in page


def test_user_named_index_does_not_overwrite(tmp_path):
    data = HDR + ("1|a|index|COMPLETED|01:00:00|02:00:00|2|01:00:00|2G|\n"
                  "1.batch|batch||COMPLETED|01:00:00||2|01:00:00||1G\n")
    f = tmp_path / "x.txt"
    f.write_text(data, encoding="utf-8")
    out = tmp_path / "r"
    assert run(str(f), "--split-by-user", str(out)).returncode == 0
    assert sorted(os.listdir(str(out))) == ["index.html", "index_user.html"]
    assert "Report for index" in (out / "index_user.html").read_text(encoding="utf-8")
    assert 'href="index_user.html"' in (out / "index.html").read_text(encoding="utf-8")
