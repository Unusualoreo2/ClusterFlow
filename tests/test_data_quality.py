"""Accounting artefacts (v0.13), found in the real IN2P3 data: very short jobs can report more CPU time than
they were allocated (e.g. 37 s of CPU in 21 s on 1 CPU). Written by the architect."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import analysis as a  # noqa: E402

HDR = "JobID|State|Elapsed|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"


def test_impossible_cpu_efficiency_is_ignored():
    out = a.analyze(HDR + "1|CANCELLED|00:21|1|00:37|12000M|569M\n" + "2|COMPLETED|01:00:00|2|01:00:00|4G|1G\n")
    j1, j2 = out["jobs"]
    assert j1["cpu_efficiency"] is None
    assert j2["cpu_efficiency"] == pytest.approx(50.0)
    assert out["summary"]["avg_cpu_efficiency"] == pytest.approx(50.0)
    assert any("1 job reported more CPU time than it was allocated" in w for w in out["warnings"])


def test_slightly_over_100_is_kept():
    j = a.analyze(HDR + "1|COMPLETED|01:00:00|1|01:10:00|4G|1G\n")["jobs"][0]
    assert j["cpu_efficiency"] == pytest.approx(116.7, abs=0.1)
    assert not any("more CPU time" in w for w in a.analyze(HDR + "1|COMPLETED|01:00:00|1|01:10:00|4G|1G\n")["warnings"])


def test_memory_over_request_is_kept():
    j = a.analyze(HDR + "1|OUT_OF_MEMORY|00:45|1|00:35|8M|28M\n")["jobs"][0]
    assert j["memory_efficiency"] == pytest.approx(350.0)


def test_plural_warning():
    rows = "1|CANCELLED|00:21|1|00:37|1G|1M\n2|CANCELLED|00:20|1|00:39|1G|1M\n"
    assert any("2 jobs reported more CPU time" in w for w in a.analyze(HDR + rows)["warnings"])
