"""Acceptance tests for v0.29: --csv carries the raw figures behind each verdict, for admins working in spreadsheets.
Written by the architect; implementation must pass them unchanged."""
import csv
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
BACKEND = os.path.join(ROOT, "backend")
CLI = os.path.join(BACKEND, "clusterflow_cli.py")
EXAMPLE = os.path.join(ROOT, "data", "example_sacct.txt")
sys.path.insert(0, BACKEND)

OLD_COLUMNS = ["job_id", "name", "state", "user", "partition", "cpu_efficiency",
               "memory_efficiency", "time_used", "wasted_core_hours", "recommendations"]
RAW_COLUMNS = ["alloc_cpus", "mem_requested_mb", "mem_used_mb", "elapsed_s", "time_limit_s",
               "queue_wait_s", "alloc_gpus", "gpu_hours"]


def run(*args):
    e = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, CLI, *args], capture_output=True, text=True,
                          encoding="utf-8", env=e, timeout=60)


def rows_for(tmp_path, src=EXAMPLE, extra=()):
    out = tmp_path / "report.csv"
    r = run(src, "--csv", str(out), *extra)
    assert r.returncode == 0, r.stderr
    with open(out, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    return [dict(zip(rows[0], row)) for row in rows[1:]], rows[0]


def test_header_keeps_old_columns_first_then_raw(tmp_path):
    _, header = rows_for(tmp_path)
    assert header == OLD_COLUMNS + RAW_COLUMNS


def test_raw_figures_for_known_job(tmp_path):
    rows, _ = rows_for(tmp_path)
    j = next(r for r in rows if r["job_id"] == "4471201")
    assert j["alloc_cpus"] == "32"
    assert j["mem_requested_mb"] == "65536"
    assert j["mem_used_mb"] == "11240"
    assert j["elapsed_s"] == "11564"
    assert j["time_limit_s"] == "43200"
    assert j["queue_wait_s"] == "340"
    assert j["alloc_gpus"] == "0"
    assert j["gpu_hours"] == ""          # no GPUs -> empty, not "None"


def test_every_row_has_every_column(tmp_path):
    rows, header = rows_for(tmp_path)
    assert len(rows) == 5
    for r in rows:
        assert len(r) == len(header)
        assert "None" not in r.values()


def test_missing_values_are_empty(tmp_path):
    src = tmp_path / "partial.txt"
    src.write_text("JobID|JobName|State|Elapsed|AllocCPUS|TotalCPU\n"
                   "900|short|COMPLETED|01:00:00|4|02:00:00\n", encoding="utf-8")
    rows, _ = rows_for(tmp_path, str(src))
    r = rows[0]
    assert r["alloc_cpus"] == "4" and r["elapsed_s"] == "3600"
    for col in ("mem_requested_mb", "mem_used_mb", "time_limit_s", "queue_wait_s"):
        assert r[col] == "", col


def test_gpu_hours_written(tmp_path):
    src = tmp_path / "gpu.txt"
    src.write_text("JobID|JobName|State|Elapsed|AllocCPUS|TotalCPU|AllocTRES\n"
                   "901|train|COMPLETED|02:00:00|8|10:00:00|cpu=8,gres/gpu=2\n", encoding="utf-8")
    rows, _ = rows_for(tmp_path, str(src))
    assert rows[0]["alloc_gpus"] == "2"
    assert rows[0]["gpu_hours"] == "4.0"


def test_formula_like_text_is_neutralised(tmp_path):
    """A job name like =HYPERLINK(...) must not run as a formula when the CSV is opened in a spreadsheet."""
    src = tmp_path / "evil.txt"
    src.write_text("JobID|JobName|User|Partition|State|Elapsed|AllocCPUS|TotalCPU\n"
                   "902|=HYPERLINK(\"http://x\")|+bob|@gpu|COMPLETED|01:00:00|4|02:00:00\n"
                   "903|-calc|alice|compute|COMPLETED|01:00:00|4|02:00:00\n", encoding="utf-8")
    rows, _ = rows_for(tmp_path, str(src))
    by_id = {r["job_id"]: r for r in rows}
    assert by_id["902"]["name"] == "'=HYPERLINK(\"http://x\")"
    assert by_id["902"]["user"] == "'+bob"
    assert by_id["902"]["partition"] == "'@gpu"
    assert by_id["903"]["name"] == "'-calc"
    assert by_id["903"]["user"] == "alice"       # ordinary text untouched


def test_anonymise_still_applies_to_csv(tmp_path):
    rows, _ = rows_for(tmp_path, extra=("--anonymise",))
    assert all(r["user"] != "amurphy" for r in rows)
