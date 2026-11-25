"""Self-contained HTML report (v0.15). Written by the architect; implementation must pass it unchanged.

`--html PATH` also writes a single HTML file (no external resources, prints cleanly) that a researcher can open,
print or email. Every value from the data is HTML-escaped. Standard library only (html module)."""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
CLI = os.path.join(ROOT, "backend", "clusterflow_cli.py")
BUNDLE = os.path.join(ROOT, "dist", "clusterflow.py")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402

HDR = "JobID|JobName|User|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"


def run(*args, script=CLI):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, script, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env, timeout=60)


@pytest.fixture(scope="module")
def demo_html(tmp_path_factory):
    path = tmp_path_factory.mktemp("h") / "report.html"
    p = run("--demo", "--html", str(path), "--cpu-hour-cost", "0.02")
    assert p.returncode == 0, p.stderr
    return path.read_text(encoding="utf-8")


def test_stdout_report_unchanged(tmp_path):
    plain = run("--demo").stdout
    with_html = run("--demo", "--html", str(tmp_path / "r.html")).stdout
    assert with_html == plain


def test_is_a_complete_document(demo_html):
    assert demo_html.lstrip().lower().startswith("<!doctype html>")
    assert "<meta charset=\"utf-8\">" in demo_html
    assert "<title>ClusterFlow report</title>" in demo_html
    assert demo_html.rstrip().endswith("</html>")


def test_self_contained(demo_html):
    assert not re.search(r"""(src|href)\s*=\s*["']?(https?:)?//""", demo_html)
    assert "<script" not in demo_html.lower()
    assert "@import" not in demo_html
    assert "@media print" in demo_html                    # prints cleanly


def test_contains_the_findings(demo_html):
    assert "32 jobs analysed" in demo_html
    assert "What to fix first" in demo_html
    assert "request fewer CPUs" in demo_html
    assert "Cost of wasted CPU time" in demo_html
    assert "Demo: built-in sample data (made up for illustration, not from a real cluster)" in demo_html
    for section in ("By user", "Typical jobs (sized from repeated runs)", "Top 5 jobs by wasted core-hours"):
        assert section in demo_html


def test_summary_is_a_table(demo_html):
    m = re.search(r"<table[^>]*class=\"summary\"[^>]*>(.*?)</table>", demo_html, re.S)
    assert m, "summary must be <table class=\"summary\">"
    assert "Avg CPU efficiency" in m.group(1) and "53%" in m.group(1)


def test_fix_first_is_a_list(demo_html):
    m = re.search(r"<ul[^>]*class=\"fix-first\"[^>]*>(.*?)</ul>", demo_html, re.S)
    assert m, "what-to-fix-first must be <ul class=\"fix-first\">"
    assert m.group(1).count("<li>") == 7


def test_values_are_escaped(tmp_path):
    rows = ("1|<script>alert(1)</script>|bob&co|COMPLETED|01:00:00|20:00:00|16|01:00:00|32G|\n"
            "1.batch|batch||COMPLETED|01:00:00||16|01:00:00||1G\n")
    f = tmp_path / "x.txt"
    f.write_text(HDR + rows, encoding="utf-8")
    out = tmp_path / "x.html"
    p = run(str(f), "--html", str(out))
    assert p.returncode == 0, p.stderr
    page = out.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "bob&amp;co" in page


def test_anonymise_applies(tmp_path):
    users = {j["user"] for j in analysis.analyze(clusterflow_cli.DEMO_SACCT)["jobs"]}
    out = tmp_path / "a.html"
    assert run("--demo", "--anonymise", "--html", str(out)).returncode == 0
    page = out.read_text(encoding="utf-8")
    for u in users:
        assert u not in page


def test_function_api():
    result = analysis.analyze(clusterflow_cli.DEMO_SACCT)
    page = clusterflow_cli.html_report(result, 5)
    assert page.lstrip().lower().startswith("<!doctype html>")
    assert "Demo:" not in page                          # banner only when a banner is passed
    assert "Note for you" in clusterflow_cli.html_report(result, 5, banner="Note for you")


def test_unwritable_path_fails_cleanly(tmp_path):
    p = run("--demo", "--html", str(tmp_path / "no_such_dir" / "r.html"))
    assert p.returncode == 2
    assert "clusterflow:" in p.stderr and "Traceback" not in p.stderr


def test_bundle_supports_html(tmp_path):
    out = tmp_path / "b.html"
    p = run("--demo", "--html", str(out), script=BUNDLE)
    assert p.returncode == 0, p.stderr
    assert "What to fix first" in out.read_text(encoding="utf-8")


@pytest.mark.parametrize("doc", ["README.md", os.path.join("docs", "user-guide.md")])
def test_documented(doc):
    with open(os.path.join(ROOT, doc), encoding="utf-8") as f:
        assert "--html" in f.read()


def test_fix_list_not_repeated_in_details(demo_html):
    """Review finding: the fix-first lines must appear only in the list, not again inside <pre>."""
    assert demo_html.count("request fewer CPUs") == 1
    pre = re.search(r"<pre>(.*?)</pre>", demo_html, re.S).group(1)
    assert "What to fix first" not in pre
    assert pre.lstrip().startswith("By user")


def test_user_guide_html_section_is_a_sentence():
    with open(os.path.join(ROOT, "docs", "user-guide.md"), encoding="utf-8") as f:
        guide = f.read()
    assert "python3 dist/clusterflow.py jobs.txt --html report.html" in guide
