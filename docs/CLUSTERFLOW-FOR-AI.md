# ClusterFlow: guide for an AI assistant working on this code

Read this before changing anything. It is short on purpose: open other files only when your task needs them.
Version at time of writing: v0.28 (see `VERSION` in `backend/clusterflow_cli.py`).

## 1. What ClusterFlow does

ClusterFlow reads Slurm job accounting data (the output of `sacct`, or a published job dataset) and tells
researchers and HPC teams how much of what their jobs requested was actually used, and what to request next time.

Example findings: "this job asked for 32 CPUs but kept about 10 busy: request `--cpus-per-task=13`",
"20 jobs asked for far more memory than they used", "jobs with long time limits waited longer to start".

It runs in two ways:
- **Command line** on a cluster login node: `dist/clusterflow.py`, one file, Python 3.6+, standard library only.
  It can run `sacct` itself. No data ever leaves the cluster.
- **Local web app** (FastAPI): upload or paste an export and get cards, tables, CSV and an HTML report.

## 2. Hard rules (never break these)

1. `backend/analysis.py` and `backend/clusterflow_cli.py` must run on **Python 3.6** with the **standard library
   only**. Not allowed: walrus `:=`, f-string `=` specifier, `str.isascii()`, `datetime.fromisoformat`,
   `subprocess.run(capture_output=..., text=...)`, `dataclasses`, builtin generics like `list[int]`.
   (`tests/test_old_python.py` scans for these; `tests/test_real_old_python.py` runs real 3.6.8 and 3.8.10.)
2. **Tests are the specification.** Never edit files in `tests/`. Make the code pass them.
3. **Never invent numbers.** Prices come only from the user's flags. Unknown values are `None`/`null`, never 0.
4. **Advice must never cause a crash:** never suggest less memory or time than a job already ran out of.
5. **Escape everything** that comes from the data before putting it in HTML (`html.escape` in Python,
   `textContent` in the browser). Never use `innerHTML` with data.
6. **One bad value must not reject a file.** Bad cells become missing values; only a missing `JobID` or `State`
   column (or fixed-width output) is an error.
7. Keep changes small and exact. Do not reformat or rewrite code you were not asked to change.

## 3. Files

| Path | What it is |
|---|---|
| `backend/analysis.py` | The engine: parsing, per-job metrics, advice, all summaries. Returns plain dicts. |
| `backend/clusterflow_cli.py` | Command line: text report, HTML report, CSV, JSON, demo data, per-user reports, comparison. |
| `backend/main.py` | FastAPI web app (wraps the engine). |
| `frontend/index.html` | The single web page (vanilla JavaScript). |
| `dist/clusterflow.py` | **Generated** single-file build (engine + CLI). Never edit by hand: run `scripts/build_bundle.py`. |
| `tests/` | ~790 pytest tests: the spec. |
| `docs/HANDOFF.md` | Current state, history, what is waiting. `docs/architecture.md`: rules in more detail. |
| `pilot/` | Six Slurm test jobs with known verdicts and `check_pilot.py` (for a first real-cluster run). |
| `tools/qwen/` | Task runner for the local model. `tools/safe-commit.sh`: commit only if every test passes. |
| `Dockerfile` | Web app image (non-root user). `tests/test_docker.py` builds it when Docker is running. |

## 4. How data flows

```
sacct text --read_sacct--> rows (dicts, canonical column names)
           --merge_steps--> one dict per job (steps 123.batch / 123.0 folded into job 123)
           --analyze_job--> per-job result (metrics + recommendations)
           --_summarise---> {"jobs", "skipped", "warnings", "summary"}
```

- `analyze(text, user=None)`: the main entry point. With `user`, only that user's jobs.
- `analyze_by_user(text)`: `{user: result}` for every user, parsing the text only once.
- The CLI then formats the result: `report()` (text), `html_report()`, `write_csv()`, or JSON.

Input format: `|`, comma or tab separated, column names in any case. The recommended export:
`sacct -P --units=M -S now-7days --format=JobID,JobName,User,Partition,State,Submit,Start,Elapsed,Timelimit,AllocCPUS,TotalCPU,ReqMem,MaxRSS,AllocTRES,TRESUsageInAve`
(No `-X`: memory peaks are recorded on the job steps.)
Jobs that are RUNNING, PENDING, REQUEUED, SUSPENDED or RESIZING are skipped and counted.

## 5. The result (main keys)

Per job (`result["jobs"][i]`): `job_id, name, state, user, partition, elapsed_s, timelimit_s, alloc_cpus,
cpu_efficiency, memory_efficiency, time_used, wasted_core_hours, wait_s, max_rss_mb, req_mem_mb, alloc_gpus,
gpu_hours, gpu_utilization, array_id, start_date, recommendations` (a list of sentences).

`result["summary"]`: `job_count, avg_cpu_efficiency, avg_memory_efficiency, total_wasted_core_hours, avg_wait_s,
max_wait_s, gpu_job_count, total_gpu_hours, avg_gpu_utilization, idle_gpu_hours, trend, wait_by_limit, profiles,
arrays, by_user, by_partition`.

Optional keys added by the CLI: `cost`, `comparison`, `cluster` (per-user reports). The web API adds `fix_first`.

## 6. Metrics and advice rules

Metrics per job:
- CPU efficiency % = TotalCPU / (Elapsed x AllocCPUS) x 100. Values over 150% are a Slurm accounting artefact:
  ignored, with a note.
- Memory efficiency % = MaxRSS / ReqMem x 100 (ReqMem ending `c` = per CPU, `n` = per node).
- Time used % = Elapsed / Timelimit x 100.
- Wasted core-hours = (Elapsed x AllocCPUS - TotalCPU) / 3600 (never below 0).
- Queue wait = Start - Submit.

Advice per job (CPU, memory and time advice only for COMPLETED jobs):
- CPU efficiency < 50% and AllocCPUS > 1: `--cpus-per-task = ceil(AllocCPUS x eff x 1.2)`.
- Single core, CPU busy < 25%, ran >= 10 min: "the job mostly waited (file input/output, network or sleep)".
- Memory efficiency < 50% (and it saves >= 1 GB): `--mem = ceil(MaxRSS x 1.25)` MB.
- Memory efficiency > 90%: warn it is close to the limit.
- Time used < 25%: `--time = Elapsed x 1.5`, rounded up to 15 minutes.
- OUT_OF_MEMORY: `--mem = ceil(max(MaxRSS, request) x 1.5)`. TIMEOUT: more time or checkpointing.
- GPUs: under 50% busy on several GPUs, suggest fewer; under 30% on one, ask if it really uses the GPU.

Summaries:
- **Typical jobs** (`profiles`): same user + job name with >= 3 COMPLETED runs; sized from near-worst runs
  (p90 busy cores x 1.2, p95 memory x 1.2, p95 run time x 1.5). Each gets paste-ready `#SBATCH` lines.
  If any run of that job ran out of memory (or time), no lower memory (or time) is suggested.
- **Job arrays**: tasks grouped by array ID. If any task ran out of memory, never suggest lowering memory.
- **Queue wait by time limit** (`wait_by_limit`): bands up to 1 h / 1-4 h / 4-12 h / 12-24 h / over 24 h, with
  the median and the 90% mark. "Shorter limits can start sooner" is said only when waits really grow.
- **Trend**: by day (export spans <= 14 days) or by week.
- **What to fix first** (`fix_first` in the CLI): counts per kind of advice, most common first, with core-hours
  wasted, GB-hours of memory unused and GPU-hours idle where they apply.

## 7. Command-line flags

`clusterflow [FILE | -] [--days N] [--all-users] [--top N] [--json] [--csv PATH] [--html PATH]
[--split-by-user DIR] [--compare BEFORE] [--anonymise] [--cpu-hour-cost RATE] [--gpu-hour-cost RATE]
[--currency SYMBOL] [--demo] [--version]`

- No FILE: runs `sacct` for the last 7 days. `--demo`: built-in made-up sample (cannot be combined with a file).
- `--split-by-user DIR`: one HTML report per user plus `index.html` (cannot be combined with `--anonymise`).
- `--compare BEFORE`: adds a "Change since before" section.
- Errors go to stderr as `clusterflow: ...` with exit code 2, never a Python traceback.

## 8. Web API

`GET /` page, `GET /api/health`, `GET /api/example` (the demo sample), `POST /api/analyze` (file upload),
`POST /api/analyze-text` (`{"text": ...}`), `POST /api/report-html` (returns the HTML report). Limit 10 MB.

## 9. How to work on a task

1. Read the task and the tests it names. Read only the lines you need (your context is small).
2. Edit with exact, small replacements. Copy the old text exactly from the file, including indentation.
3. Run the tests: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` (all must pass).
4. If you change `backend/analysis.py` or `backend/clusterflow_cli.py`, the bundle is rebuilt by
   `scripts/build_bundle.py` (the task runner and `tools/safe-commit.sh` do this for you).
5. When editing docs, keep every existing heading: make your new text end with the heading you anchored on.
6. A release bumps `VERSION` in `backend/clusterflow_cli.py` and the `| Version |` line in `docs/HANDOFF.md`
   together (a test checks they match).

## 10. Lessons learned (avoid these mistakes)

- `scripts/build_bundle.py` strips lines starting `from analysis import`: keep imports in that form.
- In Python, `"a" + X + "b %s" % y` formats only the last piece: wrap the whole string in brackets first.
- Do not rewrite a whole file to change a few lines; do not invent field names; do not duplicate code.
- Do not delete list items or headings in docs unless the task says so.
- Timing-based tests can be flaky on a busy machine: they use the best of several runs.

## 11. Slurm words

- **sacct**: Slurm's accounting command; lists finished jobs and their resource use.
- **Job step**: part of a job (`123.batch`, `123.0`); memory peaks are recorded per step.
- **AllocCPUS / ReqMem / Timelimit**: what the job asked for. **TotalCPU / MaxRSS / Elapsed**: what it used.
- **Core-hour**: one CPU core for one hour. **Backfill**: Slurm starts small, short jobs in gaps.
- **OUT_OF_MEMORY / TIMEOUT**: the job was killed for exceeding its memory / time limit.
- **#SBATCH lines**: settings at the top of a job script (`#SBATCH --mem=4000M`).
