"""Robustness: analyze() must never crash on malformed input. It may only return a result or raise ValueError."""
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import analysis as a  # noqa: E402

COLS = ["JobID", "JobName", "User", "Partition", "State", "Elapsed", "Timelimit",
        "AllocCPUS", "TotalCPU", "ReqMem", "MaxRSS"]
JUNK = ["", " ", "-", "0", "-5", "1e309", "nan", "inf", "NaN", "abc", "::", "1-", "-1-00:00:00",
        "99:99:99", "00:00:00.5.5", "1:2:3:4", "4000Mc", "4000Mn", "16G", "16Gx", "c", "n", "M",
        "1T", "12345678901234567890", "UNLIMITED", "Partition_Limit", "COMPLETED", "RUNNING",
        "OUT_OF_MEMORY", "TIMEOUT", "CANCELLED by 0", "123", "123.batch", "123_[1-3]", "éè",
        "<script>", "\"quoted\"", "a|b", "1,2", "\t", "00:00", "0-00:00:00", "1-00:00:00"]


def call(text):
    """Bad cell values must never reject the file: only a missing/unusable header may raise ValueError."""
    try:
        out = a.analyze(text)
    except ValueError as e:
        assert "missing" in str(e).lower(), "bad cell rejected the whole file: %r" % e
        return None
    assert isinstance(out, dict) and "jobs" in out and "summary" in out
    return out


@pytest.mark.parametrize("value", ["inf", "nan", "infG", "nanM", "1e400M", "-5M", "Infinity", "1-", "::", "1:2:3:4",
                                   "-01:00:00", "1e400", "99999999999999999999"])
def test_bad_cell_values_are_treated_as_missing(value):
    assert a.parse_duration(value) is None or a.parse_duration(value) >= 0
    m = a.parse_mem_mb(value)
    assert m is None or (m >= 0 and m != float("inf") and m == m)


def test_one_bad_row_does_not_hide_the_good_ones():
    text = ("JobID|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"
            "1|COMPLETED|inf|02:00:00|nan|1:2:3:4|infG|nanM\n"
            "2|COMPLETED|01:00:00|02:00:00|2|01:00:00|4G|1G\n")
    out = a.analyze(text)
    assert [j["job_id"] for j in out["jobs"]] == ["1", "2"]
    bad, good = out["jobs"]
    assert bad["cpu_efficiency"] is None and bad["memory_efficiency"] is None
    assert good["cpu_efficiency"] == pytest.approx(50.0) and good["memory_efficiency"] == pytest.approx(25.0)


@pytest.mark.parametrize("seed", range(300))
def test_random_values_never_crash(seed):
    rnd = random.Random(seed)
    rows = ["|".join(COLS)]
    for i in range(rnd.randint(1, 8)):
        vals = [rnd.choice(JUNK) for _ in COLS]
        if rnd.random() < 0.7:
            vals[0] = str(1000 + i) + rnd.choice(["", ".batch", ".0", ".extern"])
        rows.append("|".join(vals[:rnd.randint(1, len(vals))]))  # sometimes truncated rows
    call("\n".join(rows))


@pytest.mark.parametrize("seed", range(100))
def test_random_bytes_never_crash(seed):
    rnd = random.Random(10_000 + seed)
    text = "".join(rnd.choice("|,\n\r\t :.-0123456789KMGTcnabcJobIDStateElapsedAllocCPUSTotalCPU")
                   for _ in range(rnd.randint(0, 400)))
    call(text)


def test_degenerate_inputs():
    for text in ["", "\n\n", "|", ",", "JobID", "JobID|State|Elapsed|AllocCPUS|TotalCPU",
                 "JobID|State|Elapsed|AllocCPUS|TotalCPU\n|||", "﻿JobID|State|Elapsed|AllocCPUS|TotalCPU\n1|COMPLETED|01:00|1|01:00"]:
        call(text)


def test_results_are_json_safe():
    import json
    text = "|".join(COLS) + "\n1|x|u|p|COMPLETED|1e309|nan|inf|nan|nan|nan\n2|y|u|p|COMPLETED|01:00:00|02:00:00|2|01:00:00|4G|1G\n"
    out = call(text)
    if out is not None:
        json.dumps(out, allow_nan=False)  # NaN/Infinity would break the web API's JSON
