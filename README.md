# HPCFlow

A Slurm job efficiency analyser that shows how much of the requested CPU, memory and time jobs actually used, and what to request next time.

## Export your jobs

```
sacct -P --units=M -S now-7days --format=JobID,JobName,User,Partition,State,Submit,Start,Elapsed,Timelimit,AllocCPUS,TotalCPU,ReqMem,MaxRSS > jobs.txt
```

Do not add `-X`: memory usage is recorded on the job steps, which HPCFlow merges into each job automatically.

## Run it on Windows

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.txt
powershell -ExecutionPolicy Bypass -File scripts\run.ps1
```

Open http://127.0.0.1:8000

## Run it on the cluster (command line)

Copy `backend/analysis.py` and `backend/hpcflow_cli.py` to the cluster (Python 3.7+, standard library only), then on a login node:

```bash
python3 hpcflow_cli.py                 # runs sacct for your jobs of the last 7 days
python3 hpcflow_cli.py --days 30 --top 10
python3 hpcflow_cli.py jobs.txt --csv report.csv
sacct -P ... | python3 hpcflow_cli.py -
```

Options: `--all-users` (admins: adds `-a` to sacct), `--json` (machine-readable output). No data leaves the cluster.

## Run it with Docker

```bash
docker build -t hpcflow .
docker run -p 8000:8000 hpcflow
```

## API

- `GET /` serves the frontend
- `POST /api/analyze` accepts a sacct file upload and returns JSON
- `POST /api/analyze-text` accepts sacct text in a JSON body and returns JSON
- `GET /api/example` returns an example sacct export
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

When the export includes `Submit` and `Start`, HPCFlow also shows how long jobs waited in the queue: the average and longest wait overall, the average per user and per partition, and the wait of each job. Jobs that never started have no wait time.

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