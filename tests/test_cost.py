"""Cost of waste (v0.11). Written by the architect; implementation must pass it unchanged.
HPCFlow never invents prices: the user supplies their centre's rates."""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import analysis as a  # noqa: E402
from test_gpu import HDR as GPU_HDR, gpu_job  # noqa: E402

CLI = os.path.join(ROOT, "backend", "hpcflow_cli.py")
EXAMPLE = os.path.join(ROOT, "data", "example_sacct.txt")


def run(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, CLI, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env, timeout=60)


# ---- engine: idle GPU-hours -----------------------------------------------------
def test_idle_gpu_hours():
    # 4 GPUs x 2 h at 20% busy -> 6.4 idle; 1 GPU x 1 h at 85% -> 0.15 idle
    text = GPU_HDR + gpu_job(10, gpus="gres/gpu=4", util="gres/gpuutil=20") \
        + gpu_job(11, gpus="gres/gpu=1", util="gres/gpuutil=85", el="01:00:00")
    s = a.analyze(text)["summary"]
    assert s["idle_gpu_hours"] == pytest.approx(6.4 + 0.15)


def test_idle_gpu_hours_unknown_without_utilisation():
    text = "JobID|State|Elapsed|AllocCPUS|TotalCPU|AllocTRES\n1|COMPLETED|02:00:00|8|16:00:00|cpu=8,gres/gpu=2\n"
    assert a.analyze(text)["summary"]["idle_gpu_hours"] is None


# ---- CLI ----------------------------------------------------------------------------
def test_cli_prices_wasted_cpu_time():
    out = run(EXAMPLE, "--cpu-hour-cost", "0.02", "--currency", "£").stdout
    # 83.8 wasted core-hours x £0.02
    assert "Cost of wasted CPU time:  £1.68 (at £0.02 per core-hour)" in out


def test_cli_prices_idle_gpu_time(tmp_path):
    f = tmp_path / "g.txt"
    f.write_text(GPU_HDR + gpu_job(10, gpus="gres/gpu=4", util="gres/gpuutil=20"), encoding="utf-8")
    out = run(str(f), "--gpu-hour-cost", "1.50", "--currency", "$").stdout
    assert "Cost of idle GPU time:    $9.60 (at $1.50 per GPU-hour)" in out   # 6.4 idle GPU-h x 1.50


def test_cli_no_cost_lines_without_rates():
    assert "Cost of" not in run(EXAMPLE).stdout


def test_cli_rejects_negative_rate():
    r = run(EXAMPLE, "--cpu-hour-cost", "-1")
    assert r.returncode == 2 and "cost" in r.stderr.lower()


def test_json_includes_cost_when_rates_given():
    data = json.loads(run(EXAMPLE, "--json", "--cpu-hour-cost", "0.02").stdout)
    assert data["cost"]["wasted_cpu_cost"] == pytest.approx(data["summary"]["total_wasted_core_hours"] * 0.02)
    assert data["cost"]["currency"] == "£"   # default currency symbol


def test_estimate_cost_function():
    import hpcflow_cli
    summary = {"total_wasted_core_hours": 100.0, "idle_gpu_hours": None}
    c = hpcflow_cli.estimate_cost(summary, cpu_rate=0.03, gpu_rate=2.0, currency="€")
    assert c["wasted_cpu_cost"] == pytest.approx(3.0) and c["idle_gpu_cost"] is None and c["currency"] == "€"
    assert hpcflow_cli.estimate_cost(summary, None, None) is None
