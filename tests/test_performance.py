"""Scale (v0.7): admins may analyse a month of a whole cluster. Written by the architect."""
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
import analysis as a  # noqa: E402

HDR = "JobID|JobName|User|Partition|State|Submit|Start|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS"


def make(n, seed=1):
    rnd = random.Random(seed)
    rows = [HDR]
    for i in range(n):
        jid = str(1000000 + i)
        c = rnd.choice([1, 2, 4, 8, 16, 32])
        rows.append("|".join([jid, "job%d" % (i % 50), "user%d" % (i % 300), rnd.choice(["compute", "gpu"]),
                              "COMPLETED", "2026-11-20T09:00:00", "2026-11-20T09:%02d:00" % rnd.randint(0, 59),
                              "%02d:%02d:00" % (rnd.randint(1, 23), rnd.randint(0, 59)), "24:00:00", str(c),
                              "%02d:00:00" % rnd.randint(0, 99), "%dG" % rnd.choice([4, 8, 64]), ""]))
        rows.append("|".join([jid + ".batch", "batch", "", "", "COMPLETED", "", "", "01:00:00", "", str(c),
                              "01:00:00", "", "%dM" % rnd.randint(10, 60000)]))
    return "\n".join(rows) + "\n"


def test_20k_jobs_under_1_second():
    text = make(20000)
    best = min(_timed(text) for _ in range(3))
    assert best < 1.0, "analysing 20k jobs took %.2f s" % best


def _timed(text):
    t = time.perf_counter()
    out = a.analyze(text)
    dt = time.perf_counter() - t
    assert out["summary"]["job_count"] == 20000
    return dt


def test_parse_timestamp_fast_and_correct():
    from datetime import datetime
    assert a.parse_timestamp("2026-11-20T09:05:07") == datetime(2026, 11, 20, 9, 5, 7)
    assert a.parse_timestamp("2026-11-20 09:05:07") == datetime(2026, 11, 20, 9, 5, 7)
    for bad in ("2026-13-40T99:00:00", "2026-11-20X09:05:07", "2026/11/20T09:05:07", "Unknown", "", None, "2026-11-20T09:05", "2026-11-20T09:05:07Z"):
        assert a.parse_timestamp(bad) is None, bad
    t = time.perf_counter()
    for _ in range(100000):
        a.parse_timestamp("2026-11-20T09:05:07")
    assert time.perf_counter() - t < 0.5, "parse_timestamp is too slow"
