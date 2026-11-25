"""pilot/check_pilot.py (v0.6): checks HPCFlow's verdicts on the six pilot test jobs. Written by the architect."""
import json
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
CHECK = os.path.join(ROOT, "pilot", "check_pilot.py")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402

HDR = "JobID|JobName|User|Partition|State|Submit|Start|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"
T = "2026-12-01T10:00:00"
# What a cluster would plausibly record for the six pilot jobs
GOOD_RUN = {
    "good":     ("COMPLETED",      "00:10:02", "00:15:00", 4, "00:39:50", "2G", "1650M"),
    "overcpu":  ("COMPLETED",      "00:10:01", "00:15:00", 8, "00:10:00", "1G", "12M"),
    "overmem":  ("COMPLETED",      "00:10:01", "00:15:00", 1, "00:10:00", "8G", "512M"),
    "overtime": ("COMPLETED",      "00:05:01", "02:00:00", 1, "00:05:00", "1G", "11M"),
    "oom":      ("OUT_OF_MEMORY",  "00:00:03", "00:15:00", 1, "00:00:02", "1G", "1024M"),
    "timeout":  ("TIMEOUT",        "00:02:30", "00:02:00", 1, "00:02:29", "1G", "11M"),
}


def sacct(jobs, first_id=900):
    rows = []
    for i, (kind, (state, el, tl, cpus, tot, req, rss)) in enumerate(jobs.items()):
        jid = str(first_id + i)
        rows.append("|".join([jid, "hpcflow_" + kind, "me", "k2", state, T, T, el, tl, str(cpus), tot, req, ""]))
        rows.append("|".join([jid + ".batch", "batch", "", "", state, T, T, el, "", str(cpus), tot, "", rss]))
    return HDR + "\n".join(rows) + "\n"


def run_check(tmp_path, jobs, extra_text=""):
    result = analysis.analyze(sacct(jobs) + extra_text)
    f = tmp_path / "pilot_result.json"
    f.write_text(json.dumps(result), encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, CHECK, str(f)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env, timeout=60)


def line_for(out, kind):
    return [l for l in out.splitlines() if (" %s " % kind) in (" " + l + " ")][0]


def test_all_six_pass(tmp_path):
    r = run_check(tmp_path, GOOD_RUN)
    assert r.returncode == 0, r.stdout + r.stderr
    for kind in GOOD_RUN:
        assert line_for(r.stdout, kind).startswith("PASS"), r.stdout
    assert "6/6 passed" in r.stdout


def test_wrong_verdict_fails(tmp_path):
    bad = dict(GOOD_RUN)
    bad["overcpu"] = ("COMPLETED", "00:10:01", "00:15:00", 8, "01:20:00", "1G", "12M")  # 100% CPU: no CPU advice
    r = run_check(tmp_path, bad)
    assert r.returncode == 1
    assert line_for(r.stdout, "overcpu").startswith("FAIL")
    assert "5/6 passed" in r.stdout


def test_missing_job(tmp_path):
    jobs = dict(GOOD_RUN)
    del jobs["timeout"]
    r = run_check(tmp_path, jobs)
    assert r.returncode == 1 and line_for(r.stdout, "timeout").startswith("MISSING")


def test_oom_not_enforced_is_inconclusive(tmp_path):
    jobs = dict(GOOD_RUN)
    jobs["oom"] = ("COMPLETED", "00:00:05", "00:15:00", 1, "00:00:04", "1G", "3072M")
    r = run_check(tmp_path, jobs)
    assert line_for(r.stdout, "oom").startswith("INCONCLUSIVE")
    assert r.returncode == 0  # not HPCFlow's fault: the cluster did not enforce the limit


def test_latest_run_wins(tmp_path):
    """If the pilot was submitted twice, the most recent job of each kind is checked."""
    old_bad = {"overcpu": ("COMPLETED", "00:10:01", "00:15:00", 8, "01:20:00", "1G", "12M")}
    extra = sacct(old_bad, first_id=100).split("\n", 1)[1]   # older job IDs, no header
    r = run_check(tmp_path, GOOD_RUN, extra_text=extra)
    assert line_for(r.stdout, "overcpu").startswith("PASS"), r.stdout


def test_python36_compatible_and_stdlib_only():
    import ast
    src = open(CHECK, encoding="utf-8").read()
    ast.parse(src, feature_version=(3, 7))
    for bad in ("capture_output", "fromisoformat", ":=", "dataclass", "import pandas", "import requests"):
        assert bad not in src, bad
