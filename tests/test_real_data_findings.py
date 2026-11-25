"""Bugs found by running HPCFlow on real public sacct captures (v0.8). Written by the architect."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import analysis as a  # noqa: E402

# Shape of a real capture: Slurm marks the job FAILED, the step that died is OUT_OF_MEMORY.
OOM_STEP = ("JobID\tExitCode\tState\tMaxRSS\tElapsed\n"
            "7585175\t1:0\tFAILED\t\t00:00:38\n"
            "7585175.batch\t1:0\tFAILED\t7460K\t00:00:38\n"
            "7585175.extern\t0:0\tCOMPLETED\t0\t00:00:38\n"
            "7585175.0\t0:125\tOUT_OF_MEMORY\t2499348K\t00:00:38\n")


def test_out_of_memory_step_marks_the_job():
    j = a.analyze(OOM_STEP)["jobs"][0]
    assert j["state"] == "OUT_OF_MEMORY"
    assert any("out of memory" in r.lower() for r in j["recommendations"])


def test_failed_job_without_oom_step_stays_failed():
    text = OOM_STEP.replace("OUT_OF_MEMORY", "FAILED")
    assert a.analyze(text)["jobs"][0]["state"] == "FAILED"


def test_completed_job_is_not_relabelled_by_an_oom_step():
    """If the job itself COMPLETED, keep that: a step OOM that the job survived is not a job failure."""
    text = OOM_STEP.replace("7585175\t1:0\tFAILED", "7585175\t0:0\tCOMPLETED")
    assert a.analyze(text)["jobs"][0]["state"] == "COMPLETED"


def test_wasted_core_hours_unknown_not_zero_without_cpu_data():
    s = a.analyze("JobID|State|MaxRSS|Elapsed\n1|COMPLETED|1G|01:00:00\n")["summary"]
    assert s["total_wasted_core_hours"] is None


def test_wasted_core_hours_still_summed_when_known():
    s = a.analyze("JobID|State|Elapsed|AllocCPUS|TotalCPU\n1|COMPLETED|01:00:00|4|01:00:00\n")["summary"]
    assert s["total_wasted_core_hours"] == 3.0


def test_cli_prints_dash_for_unknown_waste(tmp_path):
    import subprocess
    f = tmp_path / "x.txt"
    f.write_text("JobID|State|MaxRSS|Elapsed\n1|COMPLETED|1G|01:00:00\n", encoding="utf-8")
    cli = os.path.join(os.path.dirname(__file__), "..", "backend", "hpcflow_cli.py")
    out = subprocess.run([sys.executable, cli, str(f)], stdout=subprocess.PIPE, universal_newlines=True, timeout=60).stdout
    line = [l for l in out.splitlines() if l.startswith("Wasted core-hours")][0]
    assert line.split()[-1] == "-"
