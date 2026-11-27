"""Job outcomes and failed exit codes (v0.36). Written by the architect; implementation must pass it unchanged.
Support staff triage failures first, so the report says how jobs ended.
analyze_job returns "exit_code": the number before ":" in the ExitCode column ("1:0" -> 1), None if missing/unparseable.
analysis.summarize_outcomes(jobs) returns (outcomes, top_exit_codes):
  outcomes: dict with keys completed, failed, cancelled, out_of_memory, timeout, system, other (counts; state's first
  word decides: COMPLETED, FAILED, CANCELLED (incl. "CANCELLED BY 12"), OUT_OF_MEMORY, TIMEOUT, system_ended -> system,
  anything else -> other);
  top_exit_codes: up to 3 [code, count] pairs for FAILED jobs with a non-zero exit code, most common first, ties by code.
The summary gains "outcomes" and "top_exit_codes". The text report adds, just before the "Usable figures:" line,
"Job outcomes:          6 completed, 3 failed, 1 cancelled, 1 out of memory, 1 timed out, 1 ended by system"
(only non-zero parts, in that order; "N other" last) when any job did not complete, and when top_exit_codes is not empty
"Failed exit codes:     1 (2 jobs), 2 (1 job)".
The export command asks for ...,State,ExitCode,Submit,... everywhere."""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402

HEAD = "JobID|JobName|User|Partition|State|ExitCode|AllocCPUS|Elapsed|Timelimit|TotalCPU|ReqMem|MaxRSS\n"


def row(jid, state, code="0:0"):
    return "%s|j|u1|p|%s|%s|1|01:00:00|02:00:00|00:50:00|1G|500M\n" % (jid, state, code)


SAMPLE = [row(1, "COMPLETED"), row(2, "COMPLETED"), row(3, "COMPLETED"), row(4, "COMPLETED"), row(5, "COMPLETED"),
          row(6, "COMPLETED"), row(7, "FAILED", "1:0"), row(8, "FAILED", "1:0"), row(9, "FAILED", "2:0"),
          row(10, "CANCELLED by 1001", "0:15"), row(11, "OUT_OF_MEMORY", "0:125"), row(12, "TIMEOUT", "0:0"),
          row(13, "NODE_FAIL", "0:0")]


def run(rows):
    return analysis.analyze(HEAD + "".join(rows))


def test_exit_code_parsed():
    r = run([row(1, "FAILED", "137:0"), row(2, "FAILED", ""), row(3, "FAILED", "x:y")])
    assert [j["exit_code"] for j in r["jobs"]] == [137, None, None]


def test_outcomes_and_codes():
    r = run(SAMPLE)
    assert r["summary"]["outcomes"] == {"completed": 6, "failed": 3, "cancelled": 1, "out_of_memory": 1,
                                        "timeout": 1, "system": 1, "other": 0}
    assert r["summary"]["top_exit_codes"] == [[1, 2], [2, 1]]
    assert analysis.summarize_outcomes(r["jobs"]) == (r["summary"]["outcomes"], r["summary"]["top_exit_codes"])


def test_top_three_and_ties():
    rows = [row(i, "FAILED", "%d:0" % c) for i, c in enumerate([5, 5, 3, 3, 9, 9, 7, 0], start=1)]
    assert run(rows)["summary"]["top_exit_codes"] == [[3, 2], [5, 2], [9, 2]]


def test_other_state():
    r = run([row(1, "DEADLINE"), row(2, "COMPLETED")])
    assert r["summary"]["outcomes"]["other"] == 1


def test_report_lines():
    out = clusterflow_cli.report(run(SAMPLE), 5).splitlines()
    i = out.index("Job outcomes:          6 completed, 3 failed, 1 cancelled, 1 out of memory, 1 timed out, "
                  "1 ended by system")
    assert out[i + 1] == "Failed exit codes:     1 (2 jobs), 2 (1 job)"
    assert out[i + 2].startswith("Usable figures:")


def test_no_lines_when_all_completed():
    out = clusterflow_cli.report(run([row(1, "COMPLETED"), row(2, "COMPLETED")]), 5)
    assert "Job outcomes:" not in out and "Failed exit codes:" not in out


def test_other_listed_last_and_no_codes_line():
    out = clusterflow_cli.report(run([row(1, "DEADLINE"), row(2, "FAILED", "0:9")]), 5)
    assert "Job outcomes:          1 failed, 1 other" in out
    assert "Failed exit codes:" not in out


def test_export_asks_for_exit_code():
    assert ",State,ExitCode,Submit," in analysis.EXPORT_COMMAND
    assert ",State,ExitCode,Submit," in " ".join(clusterflow_cli.sacct_command(7))
    for rel in ("README.md", "docs/user-guide.md", "docs/architecture.md", "docs/CLUSTERFLOW-FOR-AI.md",
                "frontend/index.html"):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            text = f.read()
        assert ",State,Submit," not in text, rel
