"""Queue wait by time limit (v0.22): gives researchers their own reason to request shorter limits.
Written by the architect; implementation must pass it unchanged.

- Each job gets "timelimit_s" (seconds, None if unknown).
- analysis.summarize_wait_by_limit(jobs) -> summary["wait_by_limit"]: bands in this order, only bands with at least
  one job that has both wait_s and timelimit_s:
    "up to 1 h" (<= 3600 s), "1-4 h" (<= 14400), "4-12 h" (<= 43200), "12-24 h" (<= 86400), "over 24 h"
  each {"label", "jobs", "median_wait_s", "p90_wait_s"} (analysis.percentile(waits, 50 / 90), as floats).
  v0.23: the median alone hid the long tail on real data (IN2P3: median <1m in every band, but 90% started within
  14m for limits up to 1 h vs 7h 53m for limits over 24 h), so the 90% mark is shown too.
- Report section (only with >= 2 bands), after the trend section:
    Queue wait by time limit
      up to 1 h          2 jobs  median 10m      90% within 15m
      4-12 h             1 job   median 2h 00m   90% within 2h 00m
      Longer limits waited longer here (90% mark): shorter limits can start sooner via Slurm backfill. Not a promise.
  The last line appears only when the longest band's 90% mark is above the shortest band's; otherwise:
      Waits did not grow with the time limit on this data.
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402

HDR = "JobID|State|Submit|Start|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"


def job(jid, wait_min, limit):
    start = "2026-11-20T%02d:%02d:00" % (9 + wait_min // 60, wait_min % 60)
    return ("%s|COMPLETED|2026-11-20T09:00:00|%s|00:30:00|%s|1|00:30:00|1G|\n" % (jid, start, limit)
            + "%s.batch|COMPLETED||%s|00:30:00||1|00:30:00||500M\n" % (jid, start))


DATA = HDR + job(1, 5, "01:00:00") + job(2, 15, "00:45:00") + job(3, 120, "08:00:00")


def test_timelimit_on_each_job():
    jobs = analysis.analyze(DATA)["jobs"]
    assert [j["timelimit_s"] for j in jobs] == [3600, 2700, 28800]


def test_bands():
    bands = analysis.analyze(DATA)["summary"]["wait_by_limit"]
    assert bands == [{"label": "up to 1 h", "jobs": 2, "median_wait_s": 600.0, "p90_wait_s": 900.0},
                     {"label": "4-12 h", "jobs": 1, "median_wait_s": 7200.0, "p90_wait_s": 7200.0}]


def test_band_edges():
    data = HDR + job(1, 1, "04:00:00") + job(2, 1, "04:00:01") + job(3, 1, "1-00:00:00") + job(4, 1, "1-00:00:01")
    labels = [b["label"] for b in analysis.analyze(data)["summary"]["wait_by_limit"]]
    assert labels == ["1-4 h", "4-12 h", "12-24 h", "over 24 h"]


def test_no_wait_data_no_bands():
    data = "JobID|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n1|COMPLETED|00:30:00|01:00:00|1|00:30:00|1G|\n"
    assert analysis.analyze(data)["summary"]["wait_by_limit"] == []


def norm(text):
    return [" ".join(l.split()) for l in text.splitlines()]


def test_report_section():
    out = norm(clusterflow_cli.report(analysis.analyze(DATA), 5))
    i = out.index("Queue wait by time limit")
    assert out[i + 1:i + 4] == ["up to 1 h 2 jobs median 10m 90% within 15m", "4-12 h 1 job median 2h 00m 90% within 2h 00m",
                                "Longer limits waited longer here (90% mark): shorter limits can start sooner via Slurm backfill. Not a promise."]


def test_note_when_waits_do_not_grow():
    data = HDR + job(1, 120, "01:00:00") + job(2, 5, "08:00:00")
    out = norm(clusterflow_cli.report(analysis.analyze(data), 5))
    assert "Waits did not grow with the time limit on this data." in out
    assert not any("shorter limits can start sooner" in l for l in out)


def test_no_section_with_one_band():
    data = HDR + job(1, 5, "01:00:00") + job(2, 15, "00:45:00")
    assert "Queue wait by time limit" not in clusterflow_cli.report(analysis.analyze(data), 5)


def test_demo_shows_section():
    assert "Queue wait by time limit" in clusterflow_cli.report(analysis.analyze(clusterflow_cli.DEMO_SACCT), 5)


def test_web_page_renders_bands():
    """Web parity: the page shows the same section (only with >= 2 bands), built with textContent."""
    import re
    with open(os.path.join(ROOT, "frontend", "index.html"), encoding="utf-8") as f:
        page = f.read()
    body = re.search(r"function renderWaitByLimit\(bands\) \{(.*?)\n        \}", page, re.S).group(1)
    assert "bands.length < 2" in body
    assert "'Queue wait by time limit'" in body and "fmtWait(" in body
    assert "b.p90_wait_s" in body and "'90% started within'" in body
    assert "shorter limits can start sooner via Slurm backfill. Not a promise." in body
    assert "Waits did not grow with the time limit on this data." in body
    assert "innerHTML" not in body
    assert "renderWaitByLimit(data.summary.wait_by_limit || [])" in page
