# HPCFlow - Company Plan

Last updated 25 Nov 2026. Every statistic below is verified against its source (see `docs/market-research-verified.md`); estimates and proposals are labelled as such.

## Overview
HPCFlow is a Slurm job efficiency analyser. It reads `sacct` accounting data and shows, per job, user, partition, job array and day/week, how much of the requested CPU, memory, GPU and time was actually used, how many core-hours and GPU-hours were wasted, what that waste costs at the centre's own rates, and exactly what to request next time. It runs as a single-file command-line tool on a cluster login node (Python standard library only, nothing leaves the cluster) and as a local web app.

## Problem
Researchers routinely request far more than their jobs use, which blocks the queue for everyone and wastes funded compute:
- At the IN2P3 Computing Center (CNRS, France), across 44.7M jobs in 2024, **the median completed job used about 10% of the time limit it requested** (above 20% when weighted by job duration). On its main partition, 69% of CPU time was allocated but only 41% was actually used. ([arXiv 2606.05914](https://arxiv.org/html/2606.05914), Sections 2.1 and 7.4)
- Turning historical usage into conservative recommendations can cut the walltime gap by **about 20-26% while keeping job terminations under 1%**. ([arXiv 2610.27755](https://arxiv.org/pdf/2610.27755))

Existing tools either report percentages without telling users what to request (e.g. `seff`, `reportseff`), or need cluster-wide installation by administrators (e.g. Open XDMoD, jobstats with Prometheus, ClusterCockpit). *(Competitor descriptions are from Gemini research and mostly not yet individually verified.)*

## Product
Status: v0.11 built and tested (610 automated tests; backed up to a private GitHub repository). Not yet run on a live cluster.

- CPU, memory and time efficiency; wasted core-hours; queue wait; per-user, per-partition, per-array and day/week trend summaries.
- GPU-hours, GPU utilisation (where the cluster records it) and idle-GPU advice.
- Concrete advice: the `--cpus-per-task`, `--mem`, `--time` and `--gpus` values to request next time; out-of-memory and timeout jobs flagged.
- Cost of waste at the centre's own `£/core-hour` and `£/GPU-hour` rates (HPCFlow never invents prices).
- Reads real-world exports (tab/pipe/comma, partial columns with plain-English notes); `--anonymise` for shareable reports.
- Accuracy note: the **command-line tool has no dependencies**; the **web app needs FastAPI/uvicorn**.

Not built yet: Roofline / code-level advice (needs hardware-counter data such as `likwid`), a hosted multi-user version.

## Target Customers
1. **University research-computing / HPC support teams** (buyers): fewer wasted core-hours, shorter queues, fewer support tickets. First target: QUB / NIHPC (Kelvin2).
2. **Researchers and students** (users): faster-starting jobs, less trial and error.
3. Later: national and regional facilities (e.g. DiRAC, UKRI Tier-2 services) and industry HPC teams.

## Revenue Model (hypotheses to test)
- **Free, open command-line tool** to build adoption among researchers.
- **Paid site licence per cluster** for the team features (multi-user summaries, trends, cost reports, support). *Proposal:* £1,500-£4,500 per cluster per year, chosen to stay under the discretionary spending limit at universities such as Huddersfield (under £5,000 needs no formal quotes). This is untested: other universities set different thresholds, and no buyer has been asked yet.
- **Non-dilutive funding first**: QUB student enterprise schemes (to check), then Invest NI Innovation Vouchers (**£5,000**, requires a registered business) or Innovate UK once incorporated.
- Replaced: the earlier draft prices ($20/month per lab, $500-$2,000/year per site) had no evidence behind them.

## Break-even (estimate)
With living and business costs of roughly £6,000-£11,000 a year *(the founder's own figures to confirm)*, about **2-4 site licences** at the proposed price would break even. University sales cycles are likely several months, so funding and pilots come first.

## Next Steps
1. **Kelvin2 pilot** (access requested): run `docs/pilot-guide.md` and confirm HPCFlow's advice on real jobs.
2. **Validation conversations**: offer QUB/NIHPC and 5-10 other UK research-computing teams a free, anonymised waste report; ask whether they would pay for a site licence.
3. **Apply for QUB student enterprise support** (confirm current schemes and amounts first).
4. Turn on automated testing on GitHub; build and test the Docker image.

## Risks
- **Free alternatives** (`seff`, `reportseff`, jobstats): HPCFlow must show clear extra value (exact advice, cost, zero install).
- **No live-cluster validation yet**: edge cases in real accounting data may remain.
- **Solo student founder**: limited time in term and exams; university procurement and support expectations.
- **Data protection**: `sacct` data contains usernames; HPCFlow keeps data on the cluster and offers `--anonymise`, but each centre's rules apply.
