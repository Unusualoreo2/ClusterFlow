# HPCFlow architecture (v0.2)

Owner of decisions: Claude (architect). Implementation: Qwen. Every change is verified by running tests before it is accepted.

## Review of v0.1 (why it is being rebuilt)

- `sacct` has **no `MaxCPU` field**, and `MaxRSS` comes with unit suffixes (`4200M`, `3.2G`). Real exports would crash the parser.
- `MaxRSS / Elapsed` is not memory bandwidth, and `MaxCPU / 1e12` is not a FLOP ratio. sacct records neither FLOPs nor bytes moved, so **a Roofline classification cannot be computed from sacct alone**. v0.1 always answered "Balanced".
- `Elapsed` can be `MM:SS`, `HH:MM:SS` or `D-HH:MM:SS`. v0.1 only handled one form.
- Only the first row of the file was analysed.
- The Dockerfile start command (`backend/main:app`) is invalid. `/docs` overrides FastAPI's own docs with a file that does not exist. The frontend is never served.
- `scripts/optimize.sh` rewrites source files with `sed`. Removed from use.

## Product decision

HPCFlow v0.2 is a **Slurm job efficiency analyser**. It answers the question every HPC user can act on: *did my jobs use what they asked for, and what should I request next time?* This is measurable from sacct. Roofline analysis comes back later as an optional add-on fed by `likwid`/`perf` counters, which really contain FLOPs and bytes.

## Input

The user exports their jobs with:

```
sacct -P --units=M -S now-7days --format=JobID,JobName,User,Partition,State,Elapsed,Timelimit,AllocCPUS,TotalCPU,ReqMem,MaxRSS > jobs.txt
```

`-P` gives `|`-separated output. Comma-separated files (`--delimiter=,`) are also accepted. The delimiter is detected from the header line.
Do **not** add `-X` (allocations only): `MaxRSS` is recorded on the job steps, so with `-X` memory figures are empty. HPCFlow merges each job's steps (`123.batch`, `123.0`) into the parent job, taking the largest MaxRSS.

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

## Components

- `backend/analysis.py`: pure Python standard library, no pandas. Parsing, metrics and recommendations. Fully unit-tested.
- `backend/main.py`: FastAPI. `POST /api/analyze` (file upload) returns JSON. `GET /` serves `frontend/index.html`.
- `frontend/index.html`: upload, summary cards and a per-job table.
- `tests/`: pytest, run with `python -m pytest`.
