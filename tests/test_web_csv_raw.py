"""Web page: "Download CSV" carries the raw figures too (v0.30). Written by the architect; implementation must pass it unchanged.
After the existing 8 columns the page's CSV adds, in this order:
  CPUs, Memory requested (MB), Memory used (MB), Elapsed (s), Time limit (s), Queue wait (s), GPUs, GPU-hours
from the job fields alloc_cpus, req_mem_mb, max_rss_mb, elapsed_s, timelimit_s, wait_s, alloc_gpus, gpu_hours
(same figures as the CLI's --csv). Whole numbers are rounded; GPU-hours has one decimal; a missing value is an empty cell.
The test runs the page's own csvCell function and CSV-building code in Node with a made-up result."""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
HEADER = ['Job ID', 'Name', 'State', 'CPU %', 'Memory %', 'Time used %', 'Wasted core-h.', 'Recommendations',
          'CPUs', 'Memory requested (MB)', 'Memory used (MB)', 'Elapsed (s)', 'Time limit (s)', 'Queue wait (s)',
          'GPUs', 'GPU-hours']


def page():
    with open(os.path.join(ROOT, "frontend", "index.html"), encoding="utf-8") as f:
        return f.read()


def build_csv(jobs):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js not installed")
    html = page()
    cell = re.search(r"function csvCell\(v\) \{.*?\n        \}", html, re.S)
    body = re.search(r"downloadBtn\.onclick = function \(\) \{\s*(.*?const csvContent =.*?join\('\\r\\n'\);)", html, re.S)
    assert cell and body, "csvCell or the Download CSV code could not be found"
    script = cell.group(0) + "\nconst data = " + json.dumps({"jobs": jobs}) + ";\n" + body.group(1) + \
        "\nprocess.stdout.write(csvContent);"
    out = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return [[c[1:-1].replace('""', '"') for c in re.findall(r'"(?:[^"]|"")*"', line)]
            for line in out.stdout.splitlines()]


def job(**kw):
    j = {"job_id": "101", "name": "train", "state": "COMPLETED", "cpu_efficiency": 50.4, "memory_efficiency": 20.0,
         "time_used": 33.3, "wasted_core_hours": 12.34, "recommendations": ["Ask for 2 CPUs"],
         "alloc_cpus": 4, "req_mem_mb": 8192.0, "max_rss_mb": 1638.4, "elapsed_s": 3600.4, "timelimit_s": 10800,
         "wait_s": 125.6, "alloc_gpus": 1, "gpu_hours": 1.04}
    j.update(kw)
    return j


def test_header_has_raw_columns_in_order():
    assert build_csv([job()])[0] == HEADER


def test_raw_values():
    row = build_csv([job()])[1]
    assert row[:8] == ["101", "train", "COMPLETED", "50", "20", "33", "12.3", "Ask for 2 CPUs"]
    assert row[8:] == ["4", "8192", "1638", "3600", "10800", "126", "1", "1.0"]


def test_missing_values_are_empty():
    row = build_csv([job(req_mem_mb=None, max_rss_mb=None, wait_s=None, alloc_gpus=None, gpu_hours=None,
                         timelimit_s=None)])[1]
    assert row[8:] == ["4", "", "", "3600", "", "", "", ""]
    absent = job()
    for k in ("alloc_gpus", "gpu_hours", "wait_s"):
        del absent[k]
    assert build_csv([absent])[1][13:] == ["", "", ""]


def test_zero_is_kept():
    row = build_csv([job(alloc_gpus=0, gpu_hours=0, wait_s=0)])[1]
    assert row[13:] == ["0", "0", "0.0"]


def test_formula_guard_still_applies():
    assert build_csv([job(name="=cmd()")])[1][1] == "'=cmd()"
