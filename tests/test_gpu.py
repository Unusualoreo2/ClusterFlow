"""GPU jobs (v0.9). Written by the architect; implementation must pass it unchanged.
Slurm records GPUs in AllocTRES (gres/gpu=N or gres/gpu:<type>=N) and, where GPU accounting is enabled,
utilisation in TRESUsageInAve on the job steps (gres/gpuutil=<percent>)."""
import os
import sys

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import analysis as a  # noqa: E402

HDR = "JobID|User|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|AllocTRES|TRESUsageInAve\n"


def gpu_job(jid, gpus="gres/gpu=2", util="gres/gpuutil=35", state="COMPLETED", el="02:00:00", user="ann"):
    return ("%s|%s|%s|%s|04:00:00|8|16:00:00|billing=8,cpu=8,%s,mem=32G,node=1|\n" % (jid, user, state, el, gpus)
            + "%s.batch||%s|%s||8|16:00:00||cpu=00:01:00,%s,mem=1G\n" % (jid, state, el, util)
            + "%s.0||%s|%s||8|16:00:00||cpu=16:00:00,gres/gpuutil=5,mem=20G\n" % (jid, state, el))


@pytest.mark.parametrize("tres,n", [
    ("billing=8,cpu=8,gres/gpu=2,mem=32G,node=1", 2),
    ("cpu=4,gres/gpu:a100=4,mem=16G", 4),
    ("cpu=4,gres/gpu:a100=2,gres/gpu=2,mem=16G", 2),   # typed and untyped both listed: count once
    ("cpu=4,mem=16G", 0),
    ("", 0),
])
def test_count_gpus(tres, n):
    assert a.count_gpus(tres) == n


def test_gpu_fields():
    j = a.analyze(HDR + gpu_job(10))["jobs"][0]
    assert j["alloc_gpus"] == 2
    assert j["gpu_hours"] == pytest.approx(4.0)            # 2 GPUs x 2 h
    assert j["gpu_utilization"] == pytest.approx(35.0)     # highest step value (batch 35, step 0 5)


def test_cpu_only_job_has_no_gpu_fields():
    text = HDR + "11|bob|COMPLETED|01:00:00|02:00:00|4|04:00:00|cpu=4,mem=8G|\n"
    j = a.analyze(text)["jobs"][0]
    assert j["alloc_gpus"] == 0 and j["gpu_hours"] is None and j["gpu_utilization"] is None


def test_gpu_summary():
    text = HDR + gpu_job(10) + gpu_job(11, gpus="gres/gpu:a100=1", util="gres/gpuutil=85", el="01:00:00")
    s = a.analyze(text)["summary"]
    assert s["total_gpu_hours"] == pytest.approx(5.0)       # 4 + 1
    assert s["avg_gpu_utilization"] == pytest.approx(60.0)  # (35 + 85) / 2
    assert s["gpu_job_count"] == 2


def test_no_gpus_in_export():
    s = a.analyze("JobID|State|Elapsed|AllocCPUS|TotalCPU\n1|COMPLETED|01:00:00|1|01:00:00\n")["summary"]
    assert s["total_gpu_hours"] is None and s["avg_gpu_utilization"] is None and s["gpu_job_count"] == 0


def test_low_gpu_utilization_advice():
    r = a.analyze(HDR + gpu_job(10, gpus="gres/gpu=4", util="gres/gpuutil=20"))["jobs"][0]["recommendations"]
    text = " ".join(r)
    assert "GPU utilisation is 20.0% on 4 GPUs" in text
    assert "--gpus=1" in text                               # ceil(4 * 0.20 * 1.2) = 1


def test_single_gpu_low_utilization():
    r = a.analyze(HDR + gpu_job(10, gpus="gres/gpu=1", util="gres/gpuutil=10"))["jobs"][0]["recommendations"]
    text = " ".join(r)
    assert "GPU utilisation is 10.0% on 1 GPU" in text and "check that the job really uses the GPU" in text
    assert "--gpus=" not in text


def test_no_gpu_advice_when_busy_or_not_completed():
    busy = a.analyze(HDR + gpu_job(10, util="gres/gpuutil=90"))["jobs"][0]["recommendations"]
    failed = a.analyze(HDR + gpu_job(10, util="gres/gpuutil=5", state="FAILED"))["jobs"][0]["recommendations"]
    assert not any("GPU" in r for r in busy + failed)


def test_gpu_allocation_without_utilisation_data():
    text = ("JobID|State|Elapsed|AllocCPUS|TotalCPU|AllocTRES\n"
            "1|COMPLETED|02:00:00|8|16:00:00|cpu=8,gres/gpu=2,mem=32G\n")
    out = a.analyze(text)
    j = out["jobs"][0]
    assert j["gpu_hours"] == pytest.approx(4.0) and j["gpu_utilization"] is None
    assert any("TRESUsageInAve" in w and "GPU utilisation" in w for w in out["warnings"])
    assert not any("GPU" in r for r in j["recommendations"])


def test_no_gpu_warning_when_export_has_no_gpu_jobs():
    text = "JobID|State|Elapsed|AllocCPUS|TotalCPU|AllocTRES\n1|COMPLETED|01:00:00|1|01:00:00|cpu=1,mem=1G\n"
    assert not any("GPU" in w for w in a.analyze(text)["warnings"])


def test_gpu_per_user_group():
    text = HDR + gpu_job(10, user="ann") + gpu_job(11, user="bob", gpus="gres/gpu=1", el="01:00:00")
    by_user = {g["name"]: g for g in a.analyze(text)["summary"]["by_user"]}
    assert by_user["ann"]["gpu_hours"] == pytest.approx(4.0) and by_user["bob"]["gpu_hours"] == pytest.approx(1.0)
