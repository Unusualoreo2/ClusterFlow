# Market research: verification record (25 Nov 2026)

Source: "HPCFlow Market & Profitability Research Compilation", produced with Gemini from `docs/market-research-kit.md`. Its links were lost in copy-paste, so the key claims were re-checked by Claude against primary sources. Only claims marked **Verified** may be quoted as fact in `company_plan.md`.

| # | Claim in the Gemini report | Status | Evidence |
|---|---|---|---|
| 1 | IN2P3 (CNRS) 2024: median completed job uses ~10% of its requested time limit | **Verified**, with conditions | Paper Section 7.4: "the median usage of allocated time for completed jobs is equal to around 10% of the time limit requested". Completed jobs only, excluding the `htc_daemon` partition; weighted by job duration the median is above 20%. 44.7M jobs, 945 users, up to 312 machines. [arXiv 2606.05914](https://arxiv.org/html/2606.05914) |
| 1b | (Found during checking) IN2P3 main partition: 69% of CPU time allocated, 41% used | **Verified** | Same paper, Section 2.1. |
| 2 | Walltime prediction with conservative margins cuts the walltime gap 20-26% with <1% job terminations | **Verified** (abstract) | [arXiv 2610.27755](https://arxiv.org/pdf/2610.27755). A conference version reports ~32% on Fugaku and NREL Eagle data; quote 20-26% as the conservative figure. |
| 3 | reportseff needs an external package (`click`) | **Verified** | [Princeton jobstats docs: reportseff](https://princetonuniversity.github.io/jobstats/tools/reportseff), [github.com/troycomi/reportseff](https://github.com/troycomi/reportseff) |
| 4 | University of Huddersfield: under £5,000 at budget holder's discretion; three written quotes £5,001-£50,000 | **Verified for Huddersfield only** | [Huddersfield Tendering Procedure 2024](https://staff-t4.hud.ac.uk/media/universityofhuddersfield/content2013/services/finance/procurement/TenderingProcedure-2024.docx). The document still cites the pre-2023 regulations; other universities set their own thresholds. |
| 5 | "52% of institutions set single-quote thresholds at £5k or £10k" (SUPC review) | **Not verified** | Source not found. Do not quote. |
| 6 | Invest NI Innovation Vouchers "up to £10,000" | **Wrong** | The January 2026 call offered **£5,000** vouchers, for registered businesses, to buy expertise from universities/colleges. [nibusinessinfo: January 2026 call](https://www.nibusinessinfo.co.uk/content/innovation-vouchers-january-2026-call) |
| 7 | Slurm runs on ~60% of TOP500 systems | Not checked (Gemini cited Wikipedia) | Quote only with a primary source. |
| 8 | Perlmutter: mean peak GPU memory use 28.64% | Not verified | Gemini itself flagged it as a secondary vendor blog. Do not quote. |
| 9 | Market sizes (60-100 UK university clusters, 2,000-4,000+ worldwide, team counts) | **Estimates** | Gemini's own explicit estimates; no source. Use only as assumptions. |
| 10 | Competitor descriptions (seff, jobstats, Open XDMoD, ClusterCockpit, commercial suites) | Mostly plausible, not individually verified | Only reportseff checked (row 3). |
| 11 | "HPCFlow is zero-dependency, user-space web UI and CLI" | **Partly wrong** | The CLI (`dist/hpcflow.py`) is standard-library only. The **web app needs FastAPI/uvicorn**. Correct this before using it in any pitch. |
| 12 | "No surveyed tool offers anonymised export" | Not verified | A claim of absence; check before using it as a selling point. |
| 13 | Pricing £1,500-£4,500/year per cluster | **Strategy proposal, not a fact** | Reasonable given row 4, but untested with any buyer. |
| 14 | Break-even: 2-4 site licences at Belfast living costs | **Estimate** | Depends on the user's real costs and on row 13. |
| 15 | QUB InQUBate / student competitions (£3,000, €2,000 prizes) | Not verified | Check current QUB pages before applying. |

## Conclusions safe to act on

- The waste problem is real and documented at a large production Slurm centre (row 1, 1b), and recommendation layers can recover a meaningful share of it (row 2).
- HPCFlow's differentiator (exact `--cpus-per-task` / `--mem` / `--time` advice from plain `sacct`, CLI with no dependencies, nothing leaving the cluster) is plausible but must be confirmed by talking to HPC teams.
- Pricing below a university's discretionary threshold is a sensible hypothesis; it needs testing with real buyers (QUB/NIHPC first).
