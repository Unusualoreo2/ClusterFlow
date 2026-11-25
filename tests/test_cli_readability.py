"""Readable CLI report for demos (v0.12). Written by the architect; implementation must pass it unchanged."""
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
CLI = os.path.join(ROOT, "backend", "hpcflow_cli.py")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import hpcflow_cli  # noqa: E402


HDR = "JobID|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"


def run(text, tmp_path, *args):
    f = tmp_path / "r.txt"
    f.write_text(text, encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, CLI, str(f), *args], stdout=subprocess.PIPE, universal_newlines=True,
                          encoding="utf-8", env=env, timeout=60).stdout


def test_num_thousands_separators():
    assert hpcflow_cli.num(195693.24) == "195,693.2"
    assert hpcflow_cli.num(83.8) == "83.8"
    assert hpcflow_cli.num(1234567, 0) == "1,234,567"
    assert hpcflow_cli.num(None) == "-"


def test_big_numbers_are_readable(tmp_path):
    rows = "".join("%d|COMPLETED|10:00:00|20:00:00|64|10:00:00|4G|1G\n" % i for i in range(1, 1201))
    out = run(HDR + rows, tmp_path)
    assert "HPCFlow report: 1,200 jobs analysed" in out
    assert "Wasted core-hours:     756,000.0" in out          # 1200 x (64 - 1) x 10 h


def test_fix_first_section(tmp_path):
    rows = ("1|COMPLETED|01:00:00|20:00:00|16|01:00:00|32G|1G\n"      # CPU + memory + time advice
            "2|COMPLETED|01:00:00|20:00:00|16|01:00:00|4G|3G\n"       # CPU + time advice
            "3|OUT_OF_MEMORY|00:01:00|01:00:00|1|00:01:00|1G|1G\n"    # out of memory
            "4|COMPLETED|01:00:00|01:30:00|1|01:00:00|4G|3G\n")       # well sized
    out = run(HDR + rows, tmp_path)
    assert "What to fix first" in out
    lines = out.splitlines()
    i = lines.index("What to fix first")
    section = lines[i + 1:i + 6]
    assert section[0].strip() == "2 jobs: request fewer CPUs"
    assert section[1].strip() == "2 jobs: request a shorter time limit"
    assert "1 job: request less memory" in [s.strip() for s in section]
    assert "1 job: ran out of memory" in [s.strip() for s in section]
    assert out.index("What to fix first") < out.index("Top ")


def test_no_fix_first_when_all_well_sized(tmp_path):
    out = run(HDR + "1|COMPLETED|01:00:00|01:30:00|1|01:00:00|4G|3G\n", tmp_path)
    assert "What to fix first" not in out


def test_unnamed_jobs_show_a_dash(tmp_path):
    out = run(HDR + "1|COMPLETED|01:00:00|20:00:00|16|01:00:00|32G|1G\n", tmp_path)
    top = [l for l in out.splitlines() if l.startswith("  1  ")][0]
    assert top.startswith("  1  -  CPU ")
