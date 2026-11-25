"""Acceptance tests for backend/analysis.py (written by the architect; implementation must pass them unchanged)."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import analysis as a  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "..", "data")


# ---- parse_duration -------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("00:30", 30), ("05:30", 330), ("01:05:30", 3930), ("1-02:00:00", 93600),
    ("00:01.500", 1.5), ("12:00:00", 43200), ("2-00:00:00", 172800),
])
def test_parse_duration(text, expected):
    assert a.parse_duration(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["", "UNLIMITED", "Partition_Limit", "INVALID", None])
def test_parse_duration_missing(text):
    assert a.parse_duration(text) is None


# ---- parse_mem_mb ---------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("4200M", 4200), ("3.5G", 3584), ("2048K", 2), ("1T", 1048576), ("512", 512), ("0", 0),
])
def test_parse_mem_mb(text, expected):
    assert a.parse_mem_mb(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["", None, "abc"])
def test_parse_mem_mb_missing(text):
    assert a.parse_mem_mb(text) is None


# ---- parse_req_mem --------------------------------------------------------
def test_req_mem_per_cpu():
    assert a.parse_req_mem("4000Mc", alloc_cpus=4) == pytest.approx(16000)


def test_req_mem_per_node_and_plain():
    assert a.parse_req_mem("16Gn", alloc_cpus=8) == pytest.approx(16384)
    assert a.parse_req_mem("16G", alloc_cpus=8) == pytest.approx(16384)
    assert a.parse_req_mem("", alloc_cpus=8) is None


# ---- read_sacct / merge_steps ---------------------------------------------
PIPE = (
    "JobID|JobName|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"
    "101|sim|COMPLETED|02:00:00|08:00:00|8|04:00:00|16G|\n"
    "101.batch|batch|COMPLETED|02:00:00||8|04:00:00||3000M\n"
    "101.0|sim|COMPLETED|01:59:00||8|03:59:00||3500M\n"
    "102|run|RUNNING|00:10:00|01:00:00|4|00:20:00|8G|\n"
)


def test_read_sacct_pipe_and_comma():
    rows = a.read_sacct(PIPE)
    assert len(rows) == 4 and rows[0]["JobID"] == "101" and rows[2]["MaxRSS"] == "3500M"
    comma = PIPE.replace("|", ",")
    assert a.read_sacct(comma) == rows


def test_read_sacct_ignores_blank_lines_and_whitespace():
    rows = a.read_sacct("\n" + PIPE.replace("|sim|", "| sim |") + "\n\n")
    assert len(rows) == 4 and rows[0]["JobName"] == "sim"


def test_merge_steps_takes_max_rss_and_parent_fields():
    jobs = a.merge_steps(a.read_sacct(PIPE))
    assert [j["JobID"] for j in jobs] == ["101", "102"]
    assert jobs[0]["MaxRSS"] == "3500M"
    assert jobs[0]["ReqMem"] == "16G" and jobs[0]["Timelimit"] == "08:00:00"


# ---- analyze_job ----------------------------------------------------------
def job(**kw):
    base = {"JobID": "1", "JobName": "x", "State": "COMPLETED", "Elapsed": "01:00:00",
            "Timelimit": "02:00:00", "AllocCPUS": "4", "TotalCPU": "04:00:00",
            "ReqMem": "8G", "MaxRSS": "6000M"}
    base.update(kw)
    return base


def test_metrics():
    r = a.analyze_job(job(TotalCPU="02:00:00", MaxRSS="2048M", Timelimit="10:00:00"))
    assert r["job_id"] == "1" and r["name"] == "x" and r["state"] == "COMPLETED"
    assert r["elapsed_s"] == 3600 and r["alloc_cpus"] == 4
    assert r["cpu_efficiency"] == pytest.approx(50.0)
    assert r["memory_efficiency"] == pytest.approx(25.0)
    assert r["time_used"] == pytest.approx(10.0)
    assert r["wasted_core_hours"] == pytest.approx(2.0)


def test_efficient_job_has_no_recommendations():
    r = a.analyze_job(job())  # 100% CPU, 73% memory, 50% time
    assert r["recommendations"] == []


def test_low_cpu_recommendation():
    r = a.analyze_job(job(AllocCPUS="16", TotalCPU="04:00:00"))  # 25% efficiency
    text = " ".join(r["recommendations"])
    assert "--cpus" in text or "CPUs" in text
    assert "5" in text  # ceil(16 * 0.25 * 1.2) = 5


def test_low_memory_recommendation():
    r = a.analyze_job(job(ReqMem="32G", MaxRSS="4000M"))
    assert any("5000" in s for s in r["recommendations"])  # ceil(4000 * 1.25)


def test_high_memory_warning():
    r = a.analyze_job(job(ReqMem="8G", MaxRSS="8000M"))
    assert any("memory limit" in s.lower() for s in r["recommendations"])


def test_short_runtime_recommendation():
    r = a.analyze_job(job(Elapsed="00:20:00", TotalCPU="01:20:00", Timelimit="10:00:00"))
    assert any("00:30:00" in s for s in r["recommendations"])  # 20 min * 1.5 = 30 min


def test_oom_and_timeout_states():
    oom = a.analyze_job(job(State="OUT_OF_MEMORY"))
    to = a.analyze_job(job(State="TIMEOUT", Elapsed="02:00:00", TotalCPU="08:00:00"))
    assert any("memory" in s.lower() for s in oom["recommendations"])
    assert any("time" in s.lower() for s in to["recommendations"])


def test_oom_suggests_concrete_memory():
    r = a.analyze_job(job(State="OUT_OF_MEMORY", ReqMem="8G", MaxRSS="8190M"))
    oom = r["recommendations"][0]
    assert "--mem=12288M" in oom  # v0.24: ceil(max(MaxRSS 8190, request 8192) * 1.5)
    assert "<" not in oom and "ceil" not in oom and oom.count("(") == oom.count(")")


def test_missing_values_do_not_crash():
    r = a.analyze_job(job(MaxRSS="", ReqMem="", Timelimit="UNLIMITED"))
    assert r["memory_efficiency"] is None and r["time_used"] is None
    assert r["cpu_efficiency"] == pytest.approx(100.0)


def test_zero_elapsed_does_not_crash():
    r = a.analyze_job(job(Elapsed="00:00", TotalCPU="00:00"))
    assert r["cpu_efficiency"] is None


# ---- analyze (whole file) -------------------------------------------------
def test_analyze_skips_running_and_summarises():
    out = a.analyze(PIPE)
    assert out["skipped"] == 1 and len(out["jobs"]) == 1
    j = out["jobs"][0]
    assert j["cpu_efficiency"] == pytest.approx(25.0)
    assert j["memory_efficiency"] == pytest.approx(3500 / 16384 * 100)
    s = out["summary"]
    assert s["job_count"] == 1
    assert s["avg_cpu_efficiency"] == pytest.approx(25.0)
    assert s["total_wasted_core_hours"] == pytest.approx(12.0)


def test_analyze_rejects_missing_columns():
    with pytest.raises(ValueError):
        a.analyze("JobID|Elapsed\n1|00:10:00\n")


def test_example_file():
    with open(os.path.join(DATA, "example_sacct.txt"), encoding="utf-8") as f:
        out = a.analyze(f.read())
    assert out["summary"]["job_count"] >= 4
    assert all(not math.isnan(j["cpu_efficiency"]) for j in out["jobs"] if j["cpu_efficiency"] is not None)
