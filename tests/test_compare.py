"""Before/after comparison (v0.18): show a centre what improved. Written by the architect; implementation must pass
it unchanged.

`--compare BEFORE` analyses BEFORE (a sacct export) as well and adds result["comparison"] =
{"before": metrics, "after": metrics}, metrics = clusterflow_cli.comparison_metrics(result):
  job_count, avg_cpu_efficiency, avg_memory_efficiency, wasted_core_hours_per_job (None if unknown or no jobs),
  oom_jobs (state starts OUT_OF_MEMORY), timeout_jobs (state starts TIMEOUT).
comparison_lines(comparison) returns the section lines; the text report ends with a blank line + that section (so it also appears in --html and --split-by-user is
unaffected):
  Change since before (3 jobs -> 2 jobs)
    Avg CPU efficiency:        50% -> 100% (+50 points)
    Avg memory efficiency:     50% -> 75% (+25 points)
    Wasted core-hours per job: 2.0 -> 0.0 (-100%)
    Out-of-memory jobs:        1 -> 0
    Timed-out jobs:            0 -> 0
Percent rows: "(no change)" when the rounded points are equal; just "- -> 75%" (no bracket) if either side is
unknown. Waste row: bracket only when both are known and before > 0."""
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

HDR = "JobID|JobName|User|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"


def job(jid, state, cpus, tot, req, rss):
    return ("%s|sim|ann|%s|01:00:00|04:00:00|%d|%s|%s|\n" % (jid, state, cpus, tot, req)
            + "%s.batch|batch||%s|01:00:00||%d|%s||%s\n" % (jid, state, cpus, tot, rss))


# before: two 4-core jobs at 25% CPU / 25% memory (3 wasted core-h each) + one OOM job at 100% / 100%
BEFORE = HDR + job(1, "COMPLETED", 4, "01:00:00", "4G", "1G") + job(2, "COMPLETED", 4, "01:00:00", "4G", "1G") \
    + job(3, "OUT_OF_MEMORY", 1, "01:00:00", "1G", "1G")
# after: two 1-core jobs at 100% CPU / 75% memory, nothing wasted
AFTER = HDR + job(11, "COMPLETED", 1, "01:00:00", "2G", "1536M") + job(12, "COMPLETED", 1, "01:00:00", "2G", "1536M")

EXPECTED = [
    "Change since before (3 jobs -> 2 jobs)",
    "Avg CPU efficiency: 50% -> 100% (+50 points)",
    "Avg memory efficiency: 50% -> 75% (+25 points)",
    "Wasted core-hours per job: 2.0 -> 0.0 (-100%)",
    "Out-of-memory jobs: 1 -> 0",
    "Timed-out jobs: 0 -> 0",
]


def norm(text):
    return [" ".join(line.split()) for line in text.splitlines()]


def files(tmp_path):
    b, a = tmp_path / "before.txt", tmp_path / "after.txt"
    b.write_text(BEFORE, encoding="utf-8")
    a.write_text(AFTER, encoding="utf-8")
    return str(b), str(a)


def run(*args, script=CLI):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, script, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env, timeout=60)


def test_metrics():
    m = clusterflow_cli.comparison_metrics(analysis.analyze(BEFORE))
    assert m == {"job_count": 3, "avg_cpu_efficiency": pytest.approx(50.0), "avg_memory_efficiency": pytest.approx(50.0),
                 "wasted_core_hours_per_job": pytest.approx(2.0), "oom_jobs": 1, "timeout_jobs": 0}


def test_metrics_with_no_jobs():
    running_only = HDR + "9|sim|ann|RUNNING|01:00:00|04:00:00|1|01:00:00|1G|\n"     # a header alone counts as missing columns
    m = clusterflow_cli.comparison_metrics(analysis.analyze(running_only))
    assert m["job_count"] == 0 and m["wasted_core_hours_per_job"] is None


def test_text_section_at_the_end(tmp_path):
    b, a = files(tmp_path)
    p = run(a, "--compare", b)
    assert p.returncode == 0, p.stderr
    lines = [l for l in norm(p.stdout)]
    assert lines[-6:] == EXPECTED
    assert lines[-7] == ""                          # blank line before the section


def test_no_section_without_compare(tmp_path):
    b, a = files(tmp_path)
    assert "Change since before" not in run(a).stdout


def test_json_has_comparison(tmp_path):
    b, a = files(tmp_path)
    data = json.loads(run(a, "--compare", b, "--json").stdout)
    assert data["comparison"]["before"]["job_count"] == 3
    assert data["comparison"]["after"]["oom_jobs"] == 0


def test_no_change_and_unknown_values():
    def section(before, after):
        return norm("\n".join(clusterflow_cli.comparison_lines({"before": before, "after": after})))
    m = {"job_count": 5, "avg_cpu_efficiency": 60.2, "avg_memory_efficiency": None,
         "wasted_core_hours_per_job": 0.0, "oom_jobs": 0, "timeout_jobs": 2}
    m2 = dict(m, avg_cpu_efficiency=59.9, avg_memory_efficiency=75.0, wasted_core_hours_per_job=1.5)
    out = section(m, m2)
    assert "Avg CPU efficiency: 60% -> 60% (no change)" in out
    assert "Avg memory efficiency: - -> 75%" in out
    assert "Wasted core-hours per job: 0.0 -> 1.5" in out          # before is 0: no percentage
    assert "Timed-out jobs: 2 -> 2" in out


def test_html_includes_comparison(tmp_path):
    b, a = files(tmp_path)
    out = tmp_path / "r.html"
    assert run(a, "--compare", b, "--html", str(out)).returncode == 0
    assert "Change since before (3 jobs -&gt; 2 jobs)" in out.read_text(encoding="utf-8")


def test_missing_before_file(tmp_path):
    b, a = files(tmp_path)
    p = run(a, "--compare", str(tmp_path / "nope.txt"))
    assert p.returncode == 2 and "nope.txt" in p.stderr and "Traceback" not in p.stderr


def test_bad_before_file(tmp_path):
    b, a = files(tmp_path)
    bad = tmp_path / "bad.txt"
    bad.write_text("Hello|World\n1|2\n", encoding="utf-8")
    p = run(a, "--compare", str(bad))
    assert p.returncode == 2 and "Traceback" not in p.stderr


def test_bundle(tmp_path):
    b, a = files(tmp_path)
    p = run(a, "--compare", b, script=BUNDLE)
    assert p.returncode == 0, p.stderr
    assert norm(p.stdout)[-6:] == EXPECTED


def test_documented():
    for doc in ("README.md", os.path.join("docs", "user-guide.md")):
        with open(os.path.join(ROOT, doc), encoding="utf-8") as f:
            assert "--compare" in f.read()
