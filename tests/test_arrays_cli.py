"""Job arrays in the CLI report (v0.7). Written by the architect."""
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
CLI = os.path.join(ROOT, "backend", "clusterflow_cli.py")
EXAMPLE = os.path.join(ROOT, "data", "example_sacct.txt")
sys.path.insert(0, os.path.join(ROOT, "tests"))
from test_arrays import HDR, task  # noqa: E402


def run(path, *args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, CLI, str(path), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env, timeout=60).stdout


def test_array_section(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text(HDR + "".join(task(500, i) for i in range(1, 9))
                 + task(500, 9, state="OUT_OF_MEMORY", el="00:01:00", tot="00:01:00", rss="16384M"), encoding="utf-8")
    out = run(f)
    assert "Job arrays (1)" in out
    line = [l for l in out.splitlines() if l.strip().startswith("500 ")][0]
    assert "sweep" in line and "9 tasks" in line and "8 COMPLETED" in line and "1 OUT_OF_MEMORY" in line
    assert "CPU 25%" in line and "WASTED" in line
    assert "1 of 9 tasks ran out of memory" in out and "--mem=2500M for this array" in out
    # the array section comes before the top-jobs list
    assert out.index("Job arrays (1)") < out.index("Top ")


def test_top_limits_arrays(tmp_path):
    f = tmp_path / "b.txt"
    f.write_text(HDR + "".join(task(a, i) for a in (1, 2, 3) for i in (1, 2)), encoding="utf-8")
    out = run(f, "--top", "2")
    assert "Job arrays (3, showing 2)" in out


def test_no_array_section_without_arrays():
    assert "Job arrays" not in run(EXAMPLE)


def test_anonymise_covers_arrays(tmp_path):
    f = tmp_path / "c.txt"
    f.write_text(HDR + task(500, 1) + task(500, 2), encoding="utf-8")
    out = run(f, "--anonymise")
    assert "sweep" not in out and "ann" not in out.replace("Job arrays", "").replace("analysed", "")
    assert "A1" in out
