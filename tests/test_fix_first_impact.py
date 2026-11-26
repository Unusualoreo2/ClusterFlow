"""'What to fix first' shows what each item costs (v0.27). Written by the architect; implementation must pass it.
Counts alone hide impact; three categories have a natural unit (summed over the jobs in that line):
  request fewer CPUs                  -> " (N core-hours wasted)"             sum of wasted_core_hours
  request less memory                 -> " (N GB-hours of memory unused)"     sum of (req - MaxRSS) MB / 1024 x elapsed h
  request fewer GPUs or check GPU use -> " (N GPU-hours idle)"                sum of gpu_hours x (1 - utilisation/100)
Numbers use num() (thousands separators, one decimal). Other lines are unchanged."""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402


def test_demo_lines():
    lines = [l.strip() for l in clusterflow_cli.fix_first(analysis.analyze(clusterflow_cli.DEMO_SACCT)["jobs"])]
    cpu = [l for l in lines if "request fewer CPUs" in l][0]
    assert cpu.startswith("20 jobs: request fewer CPUs (") and cpu.endswith(" core-hours wasted)")
    gpu = [l for l in lines if "request fewer GPUs" in l][0]
    assert gpu == "3 jobs: request fewer GPUs or check GPU use (59.0 GPU-hours idle)"      # 3 x 4 GPUs x 6 h x 82%
    assert "2 jobs: hit the time limit" in lines                                            # unchanged


def test_amounts_have_separators():
    jobs = [{"recommendations": ["CPU efficiency is 1.0%: request --cpus-per-task=1 instead of 64, or check..."],
             "wasted_core_hours": 1234.5, "state": "COMPLETED"}]
    assert clusterflow_cli.fix_first(jobs) == ["  1 job: request fewer CPUs (1,234.5 core-hours wasted)"]
