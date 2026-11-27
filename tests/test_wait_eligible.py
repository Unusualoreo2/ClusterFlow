"""Queue wait from Eligible (v0.33). Written by the architect; implementation must pass it unchanged.
Submit-to-Start includes time a job was held or waiting on a dependency, which is not the scheduler's doing.
analyze_job measures the wait from Eligible when it is a valid timestamp not later than Start; otherwise from Submit
(as before). Each job gets "wait_from": "Eligible", "Submit" or None (no wait known).
The summary gains "wait_from": "Eligible" if any analysed job's wait came from Eligible, else "Submit" if any wait is
known, else None. The text report (and so the HTML report) adds, right after "Max queue wait:", the line
"Queue wait from:      eligible time (holds and dependencies not counted)"  or
"Queue wait from:      submit time (export Eligible to leave out holds and dependencies)".
The export command (analysis.EXPORT_COMMAND, the CLI's sacct_command, README, docs and the web page) asks for
...,State,Submit,Eligible,Start,... and "Eligible" is a known column."""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402

HEAD = "JobID|JobName|User|Partition|State|AllocCPUS|Elapsed|Timelimit|TotalCPU|ReqMem|MaxRSS|Submit|Eligible|Start|End\n"
T = "2026-01-01T%s"


def row(jid, submit, eligible, start):
    return "%s|j|u1|p|COMPLETED|1|01:00:00|02:00:00|00:50:00|1G|500M|%s|%s|%s|2026-01-02T00:00:00\n" % (
        jid, submit, eligible, start)


def run(*rows, head=HEAD):
    return analysis.analyze(head + "".join(rows))


def jobs(r):
    return {j["job_id"]: j for j in r["jobs"]}


def test_wait_from_eligible():
    r = run(row(1, T % "00:00:00", T % "02:00:00", T % "02:10:00"))
    j = r["jobs"][0]
    assert j["wait_s"] == 600 and j["wait_from"] == "Eligible"
    assert r["summary"]["wait_from"] == "Eligible"


def test_falls_back_to_submit():
    r = run(row(1, T % "00:00:00", "Unknown", T % "00:30:00"),
            row(2, T % "00:00:00", "", T % "00:20:00"),
            row(3, T % "00:00:00", T % "05:00:00", T % "01:00:00"))   # Eligible after Start: not trusted
    js = jobs(r)
    assert js["1"]["wait_s"] == 1800 and js["1"]["wait_from"] == "Submit"
    assert js["2"]["wait_s"] == 1200 and js["2"]["wait_from"] == "Submit"
    assert js["3"]["wait_s"] == 3600 and js["3"]["wait_from"] == "Submit"
    assert r["summary"]["wait_from"] == "Submit"


def test_no_eligible_column_is_unchanged():
    head = HEAD.replace("|Eligible", "")
    line = "1|j|u1|p|COMPLETED|1|01:00:00|02:00:00|00:50:00|1G|500M|%s|%s|2026-01-02T00:00:00\n" % (
        T % "00:00:00", T % "00:45:00")
    r = run(line, head=head)
    assert r["jobs"][0]["wait_s"] == 2700 and r["jobs"][0]["wait_from"] == "Submit"


def test_no_wait_known():
    r = run(row(1, "Unknown", "Unknown", "None"))
    assert r["jobs"][0]["wait_s"] is None and r["jobs"][0]["wait_from"] is None
    assert r["summary"]["wait_from"] is None


def test_mixed_reports_eligible():
    r = run(row(1, T % "00:00:00", T % "01:00:00", T % "01:05:00"), row(2, T % "00:00:00", "Unknown", T % "00:10:00"))
    assert r["summary"]["wait_from"] == "Eligible"


def test_report_line():
    out = clusterflow_cli.report(run(row(1, T % "00:00:00", T % "02:00:00", T % "02:10:00")), 5).splitlines()
    i = [k for k, l in enumerate(out) if l.startswith("Max queue wait:")][0]
    assert out[i + 1] == "Queue wait from:      eligible time (holds and dependencies not counted)"
    out = clusterflow_cli.report(run(row(1, T % "00:00:00", "Unknown", T % "00:10:00")), 5)
    assert "Queue wait from:      submit time (export Eligible to leave out holds and dependencies)" in out
    page = clusterflow_cli.html_report(run(row(1, T % "00:00:00", T % "02:00:00", T % "02:10:00")), 5)
    assert "Queue wait from" in page and "eligible time (holds and dependencies not counted)" in page


def test_no_line_without_waits():
    assert "Queue wait from:" not in clusterflow_cli.report(run(row(1, "Unknown", "Unknown", "None")), 5)


def test_export_command_asks_for_eligible():
    assert "Eligible" in analysis.KNOWN_COLUMNS
    assert ",Submit,Eligible,Start," in analysis.EXPORT_COMMAND
    assert ",Submit,Eligible,Start," in " ".join(clusterflow_cli.sacct_command(7))
    for rel in ("README.md", "docs/user-guide.md", "docs/architecture.md", "docs/CLUSTERFLOW-FOR-AI.md",
                "frontend/index.html"):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            text = f.read()
        assert "Submit,Start," not in text, rel
        assert "Submit,Eligible,Start," in text, rel
