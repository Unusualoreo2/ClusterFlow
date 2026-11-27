"""Typical-job advice cites only measured runs (v0.35). Written by the architect; implementation must pass it unchanged.
summarize_profiles groups >= min_runs COMPLETED runs per (user, name). Before v0.35 each line said "Across N runs"
with N = all runs, even when only some runs had that figure, and sized the advice from those few.
Now each kind of advice needs at least min_runs runs that MEASURED that figure:
  CPU advice: runs with cpu_efficiency; memory advice: runs with max_rss_mb; time advice: runs with elapsed_s.
Each line's "Across N runs" uses that measured count. Each profile gains
"measured": {"cpu": ..., "memory": ..., "time": ...} (those counts). With every figure present nothing changes."""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402

HEAD = "JobID|JobName|User|Partition|State|AllocCPUS|Elapsed|Timelimit|TotalCPU|ReqMem|MaxRSS\n"


def row(jid, rss="1000M", total="01:00:00"):
    # 8 CPUs, 1 busy; 32G requested; 1 h of a 24 h limit
    return "%s|sim|u1|p|COMPLETED|8|01:00:00|1-00:00:00|%s|32G|%s\n" % (jid, total, rss)


def profile(*rows):
    ps = analysis.analyze(HEAD + "".join(rows))["summary"]["profiles"]
    assert len(ps) == 1
    return ps[0]


def lines(p, word):
    return [r for r in p["recommendations"] if word in r]


def test_all_measured_unchanged():
    p = profile(*[row(i) for i in range(5)])
    assert p["measured"] == {"cpu": 5, "memory": 5, "time": 5}
    assert lines(p, "--mem=")[0].startswith("Across 5 runs")
    assert lines(p, "--cpus-per-task=")[0].startswith("Across 5 runs")
    assert lines(p, "--time=")[0].startswith("Across 5 runs")


def test_memory_needs_enough_measured_runs():
    p = profile(row(1), row(2), row(3, rss=""), row(4, rss=""), row(5, rss=""))
    assert p["measured"]["memory"] == 2
    assert lines(p, "--mem=") == []
    assert not any("--mem=" in s for s in p["sbatch"])
    assert lines(p, "--cpus-per-task=")[0].startswith("Across 5 runs")


def test_memory_line_cites_measured_count():
    p = profile(row(1), row(2), row(3), row(4, rss=""), row(5, rss=""))
    assert p["measured"]["memory"] == 3
    assert lines(p, "--mem=")[0].startswith("Across 3 runs")


def test_cpu_needs_enough_measured_runs():
    p = profile(row(1), row(2, total=""), row(3, total=""), row(4, total=""))
    assert p["measured"]["cpu"] == 1
    assert lines(p, "--cpus-per-task=") == []
    assert lines(p, "--mem=")[0].startswith("Across 4 runs")
