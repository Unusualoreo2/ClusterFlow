"""Requeued jobs (v0.32). Written by the architect; implementation must pass it unchanged.
With sacct --duplicates (or joined exports) a requeued job's JobID appears again: a new parent row followed by its own steps.
merge_steps keeps only the LAST attempt: when a parent row (no ".") arrives for a JobID that already has a parent row,
the steps collected so far are dropped and the new attempt starts. Steps of an earlier attempt must never change the
verdict of the last one (MaxRSS, OUT_OF_MEMORY promotion, GPU use). Steps listed before any parent row still belong
to the first attempt (as before).
Each merged job gets "_attempts" (1 if listed once); analyze_job returns it as "attempts".
The summary gains "requeued_count" (jobs with attempts > 1, among analysed jobs); when > 0 the warnings include one line
starting "N job(s) was/were requeued", e.g.
"1 job was requeued (listed more than once): only its last attempt is analysed."
"2 jobs were requeued (listed more than once): only their last attempt is analysed."
A job id listed once (the common case) behaves exactly as before."""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402

HEAD = "JobID|JobName|User|Partition|State|AllocCPUS|Elapsed|Timelimit|TotalCPU|ReqMem|MaxRSS|Submit|Start|End\n"


def row(jid, state, rss="", total="00:10:00", cpus=4):
    return "%s|job|u1|p|%s|%d|01:00:00|10:00:00|%s|4G|%s|2026-01-01T00:00:00|2026-01-01T00:00:00|2026-01-01T01:00:00\n" % (
        jid, state, cpus, total, rss)


def run(*rows):
    return analysis.analyze(HEAD + "".join(rows))


def by_id(result):
    return {j["job_id"]: j for j in result["jobs"]}


def test_only_last_attempt_is_analysed():
    r = run(row("13", "PREEMPTED"), row("13.batch", "CANCELLED", rss="3900M"),
            row("13", "COMPLETED"), row("13.batch", "COMPLETED", rss="1000M"))
    assert len(r["jobs"]) == 1
    j = r["jobs"][0]
    assert j["state"] == "COMPLETED"
    assert abs(j["max_rss_mb"] - 1000) < 1e-6
    assert j["attempts"] == 2


def test_earlier_oom_step_does_not_leak():
    r = run(row("20", "FAILED"), row("20.0", "OUT_OF_MEMORY", rss="4000M"),
            row("20", "FAILED"), row("20.0", "FAILED", rss="2000M"))
    j = r["jobs"][0]
    assert j["state"] == "FAILED"   # the last attempt failed for another reason: not out of memory
    assert not any("ran out of memory" in rec for rec in j["recommendations"])


def test_three_attempts_and_arrays():
    r = run(row("30", "NODE_FAIL"), row("30", "PREEMPTED"), row("30", "COMPLETED"), row("30.batch", "COMPLETED", rss="500M"),
            row("40_1", "PREEMPTED"), row("40_1.batch", "CANCELLED", rss="3000M"),
            row("40_1", "COMPLETED"), row("40_1.batch", "COMPLETED", rss="100M"), row("40_2", "COMPLETED"))
    jobs = by_id(r)
    assert jobs["30"]["attempts"] == 3 and jobs["30"]["state"] == "COMPLETED"
    assert abs(jobs["40_1"]["max_rss_mb"] - 100) < 1e-6 and jobs["40_1"]["attempts"] == 2
    assert jobs["40_2"]["attempts"] == 1


def test_steps_before_parent_still_merge():
    r = run(row("50.batch", "COMPLETED", rss="1500M"), row("50", "COMPLETED"))
    j = r["jobs"][0]
    assert abs(j["max_rss_mb"] - 1500) < 1e-6 and j["attempts"] == 1


def test_summary_count_and_warning():
    r = run(row("13", "PREEMPTED"), row("13", "COMPLETED"), row("14", "COMPLETED"))
    assert r["summary"]["requeued_count"] == 1
    lines = [w for w in r["warnings"] if "requeued" in w]
    assert lines == ["1 job was requeued (listed more than once): only its last attempt is analysed."]
    r2 = run(row("13", "PREEMPTED"), row("13", "COMPLETED"), row("14", "NODE_FAIL"), row("14", "COMPLETED"))
    assert [w for w in r2["warnings"] if "requeued" in w] == [
        "2 jobs were requeued (listed more than once): only their last attempt is analysed."]


def test_no_duplicates_no_warning():
    r = run(row("13", "COMPLETED"), row("13.batch", "COMPLETED", rss="1000M"), row("14", "COMPLETED"))
    assert r["summary"]["requeued_count"] == 0
    assert not [w for w in r["warnings"] if "requeued" in w]
    assert all(j["attempts"] == 1 for j in r["jobs"])


def test_typical_job_advice_counts_jobs_not_attempts():
    # Same name, 3 distinct jobs, one requeued twice: profile sees 3 runs, not 5
    rows = [row("60", "PREEMPTED"), row("60", "PREEMPTED"), row("60", "COMPLETED"), row("61", "COMPLETED"),
            row("62", "COMPLETED")]
    r = run(*rows)
    profiles = r["summary"]["profiles"]
    assert len(profiles) == 1 and profiles[0]["runs"] == 3


def test_by_user_counts_once():
    text = HEAD + row("13", "PREEMPTED") + row("13", "COMPLETED")
    per_user = analysis.analyze_by_user(text)
    assert per_user["u1"]["summary"]["job_count"] == 1
    assert per_user["u1"]["summary"]["requeued_count"] == 1
