# ClusterFlow: handoff and full report (end of 25 Nov 2026)

Read this first in a new session. Keep the new session lean: open files only when a task needs them.

---

## 1. What ClusterFlow is

ClusterFlow (renamed from **HPCFlow** on 25 Nov 2026) analyses Slurm job accounting data (`sacct` exports or published job datasets) and tells researchers and HPC teams what their jobs actually used and what to request next time.

**What it reports:**
- CPU, memory, time and GPU efficiency per job; wasted core-hours and idle GPU-hours.
- Queue wait; summaries per user, per partition, per job array, and by day or week.
- Cost of waste at the centre's own rates (`--cpu-hour-cost`, `--gpu-hour-cost`); it never invents prices.
- Exact advice: `--cpus-per-task`, `--mem`, `--time`, `--gpus`; out-of-memory and timeout jobs flagged.
- **HTML report:** `--html report.html` for one file to open, print or email.
- **For HPC teams:** `--split-by-user DIR` (one report per researcher) and `--compare BEFORE` (what improved).
- **Typical-job advice:** for jobs a user runs 3+ times, sized from near-worst runs (p90 CPU, p95 memory and time).
- "What to fix first" headline; `--anonymise` for shareable reports; plain-English notes when columns are missing.

**How it runs:**
- **Cluster CLI:** `dist/clusterflow.py`, one file, Python 3.6+ standard library only, nothing leaves the cluster. Can run `sacct` itself (`--days N`).
- **Local web app:** FastAPI (`scripts/run.ps1`, http://127.0.0.1:8000): upload/paste, cards, tables, CSV export, "Price the waste" box.

## 2. State at handoff

| Item | State |
|---|---|
| Version | v0.28, **790 tests, all passing** |
| Repository | `C:\Users\Owner\Documents\Computer Science\ClusterFlow\MVP` (v0.14-v0.19 were built in the old `HPCFlow\MVP` copy: run `git pull` in ClusterFlow\MVP before using it) |
| Backup | Private GitHub repo `Unusualoreo2/ClusterFlow`; **every commit auto-pushes** (post-commit hook, log `.git/autopush.log`) |
| GitHub CLI | Portable build at `%LOCALAPPDATA%\Programs\gh-portable\bin\gh.exe`, signed in as `Unusualoreo2` (Windows admin install not possible) |
| Live cluster | **Never run on one yet** |
| Rename | Complete everywhere: code, docs, output, local folder and GitHub repo (25 Nov 2026) |

## 3. How the work is done (the user's rules)

- **Claude = architect / boss, local Qwen = builder.** Claude writes the spec and tests; Qwen3-Coder implements; Claude verifies and only implements itself after Qwen fails twice. **Use Qwen whenever possible to save Claude usage.**
- Qwen runs locally: llama.cpp router at `http://127.0.0.1:8080/v1`, model `qwen3-coder-30b` (RX 9060 XT GPU).
- **Hand a task to Qwen:** write a task file, then `bash tools/qwen/qwen-task.sh <task.md> [max_tokens] [check-command]`. It runs Qwen with file tools limited to the project, then checks all tests plus the task's own check; on failure it rolls back and retries once. See `tools/qwen/README.md`.
- **Commit only with** `bash tools/safe-commit.sh "message"`: it rebuilds the bundle and refuses to commit unless every test passes.
- **Qwen limits:** its context is 32k tokens, so tell it exactly which lines to read and give ready-made code blocks; keep task files outside the repo (the scratchpad), not in `tools/`.
- **Qwen's second attempt starts from a rollback:** if attempt 1 got close, review its diff before letting attempt 2 run; attempt 2 may rewrite good code. Changing `from analysis import ...` in the CLI needs `scripts/build_bundle.py` to keep stripping it.

- **Qwen tips learned:** give exact `replace_text` snippets with unique anchors; for doc edits, make the new text end with the original heading (Qwen tends to delete headings); always review its diff (it sometimes invents field names, duplicates code or picks a simpler design); keep each task small.

## 4. What was built (25 Nov 2026, chronological)

| Version | Content |
|---|---|
| Setup | Local Qwen given file tools (script, then Open WebUI); architect/builder workflow agreed |
| v0.2 | Rebuilt the AI-generated v0.1, whose analysis could not work (no `MaxCPU` in sacct, fake Roofline); real efficiency engine, web API, web page; unsafe scripts removed |
| v0.3 | Real-world sacct quirks; per-user and per-partition summaries |
| v0.4 | Command-line tool for cluster login nodes |
| v0.5 | Fuzz-tested (one bad value used to reject the whole file); single-file bundle; queue wait |
| v0.6 | Kelvin2 pilot kit: six test jobs with known verdicts, automatic checker, `--anonymise`, guide |
| v0.7 | Scale (100k jobs ~2 s); job-array rollup; web table capped at 200 rows |
| v0.8 | Real public sacct captures: all were rejected before; tab files, any-case headers, partial columns with notes; two real-data bugs fixed |
| v0.9 | GPU jobs: GPU-hours, utilisation, idle-GPU advice |
| v0.10 | Usage trend by day or week |
| v0.11 | Cost of waste (CLI + web) |
| v0.12 | Published-dataset format; **full IN2P3 Dec 2024 month: 2.37M real jobs in ~72 s**; readable CLI report ("What to fix first"); typical-job advice |
| v0.13 | Impossible CPU efficiency (Slurm accounting artefact on very short jobs) ignored with a note; project renamed ClusterFlow |
| v0.14 | One-command demo: `clusterflow --demo` (built-in made-up sample showing every finding; also the web page's demo button); fixed `--anonymise` leaking names in typical-job advice |
| v0.15 | `--html report.html` for one file to open, print or email; bundle checked on Python 3.15 |
| v0.16 | Paste-ready `#SBATCH` lines for typical jobs (CLI, HTML, web); bundle tested on real Python 3.6.8 and 3.8.10 (`tests/test_real_old_python.py`, embeddable builds in `%LOCALAPPDATA%\Programs\python-embed`) |
| v0.17 | --split-by-user DIR: one HTML report per user for HPC teams; `analysis.analyze_by_user` parses once (200 users / 20k jobs: 1.4 s, was 28 s) |
| v0.18 | `--compare BEFORE`: what improved between two periods; try-it-yourself guide with before/after samples; Qwen worker cannot edit tests/ |
| v0.19 | `--version`; readable `--help`; web "Download report (HTML)"; HTML report readable in dark mode; IN2P3 month re-checked (same results); progress report and README synced |
| v0.20 | Folder move done (work continues in ClusterFlow\MVP); Docker Desktop + WSL 2 installed (user approved); image hardened (non-root, .dockerignore) and tested by `tests/test_docker.py` |
| v0.21 | Per-user reports show the cluster average; CPU advice wording tidied |
| v0.22 | Queue wait by time-limit band (CLI, HTML, web) |
| v0.23 | Shows the 90% wait mark, since the median hid the tail (IN2P3: 90% started within 14m for limits up to 1 h vs 7h 53m over 24 h); the advice line appears only when waits really grow |
| v0.24 | Advice never lowers memory or time that already ran out (arrays with an OOM task, typical jobs with OOM/TIMEOUT runs); OOM advice uses max(request, MaxRSS) |
| v0.25 | Faster: fixed-layout timestamp fast path and per-day parsing in the trend (400k real jobs 11.0 s -> 9.4 s, same results on Python 3.6/3.8/3.12) |
| v0.26 | Flags single-core jobs that mostly waited (>= 10 min, CPU busy < 25%): 3.3% of real 1-core IN2P3 jobs |
| v0.27 | "What to fix first" shows core-hours wasted, GB-hours of memory unused, GPU-hours idle (real sample: 2,613 multi-core jobs waste 129k core-hours); also on the web page |
| v0.28 | `--split-by-user` also writes index.html (all users by waste, linked); VERSION fixed (was stuck at 0.19) and now tested against this file's Version line: bump both on every release |

**Real-data results (IN2P3, Zenodo 18668107, CC-BY 4.0, not stored in the repo):** 69% average CPU efficiency, 33% memory efficiency, 5.07M wasted core-hours, 15,071 out-of-memory jobs in one month.

## 5. Business side

Kept outside this public repository.

## 6. Waiting on the user

1. **GitHub `workflow` permission:** run `gh auth refresh -h github.com -s workflow` and approve the device code; then move `tools/ci/tests.yml` to `.github/workflows/` (steps in `tools/ci/README.md`). Never commit it there before approval, or every auto-push is rejected.
2. **Kelvin2 (QUB) access:** requested (up to 8 cores / 8 GB per job, <20 core-hours). When granted, follow `docs/pilot-guide.md` (about 15 minutes, 2.5 core-hours).
3. **COSMA: ignore** (user's instruction). No SSH keys exist on this PC.
4. Move to the new folder: run `git pull` in `Computer Science\ClusterFlow\MVP` FIRST, check `git log -1` there matches GitHub, then delete the old `Computer Science\HPCFlow` folder (close sessions using it first).

## 7. Open items and next candidates

- CIUK demo: done (`--demo`, `--html`, web demo button, `docs/try-it-yourself.md`).
- Next candidate: add raw figures to `--csv` (alloc CPUs, memory requested/used, elapsed, time limit, queue wait) as extra columns at the end, for admins working in spreadsheets.
- Typical-job advice tested only on constructed data (IN2P3 has no job names).
- Docker: built and tested (v0.20).
- Python 3.6/3.8: run for real in the test suite (v0.16).
- Roofline / hardware-counter analysis; hosted multi-user version: not started.

## 8. Key files

| File | Purpose |
|---|---|
| `backend/analysis.py` | The engine (parsing, metrics, advice, summaries) |
| `backend/clusterflow_cli.py` | Command-line report |
| `backend/main.py`, `frontend/index.html` | Web app |
| `dist/clusterflow.py` | Single-file cluster build (`scripts/build_bundle.py`) |
| `tests/` | 631 tests (the specs) |
| `docs/progress-report.md` | Detailed history |
| `docs/architecture.md` | All rules and formulas |
| `docs/user-guide.md`, `README.md` | Usage |
| `docs/pilot-guide.md`, `pilot/` | Kelvin2 pilot kit |
| `tools/qwen/`, `tools/safe-commit.sh`, `tools/ci/` | Workflow, gated commits, parked CI |
