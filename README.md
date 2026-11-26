# ClusterFlow

A Slurm job efficiency analyser that shows how much of the requested CPU, memory and time jobs actually used, and what to request next time.

## Export your jobs

```
sacct -P --units=M -S now-7days --format=JobID,JobName,User,Partition,State,Submit,Start,Elapsed,Timelimit,AllocCPUS,TotalCPU,ReqMem,MaxRSS,AllocTRES,TRESUsageInAve > jobs.txt
```

Do not add `-X`: memory usage is recorded on the job steps, which ClusterFlow merges into each job automatically.

## Which exports work

`|`, comma or tab separated `sacct` output with at least `JobID` and `State`. The more of the columns above you include, the more ClusterFlow can tell you: any figure it cannot compute is listed as a note instead of being guessed. Output from `sacct` without `-P` (space-padded columns) is not supported.

## Run it on Windows

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.txt
powershell -ExecutionPolicy Bypass -File scripts\run.ps1
```

Open http://127.0.0.1:8000

## Run it on the cluster (command line)

Copy the single file `dist/clusterflow.py` to the cluster (Python 3.6+, standard library only; tested on real 3.6.8 and 3.8.10), then on a login node:

```bash
python3 clusterflow.py                 # runs sacct for your jobs of the last 7 days
python3 clusterflow.py --demo           # see what a report looks like (made-up data)
python3 clusterflow.py --days 30 --top 10
python3 clusterflow.py jobs.txt --csv report.csv     # one row per job, raw figures included
python3 clusterflow.py jobs.txt --html report.html   # one file to open, print or email
python3 clusterflow.py --all-users --split-by-user reports/   # admins: one HTML report per user
python3 clusterflow.py --days 30 --compare last_quarter.txt   # what improved since an earlier export
sacct -P ... | python3 clusterflow.py -
```

Other options: `--all-users` (admins: adds `-a` to sacct), `--anonymise` (no names, safe to share), `--json` (machine-readable output), `--top N`, `--version`. Run `python3 clusterflow.py --help` for all of them. No data leaves the cluster.

## Run it with Docker

Tested with Docker Desktop 29 (WSL 2) on Windows 11: the image serves the web app on port 8000 and runs as a non-root user. `tests/test_docker.py` builds and checks it whenever Docker is running.

```bash
docker build -t clusterflow .
docker run -p 8000:8000 clusterflow
```

## Results on real data

Analysis of the IN2P3 Computing Center 2024 job dataset (Zenodo record 18668107, CC-BY 4.0) was performed on a desktop PC. The dataset is not stored in this repository.

| Metric | Value |
|------|-------|
| Average CPU efficiency | 69% |
| Average memory efficiency | 33% |
| Wasted core-hours | 5,072,809 |
| Out-of-memory jobs | 15,071 |

December 2024 data, comprising 2,374,219 jobs, was processed in about 72 seconds. The --split-by-user option generated 383 per-user HTML reports in under 3 minutes. A pilot of ClusterFlow on QUB's Kelvin2 is planned, using the pilot kit in the pilot/ directory.

ClusterFlow has not yet been run on a live university cluster.

## GPU jobs

If your export includes `AllocTRES` (and, on clusters with GPU accounting, `TRESUsageInAve`), ClusterFlow reports GPU-hours, average GPU utilisation and advice for idle GPUs, overall, per user and per job.

## Cost of waste

ClusterFlow never guesses prices. Give it your centre's rates and it prices the waste:

```bash
python3 clusterflow.py --cpu-hour-cost 0.02 --gpu-hour-cost 1.50 --currency £
```

The web app has a "Price the waste" box for the same. Wasted CPU time = allocated minus used core-hours; idle GPU time = GPU-hours x (100% - GPU utilisation).

## API

- `GET /` serves the frontend
- `POST /api/analyze` accepts a sacct file upload and returns JSON
- `POST /api/analyze-text` accepts sacct text in a JSON body and returns JSON
- `POST /api/report-html` accepts sacct text in a JSON body and returns the self-contained HTML report
- `GET /api/example` returns the built-in demo sample (the same data as `--demo`)
- `GET /api/health` returns a health check

## What it measures

Per job, plus per-user and per-partition summaries (sorted by wasted core-hours) when the export includes the User and Partition columns.

| Metric | Formula |
|---|---|
| CPU efficiency % | `TotalCPU_s / (Elapsed_s * AllocCPUS) * 100` |
| Memory efficiency % | `MaxRSS_MB / ReqMem_MB * 100` |
| Time used % | `Elapsed_s / Timelimit_s * 100` |
| Wasted core-hours | `(Elapsed_s * AllocCPUS - TotalCPU_s) / 3600` |

- CPU efficiency < 50% and AllocCPUS > 1 → suggest `ceil(AllocCPUS * eff * 1.2)` CPUs
- Memory efficiency < 50% → suggest `ceil(MaxRSS_MB * 1.25)` MB
- Memory efficiency > 90% → warn that job is close to memory limit
- Time used < 25% → suggest a time limit of `Elapsed * 1.5`, rounded up to the next 15 minutes
- State `OUT_OF_MEMORY` / `TIMEOUT` → say so and suggest more memory / more time
- Jobs that are still running (`RUNNING`, `PENDING`) are skipped.

## Queue wait time

When the export includes `Submit` and `Start`, ClusterFlow also shows how long jobs waited in the queue: the average and longest wait overall, the average per user and per partition, and the wait of each job. Jobs that never started have no wait time.

## Tests

```powershell
.venv\Scripts\python -m pip install pytest httpx
.venv\Scripts\python -m pytest
```

## Roadmap

- Roofline analysis from likwid/perf counters (planned, not built)
- Multi-user hosted version (planned)

## License

MIT (see LICENSE)