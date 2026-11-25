"""Usage trend over time (v0.10). Written by the architect; implementation must pass it unchanged."""
import os
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis as a  # noqa: E402

HDR = "JobID|State|Submit|Start|Elapsed|AllocCPUS|TotalCPU\n"


def job(jid, start, cpus=4, tot="01:00:00", submit=None):
    return "%s|COMPLETED|%s|%s|01:00:00|%d|%s\n" % (jid, submit or start, start, cpus, tot)


def test_start_date_field():
    out = a.analyze(HDR + job(1, "2026-11-20T09:00:00") + "2|COMPLETED|2026-11-21T10:00:00|Unknown|00:00:00|1|00:00:00\n")
    assert [j["start_date"] for j in out["jobs"]] == ["2026-11-20", "2026-11-21"]  # falls back to Submit


def test_daily_trend_for_short_ranges():
    text = HDR + job(1, "2026-11-20T09:00:00") + job(2, "2026-11-20T15:00:00", tot="04:00:00") + job(3, "2026-11-22T08:00:00")
    t = a.analyze(text)["summary"]["trend"]
    assert t["period"] == "day"
    assert [r["name"] for r in t["rows"]] == ["2026-11-20", "2026-11-22"]       # oldest first, empty days omitted
    day1 = t["rows"][0]
    assert day1["job_count"] == 2 and day1["avg_cpu_efficiency"] == pytest.approx((25 + 100) / 2)
    assert day1["wasted_core_hours"] == pytest.approx(3.0)


def test_weekly_trend_for_long_ranges():
    text = (HDR + job(1, "2026-10-01T09:00:00") + job(2, "2026-10-02T09:00:00")   # Thu, Fri of week starting Mon 2026-09-28
            + job(3, "2026-11-23T09:00:00"))                                      # Monday 2026-11-23
    t = a.analyze(text)["summary"]["trend"]
    assert t["period"] == "week"
    assert [r["name"] for r in t["rows"]] == ["2026-09-28", "2026-11-23"]        # week = Monday's date
    assert t["rows"][0]["job_count"] == 2


def test_no_trend_without_dates():
    t = a.analyze("JobID|State|Elapsed|AllocCPUS|TotalCPU\n1|COMPLETED|01:00:00|1|01:00:00\n")["summary"]["trend"]
    assert t == {"period": None, "rows": []}


def test_trend_rows_have_group_fields():
    r = a.analyze(HDR + job(1, "2026-11-20T09:00:00") + job(2, "2026-11-21T09:00:00"))["summary"]["trend"]["rows"][0]
    for key in ("job_count", "avg_cpu_efficiency", "avg_memory_efficiency", "wasted_core_hours", "gpu_hours", "avg_wait_s"):
        assert key in r


def test_cli_trend_table(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text(HDR + job(1, "2026-11-20T09:00:00") + job(2, "2026-11-21T09:00:00", tot="04:00:00"), encoding="utf-8")
    cli = os.path.join(ROOT, "backend", "clusterflow_cli.py")
    out = subprocess.run([sys.executable, cli, str(f)], stdout=subprocess.PIPE, universal_newlines=True, timeout=60).stdout
    assert "Trend by day" in out
    lines = out.splitlines()
    i = lines.index("Trend by day")
    assert lines[i + 2].strip().startswith("2026-11-20") and lines[i + 3].strip().startswith("2026-11-21")


def test_cli_no_trend_for_a_single_period(tmp_path):
    f = tmp_path / "s.txt"
    f.write_text(HDR + job(1, "2026-11-20T09:00:00"), encoding="utf-8")
    cli = os.path.join(ROOT, "backend", "clusterflow_cli.py")
    out = subprocess.run([sys.executable, cli, str(f)], stdout=subprocess.PIPE, universal_newlines=True, timeout=60).stdout
    assert "Trend by" not in out


def test_cli_prints_the_trend_once(tmp_path):
    f = tmp_path / "o.txt"
    f.write_text(HDR + job(1, "2026-11-20T09:00:00") + job(2, "2026-11-21T09:00:00"), encoding="utf-8")
    cli = os.path.join(ROOT, "backend", "clusterflow_cli.py")
    out = subprocess.run([sys.executable, cli, str(f)], stdout=subprocess.PIPE, universal_newlines=True, timeout=60).stdout
    assert out.count("Trend by day") == 1
