# HPCFlow: full project report

**Date:** 25 November 2026 (one working day, roughly 11:00 to 15:15)
**Status:** v0.8, 578 automated tests passing, 46 commits, backed up to a private GitHub repository.

---

## 1. Summary

HPCFlow started the day as an AI-generated prototype whose core analysis could not work. It is now a tested **Slurm job efficiency analyser**: it reads `sacct` exports and shows, per job, user, partition and job array, how much of the requested CPU, memory and time was used, how many core-hours were wasted, how long jobs waited, and exactly what to request next time. It runs as a local web app and as a single-file command-line tool for cluster login nodes, and it has been checked against real public Slurm data.

It has **not yet run on a live cluster**. Kelvin2 (QUB) access has been requested, and a pilot kit is ready for when it is granted.

| | Start of day | Now |
|---|---|---|
| Core analysis | Could not work on real `sacct` data | Correct, tested CPU/memory/time efficiency |
| Automated tests | 0 | 578 |
| Real Slurm files read | not tried | all job-data files in a public set (10 of 10 were rejected before v0.8) |
| Ways to use it | Web page (broken start script) | Web app, cluster CLI, single-file bundle |
| Backup | None | Private GitHub repo, automatic push after every commit |

---

## 2. Setting up the AI workflow

1. **Local AI given file access.** The local Qwen model (30B, on this PC's GPU) first got file tools through a small script, then through Open WebUI. The "stuck writing a file" problem was traced to a chat using a model with no file tool attached.
2. **Architect / builder workflow.** You set the rule: Claude is the architect and makes the decisions, Qwen produces the code. In practice:
   - Claude writes the specification and the acceptance tests first.
   - Qwen3-Coder implements through a worker script with file tools limited to the project folder.
   - Nothing is accepted until the tests pass and Claude has reviewed the change; when Qwen fails twice, Claude fixes it and says so in the commit message.
3. **Workflow hardened as problems appeared** (tools now saved in `tools/qwen/`):
   - Qwen froze or ran out of output space: per-request timeouts, output caps, cut-off tool calls discarded.
   - Qwen re-read whole files and ran out of memory: reads in 200-line chunks plus a search tool.
   - Qwen looped on a passing test suite: the worker stops it automatically.
   - A retry stacked on a half-finished attempt and deleted a function: failed attempts are now rolled back before retrying.
   - "Success" was reported when nothing changed (no tests for the page): every task now has its own check command.

**How Qwen performed:** it wrote most of the code and documents (29 commits credit it). Typical failure modes, all caught before committing: inventing data fields that do not exist, duplicating code, deleting headings it was told to keep, and a formula printed instead of a number.

---

## 3. Product decisions

- **Rebuilt the core (v0.2).** The original version read a `MaxCPU` field that `sacct` does not have, treated memory size as bandwidth, and labelled every job "Balanced". A Roofline analysis cannot be done from `sacct` (it records no FLOPs or memory traffic), so the product was redefined around what `sacct` genuinely supports: efficiency against what was requested. Roofline moved to the roadmap.
- **Removed unsafe scripts.** `cleanup.sh` deleted every Docker image and container on the machine; `optimize.sh` overwrote source code.
- **Removed an unverifiable statistic** ("60%+ of HPC jobs underutilised, NVIDIA survey") from the README and company plan.
- **Advice rules refined after simulation:** no memory cuts that save under 1 GB (no more "request 14 MB"), and no "request less" advice from failed, out-of-memory or timed-out runs.

---

## 4. What was built, version by version

| Version | What it added |
|---|---|
| v0.2 | Real analysis engine (Python standard library only), web API, new web page, Windows start script, fixed Dockerfile, docs |
| v0.3 | Handles real-world `sacct` quirks (array jobs, extern steps, KB memory, repeated headers); per-user and per-partition summaries |
| v0.4 | Command-line tool for cluster login nodes: runs `sacct` itself, text/CSV/JSON output, no data leaves the cluster |
| v0.5 | Crash-proofing (fuzz tests on 400+ garbled inputs found that one bad value rejected the whole file in 217 of 416 cases; fixed); single-file cluster build `dist/hpcflow.py`; queue wait time |
| v0.6 | Kelvin2 pilot kit: six test jobs with known answers, automatic PASS/FAIL checker, `--anonymise` for shareable reports, pilot guide, old-Python compatibility check |
| v0.7 | Scale (100,000 jobs in about 2 seconds); job-array rollup; web page shows at most the 200 most wasteful jobs |
| v0.8 | Real public `sacct` data: tab-separated files, any column-name case, partial exports with plain-English notes, TRES fallbacks; two bugs found only on real data fixed (out-of-memory recorded only on a job step; "0.0 wasted" shown when unknown) |

Code size: about 2,000 lines of application code, about 1,450 lines of tests.

---

## 5. Infrastructure and access

- **Version control and backup:** local git from the first change; private GitHub repo `Unusualoreo2/HPCFlow`; a hook pushes every commit automatically (verified). GitHub CLI installed as a portable build because Windows administrator approval was not possible.
- **Automatic testing on GitHub:** a workflow (all tests on Python 3.12, cluster tool on Python 3.8) is written and parked in `tools/ci/`. It needs you to approve GitHub's `workflow` permission once.
- **Clusters:**
  - Kelvin2 (QUB): access requested, for up to 8 cores / 8 GB per job and under 20 core-hours.
  - DiRAC: your CIUK 2026 files point to COSMA at Durham (`login8.cosma.dur.ac.uk`, project `do022`). This PC has no SSH key for it; an attempt to set one up was cancelled at your request.
  - No Edinburgh login was found.
- **Market research:** a Gemini research kit (`docs/market-research-kit.md`) with a context brief, seven Deep Research prompts, a NotebookLM setup and a verification step. Connecting Gemini through the browser was not possible from the laptop.

---

## 6. Not done or not verified

- **No live cluster run yet.** All results come from tests, simulated pilot data and public captures.
- **Old Python:** syntax is scanned for Python 3.6 compatibility; an actual run on 3.8 waits for the GitHub workflow.
- **Docker:** the image has never been built (marked "untested" in the README).
- **Business side:** the company plan's prices are an early AI guess with no evidence; the market research has not been run.
- **Roadmap features:** GPU efficiency, Roofline from hardware counters, history over time, hosted version.

---

## 7. What happens next

1. **Kelvin2 access granted:** run the pilot (`docs/pilot-guide.md`): about 15 minutes and 2.5 core-hours, then `check_pilot.py` reports PASS/FAIL per test job.
2. **Approve GitHub's workflow permission:** switches on automatic testing, including the first Linux and Python 3.8 runs.
3. **Run the market research** with Gemini and bring the answers back for checking before anything changes the company plan.
4. **GitHub Student Developer Pack:** cloud credits could test the Docker image and host a demo; a free domain would support approaching HPC teams.
