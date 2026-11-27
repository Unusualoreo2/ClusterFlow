"""Jobs the system ended are not the user's waste (v0.31). Written by the architect; implementation must pass it unchanged.
States PREEMPTED, NODE_FAIL and BOOT_FAIL (analysis.SYSTEM_END_STATES) mean the cluster, not the researcher, ended the job.
For such a job analyze_job:
  - still reports the measured cpu/memory efficiency and time used (they are facts);
  - sets "system_ended": True (False for every other job);
  - sets wasted_core_hours to 0.0 when it could be computed (None stays None);
  - gives no recommendations.
The summary gains "system_ended_count"; when it is > 0 the warnings include one line starting
"N job(s) ended by the system" (e.g. "2 jobs ended by the system (preempted, node failure or boot failure): not counted as waste.").
Idle GPU-hours leave system-ended jobs out. "What to fix first" therefore never lists them."""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402

HEAD = "JobID|JobName|User|Partition|State|AllocCPUS|Elapsed|Timelimit|TotalCPU|ReqMem|MaxRSS|Submit|Start|End\n"


def row(jid, state, cpus=4, elapsed="01:00:00", total="00:10:00", req="4G", rss="3900M"):
    return "%s|j%s|u1|p|%s|%d|%s|10:00:00|%s|%s|%s|2026-01-01T00:00:00|2026-01-01T00:00:00|2026-01-01T01:00:00\n" % (
        jid, jid, state, cpus, elapsed, total, req, rss)


def run(*rows):
    return analysis.analyze(HEAD + "".join(rows))


def by_id(result):
    return {j["job_id"]: j for j in result["jobs"]}


def test_states_constant():
    assert set(analysis.SYSTEM_END_STATES) == {"PREEMPTED", "NODE_FAIL", "BOOT_FAIL"}


def test_system_ended_jobs_are_not_waste():
    r = run(row(1, "PREEMPTED"), row(2, "NODE_FAIL"), row(3, "COMPLETED"))
    jobs = by_id(r)
    for jid in ("1", "2"):
        j = jobs[jid]
        assert j["system_ended"] is True
        assert j["wasted_core_hours"] == 0.0
        assert j["recommendations"] == []
        assert abs(j["cpu_efficiency"] - 100 * 600 / (3600 * 4)) < 1e-6   # facts are still reported
        assert j["memory_efficiency"] is not None
    assert jobs["3"]["system_ended"] is False
    assert jobs["3"]["wasted_core_hours"] > 3
    assert jobs["3"]["recommendations"]
    assert abs(r["summary"]["total_wasted_core_hours"] - jobs["3"]["wasted_core_hours"]) < 1e-9


def test_suffix_states_count():
    r = run(row(1, "PREEMPTED by 0"), row(2, "NODE_FAIL"))
    assert all(j["system_ended"] for j in r["jobs"])


def test_unknown_waste_stays_unknown():
    r = run(row(1, "BOOT_FAIL", total=""))
    j = r["jobs"][0]
    assert j["system_ended"] is True and j["wasted_core_hours"] is None


def test_summary_count_and_warning():
    r = run(row(1, "PREEMPTED"), row(2, "NODE_FAIL"), row(3, "COMPLETED"))
    assert r["summary"]["system_ended_count"] == 2
    lines = [w for w in r["warnings"] if "ended by the system" in w]
    assert len(lines) == 1 and lines[0].startswith("2 jobs ended by the system")
    r1 = run(row(1, "PREEMPTED"), row(3, "COMPLETED"))
    assert [w for w in r1["warnings"] if "ended by the system" in w][0].startswith("1 job ended by the system")


def test_no_warning_when_none():
    r = run(row(3, "COMPLETED"), row(4, "FAILED"), row(5, "CANCELLED by 1001"))
    assert r["summary"]["system_ended_count"] == 0
    assert not [w for w in r["warnings"] if "ended by the system" in w]
    assert not any(j["system_ended"] for j in r["jobs"])


def test_group_and_fix_first_ignore_system_ended():
    r = run(row(1, "PREEMPTED", cpus=16), row(2, "COMPLETED"))
    user = r["summary"]["by_user"][0]
    assert abs(user["wasted_core_hours"] - by_id(r)["2"]["wasted_core_hours"]) < 1e-9
    lines = clusterflow_cli.fix_first(r["jobs"])
    assert lines and lines[0].strip().startswith("1 job:")


def test_idle_gpu_hours_leave_out_system_ended():
    head = HEAD.strip() + "|AllocTRES|TRESUsageInAve\n"
    tail = "|cpu=4,gres/gpu=2,mem=4G|gres/gpuutil=10\n"
    r = analysis.analyze(head + row(1, "PREEMPTED").rstrip("\n") + tail + row(2, "COMPLETED").rstrip("\n") + tail)
    jobs = by_id(r)
    expected = jobs["2"]["gpu_hours"] * 0.9
    assert abs(r["summary"]["idle_gpu_hours"] - expected) < 1e-9


def test_reports_show_line():
    r = run(row(1, "NODE_FAIL"), row(2, "COMPLETED"))
    assert "1 job ended by the system" in clusterflow_cli.report(r, 10)
    assert "1 job ended by the system" in clusterflow_cli.html_report(r, 10)
