"""Job-array rollup (v0.7). Written by the architect; implementation must pass it unchanged."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import analysis as a  # noqa: E402

HDR = "JobID|JobName|User|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"


def task(arr, i, state="COMPLETED", el="01:00:00", tl="10:00:00", cpus=4, tot="01:00:00", req="16G", rss="2000M"):
    jid = "%s_%d" % (arr, i)
    return ("%s|sweep|ann|%s|%s|%s|%d|%s|%s|\n" % (jid, state, el, tl, cpus, tot, req)
            + "%s.batch|batch||%s|%s||%d|%s||%s\n" % (jid, state, el, cpus, tot, rss))


def analyze(body):
    return a.analyze(HDR + body)


# ---- new per-job fields ------------------------------------------------------
def test_job_fields_for_arrays_and_memory():
    out = analyze(task(500, 1) + "600|single|bob|COMPLETED|01:00:00|02:00:00|1|01:00:00|4G|\n")
    j1, j2 = out["jobs"]
    assert j1["array_id"] == "500" and j2["array_id"] is None
    assert j1["max_rss_mb"] == pytest.approx(2000) and j1["req_mem_mb"] == pytest.approx(16384)
    assert j2["max_rss_mb"] is None and j2["req_mem_mb"] == pytest.approx(4096)


# ---- rollup ------------------------------------------------------------------
def test_array_summary():
    body = "".join(task(500, i, rss="%dM" % (1000 + 100 * i)) for i in range(1, 11))  # peak 2000M
    arrays = analyze(body)["summary"]["arrays"]
    assert len(arrays) == 1
    r = arrays[0]
    assert r["array_id"] == "500" and r["name"] == "sweep" and r["user"] == "ann"
    assert r["task_count"] == 10 and r["states"] == {"COMPLETED": 10}
    assert r["avg_cpu_efficiency"] == pytest.approx(25.0)
    assert r["peak_memory_mb"] == pytest.approx(2000)
    assert r["wasted_core_hours"] == pytest.approx(30.0)  # 10 tasks x (4 - 1) core-hours


def test_array_recommendations_use_peak_and_average():
    body = "".join(task(500, i, rss="%dM" % (1000 + 100 * i)) for i in range(1, 11))
    recs = " ".join(analyze(body)["summary"]["arrays"][0]["recommendations"])
    assert "--cpus-per-task=2" in recs     # ceil(4 * 0.25 * 1.2) = 2
    assert "--mem=2500M" in recs           # ceil(peak 2000 * 1.25), not based on the average
    assert "--time=01:30:00" in recs       # longest task 1 h of 10 h limit -> 1.5 h
    assert "10 tasks" in recs


def test_array_failures_reported_and_excluded_from_advice():
    body = (task(700, 1) + task(700, 2)
            + task(700, 3, state="OUT_OF_MEMORY", rss="16384M", el="00:01:00", tot="00:01:00")
            + task(700, 4, state="TIMEOUT", el="10:00:30", tot="40:00:00"))
    r = analyze(body)["summary"]["arrays"][0]
    assert r["task_count"] == 4
    assert r["states"] == {"COMPLETED": 2, "OUT_OF_MEMORY": 1, "TIMEOUT": 1}
    recs = " ".join(r["recommendations"])
    assert "1 of 4 tasks ran out of memory" in recs
    assert "1 of 4 tasks hit the time limit" in recs
    assert "--mem=2500M" not in recs and "(e.g. --mem=24576M)" in recs  # v0.24: a task ran out, never lower memory
    assert "--time=" not in recs           # a task hit the limit: never suggest less time


def test_single_jobs_and_one_task_arrays_not_rolled_up():
    body = task(800, 1) + "900|single|bob|COMPLETED|01:00:00|02:00:00|1|01:00:00|4G|\n"
    assert analyze(body)["summary"]["arrays"] == []


def test_arrays_sorted_by_waste_and_pending_ranges_ignored():
    body = (task(1, 1) + task(1, 2)
            + task(2, 1, cpus=16) + task(2, 2, cpus=16)
            + "2_[3-50]|sweep|ann|PENDING|00:00:00|10:00:00|16|00:00:00|16G|\n")
    arrays = analyze(body)["summary"]["arrays"]
    assert [r["array_id"] for r in arrays] == ["2", "1"]
    assert arrays[0]["task_count"] == 2


def test_no_array_advice_when_well_sized():
    body = "".join(task(5, i, cpus=1, tot="01:00:00", req="4G", rss="3500M", tl="01:30:00") for i in range(1, 4))
    assert analyze(body)["summary"]["arrays"][0]["recommendations"] == []
