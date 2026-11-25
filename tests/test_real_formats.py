"""Real-world export formats (v0.8), modelled on public sacct captures (tab-separated, partial columns,
lowercase headers, TRES strings, unpadded/fixed-width output). Written by the architect."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import analysis as a  # noqa: E402


# ---- delimiters and header case ----------------------------------------------
def test_tab_separated():
    text = ("JobID\tState\tElapsed\tAllocCPUS\tTotalCPU\tReqMem\tMaxRSS\n"
            "7585175\tCOMPLETED\t01:00:00\t4\t02:00:00\t8G\t\n"
            "7585175.batch\tCOMPLETED\t01:00:00\t4\t02:00:00\t\t2048M\n")
    j = a.analyze(text)["jobs"][0]
    assert j["cpu_efficiency"] == pytest.approx(50.0) and j["memory_efficiency"] == pytest.approx(25.0)


def test_lowercase_and_mixed_case_headers():
    text = ("jobid|state|elapsed|alloccpus|totalcpu|reqmem|maxrss|user\n"
            "1|COMPLETED|01:00:00|2|01:00:00|4G|1024M|ann\n")
    out = a.analyze(text)
    j = out["jobs"][0]
    assert j["cpu_efficiency"] == pytest.approx(50.0) and j["memory_efficiency"] == pytest.approx(25.0)
    assert out["summary"]["by_user"][0]["name"] == "ann"


# ---- relaxed required columns ------------------------------------------------
def test_only_jobid_and_state_required():
    text = "JobID|ExitCode|State|MaxRSS|Elapsed\n1|0:0|COMPLETED|500M|00:10:00\n2|0:0|FAILED||00:00:05\n"
    out = a.analyze(text)
    assert [j["job_id"] for j in out["jobs"]] == ["1", "2"]
    assert out["jobs"][0]["cpu_efficiency"] is None and out["jobs"][0]["memory_efficiency"] is None
    w = " ".join(out["warnings"])
    assert "TotalCPU" in w and "CPU efficiency" in w
    assert "ReqMem" in w and "memory efficiency" in w


def test_missing_jobid_or_state_still_rejected_with_command():
    with pytest.raises(ValueError) as e:
        a.analyze("Elapsed|MaxRSS\n00:10:00|1G\n")
    msg = str(e.value)
    assert "missing" in msg.lower() and "JobID" in msg and "State" in msg
    assert "sacct -P" in msg   # tells the user how to export correctly


def test_no_warnings_for_a_complete_export():
    text = ("JobID|JobName|User|Partition|State|Submit|Start|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"
            "1|x|u|p|COMPLETED|2026-11-20T09:00:00|2026-11-20T09:01:00|01:00:00|02:00:00|1|01:00:00|4G|1G\n")
    assert a.analyze(text)["warnings"] == []


# ---- TRES fallbacks ---------------------------------------------------------------
def test_memory_request_from_alloctres():
    text = ("JobID|State|Elapsed|AllocCPUS|TotalCPU|AllocTRES|MaxRSS\n"
            "32641375|COMPLETED|01:00:29|1|01:00:29|billing=1,cpu=1,mem=7996M,node=1|\n"
            "32641375.batch|COMPLETED|01:00:32|1|01:00:32|cpu=1,mem=7996M,node=1|276869K\n")
    out = a.analyze(text)
    j = out["jobs"][0]
    assert j["req_mem_mb"] == pytest.approx(7996)
    assert j["memory_efficiency"] == pytest.approx(276869 / 1024 / 7996 * 100)
    assert not any("ReqMem" in w for w in out["warnings"])


def test_reqtres_g_units_and_cpu_count_from_tres():
    text = ("JobID|State|Elapsed|TotalCPU|ReqTRES|MaxRSS\n"
            "1|COMPLETED|01:00:00|02:00:00|billing=4,cpu=4,mem=16G,node=1|\n"
            "1.batch|COMPLETED|01:00:00|02:00:00||4096M\n")
    j = a.analyze(text)["jobs"][0]
    assert j["alloc_cpus"] == 4 and j["cpu_efficiency"] == pytest.approx(50.0)
    assert j["req_mem_mb"] == pytest.approx(16384) and j["memory_efficiency"] == pytest.approx(25.0)


def test_ncpus_fallback():
    text = "JobID|State|Elapsed|NCPUS|TotalCPU\n1|COMPLETED|01:00:00|8|02:00:00\n"
    assert a.analyze(text)["jobs"][0]["cpu_efficiency"] == pytest.approx(25.0)


def test_parse_tres():
    assert a.parse_tres("billing=1,cpu=4,mem=7996M,node=1") == {"billing": "1", "cpu": "4", "mem": "7996M", "node": "1"}
    assert a.parse_tres("cpu=2,gres/gpu=1,mem=1G") == {"cpu": "2", "gres/gpu": "1", "mem": "1G"}
    assert a.parse_tres("") == {} and a.parse_tres(None) == {} and a.parse_tres("garbage") == {}


# ---- output without -P -----------------------------------------------------------
def test_fixed_width_output_gets_a_clear_error():
    text = ("JobID           JobName  Partition    Account  AllocCPUS      State ExitCode\n"
            "------------ ---------- ---------- ---------- ---------- ---------- --------\n"
            "123456             test    compute    proj123          4  COMPLETED      0:0\n")
    with pytest.raises(ValueError) as e:
        a.analyze(text)
    assert "-P" in str(e.value) and "fixed-width" in str(e.value).lower()
