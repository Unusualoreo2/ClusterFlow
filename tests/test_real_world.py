"""Real-world sacct quirks (v0.3). Written by the architect; implementation must pass them unchanged."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import analysis as a  # noqa: E402

HDR = "JobID|JobName|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"


def run(body):
    return a.analyze(HDR + body)


def test_array_jobs_are_separate_jobs():
    out = run(
        "500_1|arr|COMPLETED|01:00:00|02:00:00|2|02:00:00|4G|\n"
        "500_1.batch|batch|COMPLETED|01:00:00||2|02:00:00||1000M\n"
        "500_2|arr|COMPLETED|01:00:00|02:00:00|2|01:00:00|4G|\n"
        "500_2.batch|batch|COMPLETED|01:00:00||2|01:00:00||3000M\n"
        "500_[3-10]|arr|PENDING|00:00:00|02:00:00|0|00:00:00|4G|\n"
    )
    assert [j["job_id"] for j in out["jobs"]] == ["500_1", "500_2"]
    assert out["skipped"] == 1
    assert out["jobs"][1]["memory_efficiency"] == pytest.approx(3000 / 4096 * 100)


def test_extern_step_counts_for_memory():
    out = run(
        "600|x|COMPLETED|01:00:00|02:00:00|1|01:00:00|4G|\n"
        "600.extern|extern|COMPLETED|01:00:00||1|00:00:00||3500M\n"
        "600.batch|batch|COMPLETED|01:00:00||1|01:00:00||200M\n"
    )
    assert out["jobs"][0]["memory_efficiency"] == pytest.approx(3500 / 4096 * 100)


def test_cancelled_by_user_and_never_started():
    out = run(
        "700|x|CANCELLED by 12345|00:00:00|01:00:00|0|00:00:00|4G|\n"
        "701|y|CANCELLED by 12345|00:30:00|01:00:00|4|01:00:00|4G|\n"
        "701.batch|batch|CANCELLED|00:30:00||4|01:00:00||1000M\n"
    )
    j700, j701 = out["jobs"]
    assert j700["cpu_efficiency"] is None and j700["recommendations"] == []
    assert j701["cpu_efficiency"] == pytest.approx(50.0)


def test_kilobyte_memory_without_units_flag():
    out = run(
        "800|x|COMPLETED|01:00:00|02:00:00|1|01:00:00|8G|\n"
        "800.batch|batch|COMPLETED|01:00:00||1|01:00:00||2097152K\n"
    )
    assert out["jobs"][0]["memory_efficiency"] == pytest.approx(25.0)


def test_heterogeneous_job_components():
    out = run(
        "900+0|het|COMPLETED|01:00:00|02:00:00|2|02:00:00|4G|\n"
        "900+0.batch|batch|COMPLETED|01:00:00||2|02:00:00||2048M\n"
        "900+1|het|COMPLETED|01:00:00|02:00:00|4|02:00:00|4G|\n"
    )
    assert [j["job_id"] for j in out["jobs"]] == ["900+0", "900+1"]


def test_windows_line_endings_and_trailing_delimiter():
    text = (HDR.rstrip("\n") + "|\r\n"
            "1|x|COMPLETED|01:00:00|02:00:00|1|01:00:00|4G||\r\n"
            "1.batch|batch|COMPLETED|01:00:00||1|01:00:00||1024M|\r\n")
    out = a.analyze(text)
    assert out["jobs"][0]["memory_efficiency"] == pytest.approx(25.0)


def test_repeated_header_lines_are_ignored():
    out = a.analyze(HDR + "1|x|COMPLETED|01:00:00|02:00:00|1|01:00:00|4G|\n" + HDR
                    + "2|y|COMPLETED|01:00:00|02:00:00|1|01:00:00|4G|\n")
    assert [j["job_id"] for j in out["jobs"]] == ["1", "2"]


def test_failed_and_node_fail_states_are_analysed():
    out = run(
        "1|x|FAILED|00:10:00|01:00:00|1|00:10:00|4G|\n"
        "2|y|NODE_FAIL|00:10:00|01:00:00|1|00:10:00|4G|\n"
    )
    assert len(out["jobs"]) == 2 and out["skipped"] == 0


def test_requeued_and_suspended_are_skipped():
    out = run(
        "1|x|REQUEUED|00:10:00|01:00:00|1|00:10:00|4G|\n"
        "2|y|SUSPENDED|00:10:00|01:00:00|1|00:10:00|4G|\n"
        "3|z|COMPLETED|00:10:00|01:00:00|1|00:10:00|4G|\n"
    )
    assert [j["job_id"] for j in out["jobs"]] == ["3"] and out["skipped"] == 2
