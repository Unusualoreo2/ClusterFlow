"""Recommendation rules refined in v0.6 after the simulated pilot run. Written by the architect."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import analysis as a  # noqa: E402


def job(**kw):
    base = {"JobID": "1", "JobName": "x", "State": "COMPLETED", "Elapsed": "01:00:00",
            "Timelimit": "02:00:00", "AllocCPUS": "4", "TotalCPU": "04:00:00",
            "ReqMem": "8G", "MaxRSS": "6000M"}
    base.update(kw)
    return a.analyze_job(base)


def mem_advice(r):
    return [s for s in r["recommendations"] if s.startswith("Memory efficiency")]


def test_no_memory_advice_when_saving_is_under_1gb():
    # 1G requested, 12M used: suggestion would be 15M, saving < 1 GB -> no advice
    assert mem_advice(job(ReqMem="1G", MaxRSS="12M")) == []
    # 2G requested, 300M used: suggestion 375M, saving 1673M >= 1024M -> advice
    assert mem_advice(job(ReqMem="2G", MaxRSS="300M"))


def test_memory_efficiency_still_reported_without_advice():
    r = job(ReqMem="1G", MaxRSS="12M")
    assert r["memory_efficiency"] is not None and r["memory_efficiency"] < 2


def test_reduction_advice_only_for_completed_jobs():
    for state in ("FAILED", "CANCELLED by 123", "NODE_FAIL", "OUT_OF_MEMORY", "TIMEOUT"):
        r = job(State=state, AllocCPUS="16", TotalCPU="01:00:00", ReqMem="64G", MaxRSS="1000M", Timelimit="48:00:00")
        text = " ".join(r["recommendations"])
        assert "--cpus-per-task" not in text, state
        assert "Memory efficiency" not in text, state
        assert "--time=" not in text, state


def test_oom_and_timeout_keep_their_own_advice():
    oom = job(State="OUT_OF_MEMORY", ReqMem="1G", MaxRSS="1024M", Elapsed="00:00:03", Timelimit="00:15:00")
    assert len(oom["recommendations"]) == 1 and "out of memory" in oom["recommendations"][0]
    to = job(State="TIMEOUT", Elapsed="00:02:30", Timelimit="00:02:00", ReqMem="1G", MaxRSS="11M")
    assert len(to["recommendations"]) == 1 and "time limit" in to["recommendations"][0]


def test_completed_jobs_unchanged():
    r = job(AllocCPUS="16", TotalCPU="04:00:00", ReqMem="32G", MaxRSS="4000M", Timelimit="10:00:00")
    text = " ".join(r["recommendations"])
    assert "--cpus-per-task=5" in text and "--mem=5000M" in text and "--time=01:30:00" in text
