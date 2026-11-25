"""Queue wait time from Submit/Start (v0.5). Written by the architect; implementation must pass it unchanged."""
import os
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis as a  # noqa: E402
import clusterflow_cli  # noqa: E402

TEXT = (
    "JobID|User|State|Submit|Start|Elapsed|AllocCPUS|TotalCPU\n"
    "1|ann|COMPLETED|2026-11-20T09:00:00|2026-11-20T09:30:00|01:00:00|1|01:00:00\n"   # 30 min
    "1.batch||COMPLETED|2026-11-20T09:30:00|2026-11-20T09:30:00|01:00:00|1|01:00:00\n"
    "2|ann|COMPLETED|2026-11-20T10:00:00|2026-11-21T12:00:00|01:00:00|1|01:00:00\n"   # 26 h
    "3|bob|CANCELLED by 0|2026-11-20T10:00:00|None|00:00:00|0|00:00:00\n"           # never started
    "4|bob|COMPLETED|2026-11-20T10:00:00|2026-11-20T10:00:05|01:00:00|1|01:00:00\n"   # 5 s
)


@pytest.mark.parametrize("text,ok", [
    ("2026-11-20T09:00:00", True), ("Unknown", False), ("None", False), ("", False),
    ("2026-13-40T99:00:00", False), (None, False), ("2026-11-20 09:00:00", True),
])
def test_parse_timestamp(text, ok):
    assert (a.parse_timestamp(text) is not None) == ok


def test_wait_per_job():
    jobs = {j["job_id"]: j for j in a.analyze(TEXT)["jobs"]}
    assert jobs["1"]["wait_s"] == 1800
    assert jobs["2"]["wait_s"] == 26 * 3600
    assert jobs["3"]["wait_s"] is None
    assert jobs["4"]["wait_s"] == 5


def test_wait_summary_and_groups():
    s = a.analyze(TEXT)["summary"]
    assert s["avg_wait_s"] == pytest.approx((1800 + 93600 + 5) / 3)
    assert s["max_wait_s"] == 93600
    by_user = {g["name"]: g for g in s["by_user"]}
    assert by_user["ann"]["avg_wait_s"] == pytest.approx((1800 + 93600) / 2)
    assert by_user["bob"]["avg_wait_s"] == pytest.approx(5)


def test_no_wait_columns():
    s = a.analyze("JobID|State|Elapsed|AllocCPUS|TotalCPU\n1|COMPLETED|01:00:00|1|01:00:00\n")["summary"]
    assert s["avg_wait_s"] is None and s["max_wait_s"] is None
    assert a.analyze("JobID|State|Elapsed|AllocCPUS|TotalCPU\n1|COMPLETED|01:00:00|1|01:00:00\n")["jobs"][0]["wait_s"] is None


def test_start_before_submit_is_ignored():
    t = ("JobID|State|Submit|Start|Elapsed|AllocCPUS|TotalCPU\n"
         "1|COMPLETED|2026-11-20T10:00:00|2026-11-20T09:00:00|01:00:00|1|01:00:00\n")
    assert a.analyze(t)["jobs"][0]["wait_s"] is None


@pytest.mark.parametrize("secs,text", [
    (None, "-"), (5, "<1m"), (59, "<1m"), (60, "1m"), (1800, "30m"), (3600, "1h 00m"),
    (3900, "1h 05m"), (93600, "1d 02h"), (90000, "1d 01h"),
])
def test_fmt_wait(secs, text):
    assert clusterflow_cli.fmt_wait(secs) == text


def test_cli_shows_wait(tmp_path):
    f = tmp_path / "w.txt"
    f.write_text(TEXT, encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    out = subprocess.run([sys.executable, os.path.join(ROOT, "backend", "clusterflow_cli.py"), str(f)],
                         capture_output=True, text=True, encoding="utf-8", env=env, timeout=60).stdout
    assert "Avg queue wait:" in out and "8h 50m" in out      # (1800+93600+5)/3 = 31801.7 s
    assert "Max queue wait:" in out and "1d 02h" in out


def test_cli_hides_wait_lines_without_columns(tmp_path):
    f = tmp_path / "p.txt"
    f.write_text("JobID|State|Elapsed|AllocCPUS|TotalCPU\n1|COMPLETED|01:00:00|1|01:00:00\n", encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    out = subprocess.run([sys.executable, os.path.join(ROOT, "backend", "clusterflow_cli.py"), str(f)],
                         capture_output=True, text=True, encoding="utf-8", env=env, timeout=60).stdout
    assert "queue wait" not in out.lower()
