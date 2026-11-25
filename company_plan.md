# HPCFlow - Company Plan

## Overview
HPCFlow is an open-source tool that analyzes HPC job performance using Slurm `sacct` CSVs, Roofline model, and profiling data to identify bottlenecks and recommend code optimizations. Designed for Linux, HPC, and academic use, it helps researchers and engineers improve computational efficiency.

## Problem
Many HPC jobs use far less of their allocated CPU and memory than they request (TODO: find a real, citable source for how common this is). Most users do not profile or optimize their code, despite Slurm logs being readily available. There is a gap in accessible, lightweight tools that turn raw job data into actionable performance insights.

## Product
The script reads Slurm job results exported as CSV (via `sacct`) and performs:
- Parses elapsed time, CPU usage, and memory metrics.
- Computes CPU utilization and memory bandwidth.
- Applies a Roofline model to classify workloads as compute-bound, memory-bound, or balanced.
- Returns optimization recommendations (e.g., vectorization for compute-bound, data layout for memory-bound).

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
- Month 1: Complete MVP with core analysis engine and FastAPI web interface.
- Month 2: Implement frontend (React) and integrate with `likwid` for enhanced profiling.
- Month 3: Dockerize, deploy on VPS, and launch GitHub with 100+ stars target.

## Risks
- Lack of real-world `sacct` data for testing (requires user or lab access).
- Low adoption if no visual dashboard or exportable reports.
- Limited monetization in early phase without premium features.
- Compliance risk if user data is accidentally stored (mitigated by in-memory processing).

TODO: Confirm with lab or HPC admin for real `sacct` CSV sample to validate analysis.