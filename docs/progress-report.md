# HPCFlow progress report (25 Nov 2026)

## Summary

HPCFlow v0.2 is built, tested and committed. It is a Slurm job efficiency analyser: it reads a `sacct` export and shows, per job, how much of the requested CPU, memory and time was used, how many core-hours were wasted, and what to request next time. It runs as a local web app on Windows.

## Team and workflow

- **Claude (architect):** product decisions, specifications, acceptance tests, review and verification.
- **Qwen3-Coder 30B (builder, running locally):** wrote the code and documentation to spec.
- Every change was accepted only after the tests passed and a manual or browser check, then committed to a local git repository.

## What was done

1. **Reviewed v0.1.** Its core analysis could not work. It relied on a `MaxCPU` field that `sacct` does not have, treated memory size as memory bandwidth, and labelled every job "Balanced". A Roofline analysis cannot be done from `sacct`, which records no FLOP or memory-traffic data.
2. **Redefined the product** as a job efficiency analyser, which `sacct` data can genuinely support. Roofline moved to the roadmap (it needs likwid/perf counter data). See `docs/architecture.md`.
3. **Built v0.2:**
   - Analysis engine (`backend/analysis.py`): Python standard library only, handles every Slurm duration and memory format, merges job steps.
   - Web API (`backend/main.py`): file upload, pasted text, example data, input limits and clear errors.
   - Frontend (`frontend/index.html`): summary cards, colour-coded per-job table, recommendations, CSV export. Job names from uploaded files are rendered safely as text.
   - Windows start script (`scripts/run.ps1`), Dockerfile, README, user guide, updated company plan.
4. **Removed unsafe v0.1 scripts:** `cleanup.sh` deleted every Docker image and container on the machine, and `optimize.sh` overwrote source files. Both can still be recovered from git history.

## Quality

- 49 automated tests, all passing.
- Bugs caught in review and fixed: a formula printed instead of a number in the out-of-memory advice, all efficiency bars showing red, a malformed CSV export with duplicate downloads, inverted advice in the user guide, and a wrong export command (`-X` hides memory data).
- An unverifiable statistic ("60%+ of HPC jobs underutilised, NVIDIA survey") was removed from the README and the company plan.

## v0.3 (same day)

- **Ready for real exports:** new tests cover array jobs, `.extern` steps, memory in KB, heterogeneous jobs, Windows line endings and failed jobs. Three bugs were found and fixed: a crash on repeated header lines, `--time=00:00:00` advice for jobs that never started, and requeued or suspended jobs being analysed as finished.
- **Per-user and per-partition summaries:** jobs, average efficiencies and wasted core-hours per user and per partition, sorted by waste, shown as two tables in the web app. Review caught an averaging bug (dividing by all jobs instead of jobs with a value) before it was committed.
- 65 automated tests, all passing.

## v0.4 (same day)

- **Command-line version** (`backend/hpcflow_cli.py`) that runs on the cluster itself: it calls `sacct`, prints the report (summary, by-user and by-partition tables, top jobs by waste with recommendations) and can write CSV or JSON. Standard library only, Python 3.7+ syntax. No data leaves the cluster.
- Qwen's draft passed 76 of 79 tests but read data fields that don't exist. After two failed rounds, Claude rewrote the report functions.
- 79 automated tests, all passing.

## v0.5 (same day)

- **Crash-proof:** a fuzz test feeds 400+ random and garbled exports through the engine. It found that one unreadable value (e.g. `inf`, `1-`, `123_[1-3]`) rejected the entire file in 217 of 416 cases. Unreadable, negative or infinite values are now treated as missing, and the rest of the file is still analysed.
- **One-file install for clusters:** `scripts/build_bundle.py` builds `dist/hpcflow.py` (engine + CLI in one file, Python 3.7+, Linux line endings enforced by `.gitattributes`). Users copy a single file.
- **Queue wait time:** from `sacct`'s Submit/Start columns. Per job, average and longest overall, and average per user/partition. Shown in the CLI ("Avg/Max queue wait") and the web app (card + column).
- **Workflow fixes:** the automation now judges success by the tests plus a task-specific check (not by what Qwen says), rolls back a failed attempt before retrying, and stops Qwen when it loops on a passing test suite. Qwen reads files in 200-line chunks and can search, so it no longer runs out of memory on large files.
- 521 automated tests, all passing.

## v0.6 (same day): Kelvin2 pilot kit

- **Pilot test jobs** (`pilot/`): six Slurm jobs with known correct verdicts (well sized, too many CPUs, too much memory, too much time, out of memory, timeout), about 2.5 core-hours in total, plus `submit_all.sh`.
- **Automatic pilot check** (`pilot/check_pilot.py`): reads HPCFlow's JSON output and prints PASS/FAIL per test job.
- **`--anonymise`**: shareable reports, with users, job names and job IDs replaced by `user1`/`job1`/`J1`.
- **Better advice, found by simulating the pilot:** no more "request --mem=14M" on small jobs (memory cuts only when they save at least 1 GB), and no "request less" advice derived from failed, out-of-memory or timed-out runs.
- **Old-Python check:** a test scans the cluster file for anything newer than Python 3.6 (verified to catch planted violations); Python 3.6 itself is not installed here, so this is a scan, not a run.
- **Guide:** `docs/pilot-guide.md`, step by step, without guessing Kelvin2-specific settings.
- Kelvin2 access requested (25 Nov 2026). 540 automated tests, all passing.

## v0.7: scale and job arrays

- **Scale measured:** 100,000 jobs analyse in about 2 seconds (linear); a performance test guards against slowdowns. No optimisation was needed.
- **Job-array rollup:** one entry per array with task states, average efficiencies, peak memory and advice from completed tasks only (failed tasks reported separately), in the engine, CLI and web app.
- **Web app shows at most 200 jobs** (most wasteful first); the CSV keeps all of them, so large uploads no longer freeze the browser.
- **Cleanup:** removed duplicate, self-recursive helper functions left by an interrupted AI edit; a new test fails on any duplicate definition.

## v0.8: real-world exports

- **First contact with real data:** public `sacct` captures from real clusters (published in an open-source R package; kept outside this repository). **All 10 files were rejected at first.** Now every job-data file is read, including exports with 1,328 real jobs, tab-separated files, lowercase headers and partial columns.
- **Partial exports:** only `JobID` and `State` are required; missing columns produce plain-English notes in the CLI and a yellow box in the web app instead of an error. CPU count and memory request fall back to `NCPUS` / `AllocTRES` / `ReqTRES`.
- **Two real bugs fixed:** Slurm marks some jobs `FAILED` when a step ran out of memory, so HPCFlow now reports `OUT_OF_MEMORY` with memory advice; and missing CPU data now shows wasted core-hours as unknown instead of 0.0.
- **Market research kit** (`docs/market-research-kit.md`): prompts for Gemini Deep Research and NotebookLM, with a verification step before results enter the company plan.
- 578 automated tests, all passing.

## v0.9: GPU jobs

- **GPU-hours and utilisation:** GPUs counted from `AllocTRES` (`gres/gpu=N` or typed `gres/gpu:a100=N`); utilisation from `TRESUsageInAve` (`gres/gpuutil`) where the cluster records it. Reported per job, user, partition and overall; GPU columns added to every export command.
- **Idle-GPU advice:** completed jobs under 50% busy on several GPUs get a `--gpus=` suggestion; single-GPU jobs under 30% are asked whether they really use the GPU.
- **CLI and web app:** GPU lines in the report and a GPU-hours card, shown only when the export has GPU jobs.
- **Workflow:** Qwen built the engine, summaries, CLI lines and docs; it failed the web card's HTML edit three times (run live and relayed to you), so Claude added it. The edit tool now matches text even when Qwen drops indentation.
- Not verified: GPU utilisation on a real cluster (needs GPU accounting enabled).
- 594 automated tests, all passing; backed up to GitHub automatically.

## v0.10: usage trend over time

- **Trend table** in the engine, CLI and web app: jobs grouped by start day (exports of 14 days or less) or by week, with efficiency, wasted core-hours, GPU-hours and queue wait per period, oldest first.
- **Workflow:** Qwen built the engine part first try and the display in one run; Claude corrected a one-space indentation slip and made the edit tool align replacements properly.
- 602 automated tests, all passing; backed up to GitHub automatically.

## v0.11-v0.12: cost, real data at scale, readable report, typical-job advice (evening 25 Nov)

- **Cost of waste** in the CLI (`--cpu-hour-cost`, `--gpu-hour-cost`, `--currency`) and a "Price the waste" box in the web app; idle GPU-hours priced from utilisation. HPCFlow never invents prices.
- **Real data at scale:** reads the published IN2P3 2024 dataset format (Unix timestamps, durations in seconds, lowercase states). The full December 2024 month, **2.37 million real jobs, analyses in 72 seconds**: 69% CPU efficiency, 33% memory efficiency, 5.07 million wasted core-hours, 15,071 out-of-memory jobs. Profiling confirmed linear scaling and found one speed-up (applied).
- **Readable CLI report for the CIUK demo:** "What to fix first" headline (e.g. *84,390 jobs: request a shorter time limit* on a 100k-job sample), thousands separators, `--top` limits every table.
- **Typical-job advice:** for jobs a user runs 3+ times, advice sized from the near-worst runs (p90 CPU, p95 memory and time), so one unusually small run cannot cause a crash-prone recommendation. In the CLI, web app and docs.
- **Process:** a gated commit helper (`tools/safe-commit.sh`) now refuses to commit unless all tests pass, after one broken test file reached GitHub for about 30 seconds. Qwen built almost everything; Claude implemented the readable report after Qwen failed it twice.
- Open: 6 jobs in the IN2P3 month show impossible >150% efficiencies (likely dataset quirks; not investigated). IN2P3 has no job names, so typical-job advice was tested on constructed data only.
- 627 automated tests, all passing; backed up to GitHub automatically.

## Not yet done

- Test with real `sacct` exports from a university cluster. So far only realistic sample data has been used.
- Build and run the Docker image (Docker is not installed on this PC).
- Publish the code on GitHub.
- Roadmap: job history and trends, per-user and per-partition summaries, then a Roofline prototype from likwid data.

## How to run

```
powershell -ExecutionPolicy Bypass -File scripts\run.ps1
```

Then open http://127.0.0.1:8000 and click "Try example data".
