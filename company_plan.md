# HPCFlow - Company Plan

## Overview
HPCFlow is an open-source Slurm job efficiency analyser. It reads a `sacct` export and shows, per job, how much of the requested CPU, memory and time was actually used, how many core-hours were wasted, and exactly what to request next time. Designed for researchers, students and engineers on Slurm clusters.

## Problem
Many HPC jobs use far less of their allocated CPU and memory than they request (TODO: find a real, citable source for how common this is). Most users do not profile or optimize their code, despite Slurm logs being readily available. There is a gap in accessible, lightweight tools that turn raw job data into actionable performance insights.

## Product
Status: v0.2 built and tested (49 automated tests; web app runs locally on Windows or in Docker).

HPCFlow reads Slurm job results exported with `sacct` (pipe- or comma-separated) and:
- Merges each job's steps and computes CPU efficiency, memory efficiency, share of the time limit used and wasted core-hours.
- Gives concrete recommendations: the `--cpus-per-task`, `--mem` and `--time` values to request next time, and flags jobs that ran out of memory or time.
- Shows the results in a web page (summary cards, per-job table, CSV export).

Not built yet: Roofline / code-level optimisation advice. `sacct` does not record FLOPs or memory traffic, so this needs hardware-counter data (likwid or perf) and is on the roadmap.

## Target Customers
- Academic HPC researchers and students at universities.
- Engineering teams in industry using HPC clusters.
- HPC system administrators seeking performance diagnostics tools.

## Revenue Model
- **MVP (0–3 months):** Open-source on GitHub (MIT license), no direct revenue.
- **Freemium (3–6 months):** Add dashboard with job history and advanced analytics; $20/month for lab teams.
- **Enterprise (6–12 months):** Sell site licenses to universities; $500–$2,000/year per lab.
- **Long-term (12+ months):** Apply for grants (EPSRC, EU HPC) to fund development and scaling.

## Roadmap (Next 3 Months)
- Done (Nov 2026): v0.2 analysis engine, FastAPI web app, frontend, Docker image, tests.
- Month 1: Validate on real `sacct` exports from a university cluster; publish on GitHub.
- Month 2: Job history and trends over time; per-user and per-partition summaries.
- Month 3: Prototype Roofline analysis from `likwid` counter data.

## Risks
- Lack of real-world `sacct` data for testing (requires user or lab access).
- Low adoption if no visual dashboard or exportable reports.
- Limited monetization in early phase without premium features.
- Compliance risk if user data is accidentally stored (mitigated by in-memory processing).

TODO: Confirm with lab or HPC admin for real `sacct` CSV sample to validate analysis.