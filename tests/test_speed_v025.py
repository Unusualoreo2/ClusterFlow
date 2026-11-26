"""Faster timestamp parsing and trend (v0.25), same results. Written by the architect.
Profiling 400k real jobs: timestamps were parsed with strptime ~3 times per job and summarize_trend parsed every
job's day twice. A fixed-layout fast path must give exactly what strptime gives (or None where strptime fails)."""
import os
import sys
from datetime import datetime

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402


def reference(text):
    text = (text or "").strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except (ValueError, TypeError):
            pass
    return None


CASES = ["2026-11-18T08:05:40", "2026-11-18 08:05:40", "2024-02-29T23:59:59", "2025-02-29T00:00:00",
         "2026-13-01T00:00:00", "2026-11-31T00:00:00", "2026-11-18T24:00:00", "2026-11-18T08:60:00",
         "2026-11-18T08:05:61", "2026-11-18X08:05:40", "2026-11-18T08:05", "2026-11-18T08:05:40.5",
         "Unknown", "None", "", "  2026-11-18T08:05:40  ", "2026-1-18T08:05:40", "2026-+1-18T08:05:40",
         "20a6-11-18T08:05:40", "2026-11-18T 8:05:40", "0000-01-01T00:00:00", "9999-12-31T23:59:59"]


@pytest.mark.parametrize("text", CASES)
def test_same_as_strptime(text):
    assert analysis._parse_timestamp_text(text.strip()) == reference(text)
    if not text.strip().isdigit():
        assert analysis.parse_timestamp(text) == reference(text)


def test_fast_path_skips_strptime(monkeypatch):
    class Boom:
        @staticmethod
        def strptime(*a):
            raise AssertionError("strptime used for a standard timestamp")
    real = analysis.datetime

    class Patched(real):
        strptime = Boom.strptime
    monkeypatch.setattr(analysis, "datetime", Patched)
    assert analysis._parse_timestamp_text("2026-11-18T08:05:40") == real(2026, 11, 18, 8, 5, 40)


def test_trend_unchanged_on_demo():
    trend = analysis.analyze(clusterflow_cli.DEMO_SACCT)["summary"]["trend"]
    assert trend["period"] == "day"
    assert [r["name"] for r in trend["rows"]] == ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"]
    assert [r["job_count"] for r in trend["rows"]] == [4, 4, 17, 4, 3]
