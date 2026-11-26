"""Single-core jobs that mostly waited (v0.26). Written by the architect; implementation must pass it unchanged.
CPU advice only covers multi-core jobs, so a 1-core job idle most of the time got no comment. On 93k real 1-core
IN2P3 jobs, 3.3% ran >= 10 min with the CPU busy < 25% (~8,000 idle core-hours). Short jobs are left alone
(start-up overhead dominates).
Rule: COMPLETED, AllocCPUS == 1, CPU efficiency < 25%, elapsed >= 600 s ->
  "CPU was busy only 12.5% of the run: the job mostly waited (file input/output, network or sleep). Worth checking it is not stuck waiting."
"What to fix first" category: "mostly waited instead of computing"."""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402

HDR = "JobID|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"


def recs(state="COMPLETED", el="02:00:00", cpus=1, tot="00:15:00"):
    data = HDR + "1|%s|%s|03:00:00|%d|%s|1G|\n1.batch|%s|%s||%d|%s||800M\n" % (state, el, cpus, tot, state, el, cpus, tot)
    return analysis.analyze(data)["jobs"][0]["recommendations"]


MSG = ("CPU was busy only 12.5% of the run: the job mostly waited (file input/output, network or sleep). "
       "Worth checking it is not stuck waiting.")


def test_flagged():
    assert MSG in recs()


def test_not_for_short_jobs():
    assert not any(r.startswith("CPU was busy only") for r in recs(el="00:09:59", tot="00:01:00"))


def test_not_at_25_percent_or_more():
    assert not any(r.startswith("CPU was busy only") for r in recs(tot="00:30:00"))


def test_not_for_multicore_or_failed():
    assert not any(r.startswith("CPU was busy only") for r in recs(cpus=4, tot="01:00:00"))
    assert not any(r.startswith("CPU was busy only") for r in recs(state="FAILED"))


def test_fix_first_category():
    data = HDR + "1|COMPLETED|02:00:00|03:00:00|1|00:15:00|1G|\n1.batch|COMPLETED|02:00:00||1|00:15:00||800M\n"
    assert "  1 job: mostly waited instead of computing" in clusterflow_cli.fix_first(analysis.analyze(data)["jobs"])
