"""Advice never suggests less of something that already ran out (v0.24). Written by the architect.

Found in review: an array with one out-of-memory task was still told to LOWER memory (sized from the tasks that
finished), and typical-job advice (sized from completed runs only) could lower memory/time for a job that sometimes
runs out of memory/time. Following that advice causes more crashes.
- Single job out of memory: --mem = ceil(max(MaxRSS, request) * 1.5) (MaxRSS is sampled and can be far below the
  real peak at the kill).
- Array with any OUT_OF_MEMORY task: no "Peak memory over ..." advice; the out-of-memory line suggests
  --mem = ceil(max(highest MaxRSS of any task, request) * 1.5): "... request more memory for this array (e.g. --mem=NM)."
- Typical job (same user + name): any OUT_OF_MEMORY run -> no lower-memory advice or #SBATCH --mem line;
  any TIMEOUT run -> no shorter-time advice or #SBATCH --time line. Other advice is unchanged."""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import analysis  # noqa: E402
from test_arrays import HDR as AHDR, task  # noqa: E402
from test_profiles import HDR as PHDR, run_row  # noqa: E402


def test_single_job_oom_uses_the_larger_of_request_and_rss():
    data = PHDR + run_row(1, state="OUT_OF_MEMORY", req="8G", rss="1000M")
    rec = analysis.analyze(data)["jobs"][0]["recommendations"][0]
    assert rec == "Job ran out of memory: request more memory (e.g. --mem=12288M)."


def test_single_job_oom_rss_above_request():
    data = PHDR + run_row(1, state="OUT_OF_MEMORY", req="1G", rss="2000M")
    assert "--mem=3000M" in analysis.analyze(data)["jobs"][0]["recommendations"][0]


def test_array_with_oom_task_is_not_told_to_lower_memory():
    data = AHDR + "".join(task(500, i) for i in range(1, 9)) + task(500, 9, state="OUT_OF_MEMORY", rss="16384M")
    recs = analysis.analyze(data)["summary"]["arrays"][0]["recommendations"]
    assert "1 of 9 tasks ran out of memory: request more memory for this array (e.g. --mem=24576M)." in recs
    assert not any(r.startswith("Peak memory over") for r in recs)


def test_array_without_oom_still_lowers_memory():
    data = AHDR + "".join(task(500, i) for i in range(1, 9))
    recs = analysis.analyze(data)["summary"]["arrays"][0]["recommendations"]
    assert any(r.startswith("Peak memory over") for r in recs)


def profile(data):
    return [p for p in analysis.analyze(data)["summary"]["profiles"] if p["name"] == "sim"][0]


def test_profile_with_oom_run_keeps_memory():
    data = PHDR + "".join(run_row(i) for i in range(1, 6)) + run_row(6, state="OUT_OF_MEMORY", rss="65536M")
    p = profile(data)
    assert not any("--mem=" in r for r in p["recommendations"])
    assert not any(s.startswith("#SBATCH --mem") for s in p["sbatch"])
    assert any("--cpus-per-task=" in r for r in p["recommendations"])      # other advice unchanged


def test_profile_with_timeout_run_keeps_time():
    data = PHDR + "".join(run_row(i) for i in range(1, 6)) + run_row(6, state="TIMEOUT", el="12:00:00")
    p = profile(data)
    assert not any("--time=" in r for r in p["recommendations"])
    assert not any(s.startswith("#SBATCH --time") for s in p["sbatch"])
    assert any("--mem=" in r for r in p["recommendations"])


def test_profile_without_failures_unchanged():
    p = profile(PHDR + "".join(run_row(i) for i in range(1, 6)))
    assert [s.split("=")[0] for s in p["sbatch"]] == ["#SBATCH --cpus-per-task", "#SBATCH --mem", "#SBATCH --time"]
