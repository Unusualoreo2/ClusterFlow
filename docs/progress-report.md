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
