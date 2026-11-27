"""Data-quality line (v0.34). Written by the architect; implementation must pass it unchanged.
A missing figure must never read as zero, and support staff need to know how much of the report rests on real figures.
The summary gains "data_quality": {"jobs": N, "cpu": jobs with cpu_efficiency, "memory": jobs with memory_efficiency,
"time": jobs with time_used} (counts over analysed jobs).
The text report (and so the HTML report) adds, just before the first "Note:" line (or where it would be),
"Usable figures:        CPU 75%, memory 25%, time 100% of jobs" (whole percentages, rounded) when N > 0.
When memory figures exist for fewer than half the jobs (and N > 0), and no column warning about MaxRSS or ReqMem
already explains it, the warnings include:
"Memory figures are missing for 3 of 4 jobs: memory advice is low confidence."
(analysis.MEMORY_CONFIDENCE_SHARE = 0.5)."""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402

HEAD = "JobID|JobName|User|Partition|State|AllocCPUS|Elapsed|Timelimit|TotalCPU|ReqMem|MaxRSS\n"


def row(jid, total="00:30:00", rss="500M", limit="02:00:00"):
    return "%s|j|u1|p|COMPLETED|1|01:00:00|%s|%s|1G|%s\n" % (jid, limit, total, rss)


def run(*rows, head=HEAD):
    return analysis.analyze(head + "".join(rows))


def mem_notes(r):
    return [w for w in r["warnings"] if w.startswith("Memory figures are missing")]


def test_summary_counts():
    r = run(row(1), row(2, rss=""), row(3, rss="", total=""), row(4, rss=""))
    assert r["summary"]["data_quality"] == {"jobs": 4, "cpu": 3, "memory": 1, "time": 4}


def test_low_confidence_note():
    r = run(row(1), row(2, rss=""), row(3, rss=""), row(4, rss=""))
    assert analysis.MEMORY_CONFIDENCE_SHARE == 0.5
    assert mem_notes(r) == ["Memory figures are missing for 3 of 4 jobs: memory advice is low confidence."]


def test_no_note_at_half_or_more():
    assert mem_notes(run(row(1), row(2, rss=""))) == []
    assert mem_notes(run(row(1), row(2))) == []


def test_no_duplicate_when_column_missing():
    head = HEAD.replace("|MaxRSS", "")
    r = analysis.analyze(head + "1|j|u1|p|COMPLETED|1|01:00:00|02:00:00|00:30:00|1G\n")
    assert any("MaxRSS column missing" in w for w in r["warnings"])
    assert mem_notes(r) == []
    assert r["summary"]["data_quality"]["memory"] == 0


def test_report_line_before_notes():
    r = run(row(1), row(2, rss=""), row(3, rss="", total=""), row(4, rss=""))
    out = clusterflow_cli.report(r, 5).splitlines()
    i = out.index("Usable figures:        CPU 75%, memory 25%, time 100% of jobs")
    notes = [k for k, l in enumerate(out) if l.startswith("Note: ")]
    assert notes and i == notes[0] - 1


def test_report_line_without_notes():
    out = clusterflow_cli.report(run(row(1), row(2)), 5)
    assert "Usable figures:        CPU 100%, memory 100%, time 100% of jobs" in out
    page = clusterflow_cli.html_report(run(row(1), row(2)), 5)
    assert "Usable figures" in page and "CPU 100%, memory 100%, time 100% of jobs" in page


def test_rounding():
    r = run(row(1), row(2), row(3, rss=""))
    assert "memory 67%" in clusterflow_cli.report(r, 5)
