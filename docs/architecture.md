# ClusterFlow architecture (v0.2)

Owner of decisions: the architect. Implementation: Qwen. Every change is verified by running tests before it is accepted.

## Review of v0.1 (why it is being rebuilt)

- `sacct` has **no `MaxCPU` field**, and `MaxRSS` comes with unit suffixes (`4200M`, `3.2G`). Real exports would crash the parser.
- `MaxRSS / Elapsed` is not memory bandwidth, and `MaxCPU / 1e12` is not a FLOP ratio. sacct records neither FLOPs nor bytes moved, so **a Roofline classification cannot be computed from sacct alone**. v0.1 always answered "Balanced".
- `Elapsed` can be `MM:SS`, `HH:MM:SS` or `D-HH:MM:SS`. v0.1 only handled one form.
- Only the first row of the file was analysed.
- The Dockerfile start command (`backend/main:app`) is invalid. `/docs` overrides FastAPI's own docs with a file that does not exist. The frontend is never served.
- `scripts/optimize.sh` rewrites source files with `sed`. Removed from use.

## Product decision

ClusterFlow v0.2 is a **Slurm job efficiency analyser**. It answers the question every HPC user can act on: *did my jobs use what they asked for, and what should I request next time?* This is measurable from sacct. Roofline analysis comes back later as an optional add-on fed by `likwid`/`perf` counters, which really contain FLOPs and bytes.

## Input

The user exports their jobs with:

```
sacct -P --units=M -S now-7days --format=JobID,JobName,User,Partition,State,Submit,Eligible,Start,Elapsed,Timelimit,AllocCPUS,TotalCPU,ReqMem,MaxRSS,AllocTRES,TRESUsageInAve > jobs.txt
```

`-P` gives `|`-separated output. Comma-separated files (`--delimiter=,`) are also accepted. The delimiter is detected from the header line.
Do **not** add `-X` (allocations only): `MaxRSS` is recorded on the job steps, so with `-X` memory figures are empty. ClusterFlow merges each job's steps (`123.batch`, `123.0`) into the parent job, taking the largest MaxRSS.

## Metrics, per job

| Metric | Formula |
|---|---|
| CPU efficiency % | `TotalCPU_s / (Elapsed_s * AllocCPUS) * 100` |
| Memory efficiency % | `MaxRSS_MB / ReqMem_MB * 100` (ReqMem ending in `c`/`Mc` = per CPU: multiply by AllocCPUS; `n`/`Mn` = per node) |
| Time used % | `Elapsed_s / Timelimit_s * 100` |
| Wasted core-hours | `(Elapsed_s * AllocCPUS - TotalCPU_s) / 3600` |

## Recommendations (rules)

- CPU efficiency < 50% and AllocCPUS > 1 → suggest `ceil(AllocCPUS * eff * 1.2)` CPUs (at least 1), or check the code really runs in parallel.
- Memory efficiency < 50% → suggest `ceil(MaxRSS_MB * 1.25)` MB.
- Memory efficiency > 90% → warn that the job is close to its memory limit.
- Time used < 25% → suggest a time limit of `Elapsed * 1.5`, rounded up to the next 15 minutes.
- State `OUT_OF_MEMORY` / `TIMEOUT` → say so and suggest more memory / more time.
- Jobs that are still running (`RUNNING`, `PENDING`) are skipped.

## Group summaries (v0.3)

When the header has `User` / `Partition`, `summary.by_user` / `summary.by_partition` list one entry per value (`(unknown)` if blank) with `job_count`, `avg_cpu_efficiency`, `avg_memory_efficiency` (averages over jobs that have a value) and `wasted_core_hours`, sorted by wasted core-hours descending. Otherwise both lists are empty.

Jobs in states RUNNING, PENDING, REQUEUED, SUSPENDED and RESIZING are skipped. Repeated header lines (joined exports) are ignored.

## Queue wait (v0.5)

`wait_s = Start - Submit` in seconds (timestamps `YYYY-MM-DDTHH:MM:SS`; `Unknown`/`None` or Start before Submit give no value). Summary: `avg_wait_s`, `max_wait_s`; groups: `avg_wait_s`. Bad cell values anywhere are treated as missing, never as a reason to reject the file.

## Real-world exports (v0.8)

Tested against public `sacct` captures from real clusters. ClusterFlow reads `|`, comma and tab separated exports, column names in any case (`maxrss` = `MaxRSS`), and only requires `JobID` and `State`. Missing columns are reported as `warnings` (e.g. no `TotalCPU` -> no CPU efficiency) instead of rejecting the file. Fallbacks: CPU count from `NCPUS` or `cpu=` in `AllocTRES`/`ReqTRES`; memory request from `mem=` in `AllocTRES`/`ReqTRES`. A job Slurm marks `FAILED` whose step ran `OUT_OF_MEMORY` is reported as `OUT_OF_MEMORY`. Unknown totals are `null`, never 0. Fixed-width output (exported without `-P`) is refused with the correct export command. Job arrays are summarised in `summary.arrays`; the web table shows at most the 200 most wasteful jobs (CSV has all).

## GPU jobs (v0.9)

GPUs come from `AllocTRES` (or `ReqTRES`): `gres/gpu=N`, or typed `gres/gpu:<type>=N` (if both appear, the untyped total counts). `gpu_hours = GPUs x Elapsed`. Utilisation is the highest `gres/gpuutil` in `TRESUsageInAve` across the job and its steps; it exists only where the cluster has GPU accounting enabled, otherwise a note says it is unavailable. Advice (completed jobs only): under 50% busy on several GPUs, suggest `--gpus=ceil(GPUs x util x 1.2)`; under 30% on one GPU, ask whether the job really uses the GPU. Summary: `gpu_job_count`, `total_gpu_hours`, `avg_gpu_utilization`; groups: `gpu_hours`.

## Usage trend (v0.10)

`summary.trend = {"period": "day" | "week" | null, "rows": [...]}`. Jobs are dated by `Start` (falling back to `Submit`); exports spanning 14 days or less are grouped by day, longer ones by week (named after its Monday). Rows have the same fields as the per-user groups and are sorted oldest first. The CLI and web app show the trend only when there are at least two periods.

## Typical-job profiles (v0.12)

`summary.profiles`: per (user, job name) with at least 3 COMPLETED runs: `cpus_needed = ceil(p90 busy cores x 1.2)`, `mem_needed = ceil(p95 peak memory x 1.2)`, `time_needed = p95 run time x 1.5` rounded up to 15 minutes; compared with the median request. Advice only when it reduces the request (memory by at least 1 GB, time by more than half). Sorted by wasted core-hours.

## Components

- `backend/analysis.py`: pure Python standard library, no pandas. Parsing, metrics and recommendations. Fully unit-tested.
- `backend/main.py`: FastAPI. `POST /api/analyze` (file upload) returns JSON. `GET /` serves `frontend/index.html`.
- `frontend/index.html`: upload, summary cards and a per-job table.
- `tests/`: pytest, run with `python -m pytest`.
