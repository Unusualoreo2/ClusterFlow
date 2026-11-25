"""Per-user and per-partition summaries (v0.3). Written by the architect; implementation must pass them unchanged."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import analysis as a  # noqa: E402

TEXT = (
    "JobID|JobName|User|Partition|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"
    # alice: 2 jobs on 'compute'. 8 CPUs x 1 h, 2 CPU-h used -> 6 wasted; 4 CPUs x 1 h, 4 used -> 0 wasted
    "1|a1|alice|compute|COMPLETED|01:00:00|02:00:00|8|02:00:00|8G|\n"
    "1.batch|batch||compute|COMPLETED|01:00:00||8|02:00:00||2048M\n"
    "2|a2|alice|compute|COMPLETED|01:00:00|02:00:00|4|04:00:00|8G|\n"
    "2.batch|batch||compute|COMPLETED|01:00:00||4|04:00:00||6144M\n"
    # bob: 1 job on 'gpu'. 16 CPUs x 1 h, 4 used -> 12 wasted
    "3|b1|bob|gpu|COMPLETED|01:00:00|02:00:00|16|04:00:00|8G|\n"
    "3.batch|batch||gpu|COMPLETED|01:00:00||16|04:00:00||1024M\n"
    # bob: running job is skipped and not counted in groups
    "4|b2|bob|compute|RUNNING|00:10:00|02:00:00|4|00:10:00|8G|\n"
)


def test_jobs_carry_user_and_partition():
    jobs = a.analyze(TEXT)["jobs"]
    assert [(j["user"], j["partition"]) for j in jobs] == [("alice", "compute"), ("alice", "compute"), ("bob", "gpu")]


def test_by_user_sorted_by_waste():
    by_user = a.analyze(TEXT)["summary"]["by_user"]
    assert [g["name"] for g in by_user] == ["bob", "alice"]
    bob, alice = by_user
    assert bob["job_count"] == 1 and bob["wasted_core_hours"] == pytest.approx(12.0)
    assert alice["job_count"] == 2 and alice["wasted_core_hours"] == pytest.approx(6.0)
    assert alice["avg_cpu_efficiency"] == pytest.approx((25.0 + 100.0) / 2)
    assert alice["avg_memory_efficiency"] == pytest.approx((25.0 + 75.0) / 2)


def test_by_partition():
    by_part = a.analyze(TEXT)["summary"]["by_partition"]
    assert [(g["name"], g["job_count"]) for g in by_part] == [("gpu", 1), ("compute", 2)]


def test_groups_empty_when_columns_absent():
    text = "JobID|State|Elapsed|AllocCPUS|TotalCPU\n1|COMPLETED|01:00:00|1|01:00:00\n"
    s = a.analyze(text)["summary"]
    assert s["by_user"] == [] and s["by_partition"] == []
    assert a.analyze(text)["jobs"][0]["user"] == ""


def test_blank_user_grouped_as_unknown():
    text = ("JobID|User|State|Elapsed|AllocCPUS|TotalCPU\n"
            "1||COMPLETED|01:00:00|2|01:00:00\n"
            "2|carol|COMPLETED|01:00:00|1|01:00:00\n")
    names = [g["name"] for g in a.analyze(text)["summary"]["by_user"]]
    assert names == ["(unknown)", "carol"]


def test_group_averages_none_when_no_values():
    text = "JobID|User|State|Elapsed|AllocCPUS|TotalCPU\n1|dave|COMPLETED|01:00:00|1|01:00:00\n"
    g = a.analyze(text)["summary"]["by_user"][0]
    assert g["avg_memory_efficiency"] is None and g["avg_cpu_efficiency"] == pytest.approx(100.0)


def test_group_average_ignores_jobs_without_a_value():
    text = ("JobID|User|State|Elapsed|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"
            "1|erin|COMPLETED|01:00:00|1|01:00:00|4G|2048M\n"   # memory 50%
            "2|erin|COMPLETED|01:00:00|1|01:00:00||\n")          # no memory data
    g = a.analyze(text)["summary"]["by_user"][0]
    assert g["job_count"] == 2
    assert g["avg_memory_efficiency"] == pytest.approx(50.0)  # not 25.0
