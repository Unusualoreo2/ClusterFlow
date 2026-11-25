"""Advice from a user's typical jobs across many runs (v0.12). Written by the architect.
Per (user, job name) with >= 3 completed runs: size to near-worst runs (p90 cores, p95 memory, p95 time)."""
import os
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis as a  # noqa: E402

HDR = "JobID|JobName|User|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"


def run_row(jid, name="sim", user="ann", state="COMPLETED", el="01:00:00", tl="12:00:00", cpus=16, tot="02:00:00",
            req="64G", rss="4000M"):
    return ("%s|%s|%s|%s|%s|%s|%d|%s|%s|\n" % (jid, name, user, state, el, tl, cpus, tot, req)
            + "%s.batch|batch||%s|%s||%d|%s||%s\n" % (jid, state, el, cpus, tot, rss))


def test_percentile():
    assert a.percentile([5, 1, 3, 2, 4], 50) == 3
    assert a.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90) == 9
    assert a.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == 10
    assert a.percentile([], 90) is None


def test_profile_sizes_to_near_worst_runs():
    # 10 runs of 'sim': cores used 2..? (TotalCPU / Elapsed), memory 1000..10000M, all 1 h of 12 h
    rows = "".join(run_row(i, tot="%02d:00:00" % (i if i < 10 else 2), rss="%dM" % (i * 1000)) for i in range(1, 11))
    profiles = a.analyze(HDR + rows)["summary"]["profiles"]
    assert len(profiles) == 1
    p = profiles[0]
    assert p["user"] == "ann" and p["name"] == "sim" and p["runs"] == 10
    assert p["cpus_requested"] == 16 and p["cpus_needed"] == 10        # p90 cores = 8 -> ceil(8 x 1.2)
    assert p["mem_requested_mb"] == pytest.approx(65536)
    assert p["mem_needed_mb"] == 12000                                  # p95 = 10000M -> ceil(10000 x 1.2)
    assert p["time_needed_s"] == 5400                                   # p95 = 1 h -> 1.5 h
    text = " ".join(p["recommendations"])
    assert "--cpus-per-task=10" in text and "--mem=12000M" in text and "--time=01:30:00" in text
    assert "10 runs" in text


def test_one_small_run_does_not_shrink_the_advice():
    # 9 runs need ~30 GB, 1 run used 2 GB: per-job advice for that run would be dangerous, the profile is not
    rows = "".join(run_row(i, rss="30000M") for i in range(1, 10)) + run_row(10, rss="2000M")
    p = a.analyze(HDR + rows)["summary"]["profiles"][0]
    assert p["mem_needed_mb"] == 36000


def test_only_completed_runs_and_minimum_three():
    rows = (run_row(1) + run_row(2) + run_row(3, state="FAILED") + run_row(4, state="OUT_OF_MEMORY")
            + run_row(5, name="other") + run_row(6, name="other") + run_row(7, name="other"))
    profiles = a.analyze(HDR + rows)["summary"]["profiles"]
    assert [(p["name"], p["runs"]) for p in profiles] == [("other", 3)]


def test_no_advice_when_well_sized():
    rows = "".join(run_row(i, cpus=2, tot="02:00:00", req="5G", rss="4000M", tl="01:30:00") for i in range(1, 5))
    p = a.analyze(HDR + rows)["summary"]["profiles"][0]
    assert p["recommendations"] == []


def test_profiles_sorted_by_waste_and_separate_per_user():
    rows = ("".join(run_row(i, user="ann", cpus=4) for i in range(1, 4))
            + "".join(run_row(10 + i, user="bob", cpus=32) for i in range(1, 4)))
    profiles = a.analyze(HDR + rows)["summary"]["profiles"]
    assert [p["user"] for p in profiles] == ["bob", "ann"]


def test_no_profiles_without_names():
    rows = "1|COMPLETED|01:00:00|1|01:00:00\n2|COMPLETED|01:00:00|1|01:00:00\n3|COMPLETED|01:00:00|1|01:00:00\n"
    assert a.analyze("JobID|State|Elapsed|AllocCPUS|TotalCPU\n" + rows)["summary"]["profiles"] == []


def test_cli_typical_jobs_section(tmp_path):
    rows = "".join(run_row(i, tot="%02d:00:00" % (i if i < 10 else 2), rss="%dM" % (i * 1000)) for i in range(1, 11))
    f = tmp_path / "p.txt"
    f.write_text(HDR + rows, encoding="utf-8")
    cli = os.path.join(ROOT, "backend", "hpcflow_cli.py")
    out = subprocess.run([sys.executable, cli, str(f)], stdout=subprocess.PIPE, universal_newlines=True, timeout=60).stdout
    assert "Typical jobs (sized from repeated runs)" in out
    assert "ann / sim (10 runs)" in out and "--cpus-per-task=10" in out
