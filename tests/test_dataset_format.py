"""Published job datasets (v0.12): format of the IN2P3 2024 workload dataset (Zenodo 18668107, CC-BY 4.0):
tab-separated, lowercase states, durations in seconds, Unix timestamps, allocmem/allocgpus columns, NULL.
Rows below are written by the architect in that format (not copied from the dataset)."""
import os
import subprocess
import sys
from datetime import datetime

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis as a  # noqa: E402

HDR = "jobid\tstate\taccount\tuser\tpartition\tsubmit\teligible\tstart\tend\ttimelimit\telapsed\tallocmem\tmaxrss\talloccpus\ttotalcpu\tallocgpus\n"
# 2024-12-01 00:00:00 UTC = 1733011200
ROWS = (
    "1\tcompleted\tacc1\tu1\thtc\t1733011200\t1733011200\t1733011800\t1733015400\t36000\t3600\t10240\t2048\t4\t3600\t0\n"   # 10 min wait, 1 h of 10 h, 4 CPUs 25%, 2 of 10 GB
    "2\tout_of_memory\tacc1\tu1\thtc\t1733011200\t1733011200\t1733011200\t1733011260\t3600\t60\t2000\t2000\t1\t55\t0\n"
    "3\trunning\tacc2\tu2\thtc\t1733011200\t1733011200\t1733011200\tNULL\t3600\t600\t2000\tNULL\t1\t500\t0\n"
    "4\tcompleted\tacc2\tu2\tgpu\t1733011200\t1733011200\t1733011200\t1733018400\t7200\t7200\t32000\t30000\t8\t57600\t2\n"
)


def test_plain_seconds_and_unix_timestamps():
    assert a.parse_duration("21600") == 21600 and a.parse_duration("4.5") == 4.5
    assert a.parse_duration("NULL") is None
    assert a.parse_timestamp("1733011200") == datetime(2024, 12, 1, 0, 0, 0)
    assert a.parse_timestamp("12345") is None          # too short to be a Unix timestamp


def test_dataset_rows_are_analysed():
    out = a.analyze(HDR + ROWS)
    jobs = {j["job_id"]: j for j in out["jobs"]}
    assert out["skipped"] == 1                           # lowercase "running" is skipped
    j1 = jobs["1"]
    assert j1["state"] == "COMPLETED"
    assert j1["cpu_efficiency"] == pytest.approx(25.0)
    assert j1["memory_efficiency"] == pytest.approx(20.0)
    assert j1["time_used"] == pytest.approx(10.0)
    assert j1["wait_s"] == 600
    assert j1["start_date"] == "2024-12-01"
    assert any("--cpus-per-task=2" in r for r in j1["recommendations"])   # ceil(4 x 0.25 x 1.2)
    assert jobs["2"]["state"] == "OUT_OF_MEMORY"
    assert any("out of memory" in r.lower() for r in jobs["2"]["recommendations"])
    assert jobs["4"]["alloc_gpus"] == 2 and jobs["4"]["gpu_hours"] == pytest.approx(4.0)


def test_no_reqmem_warning_when_allocmem_present():
    assert not any("ReqMem" in w for w in a.analyze(HDR + ROWS)["warnings"])


def test_cli_limits_group_tables(tmp_path):
    rows = "".join("%d\tcompleted\tacc\tuser%02d\thtc\t1733011200\t1733011200\t1733011200\t1733014800\t7200\t3600\t2000\t1000\t2\t3600\t0\n"
                   % (i, i) for i in range(30))
    f = tmp_path / "d.tsv"
    f.write_text(HDR + rows, encoding="utf-8")
    cli = os.path.join(ROOT, "backend", "clusterflow_cli.py")
    out = subprocess.run([sys.executable, cli, str(f), "--top", "5"], stdout=subprocess.PIPE,
                         universal_newlines=True, timeout=60).stdout
    assert "By user (30, showing 5)" in out
    lines = out.splitlines()
    i = lines.index("By user (30, showing 5)")
    assert lines[i + 7] == ""                            # title, header, 5 rows, blank line
