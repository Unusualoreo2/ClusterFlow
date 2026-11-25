# HPCFlow market and profitability research kit (for Gemini)

How to use it:
1. **Deep Research:** start a new chat, paste the **Context brief** (section 1), then run the prompts in section 2 one at a time.
2. **NotebookLM:** create a notebook "HPCFlow market", add the sources in section 3, then ask the questions listed there.
3. **Before anything goes into `company_plan.md`:** paste Gemini's answer back to Claude with the request "check this against its sources". Treat any number without a working link as unverified.

Ground rules to paste with every prompt (already included below): cite a source for every number, say "unknown" rather than estimate silently, separate facts from estimates.

---

## 1. Context brief (paste this first)

> I am a first-year computer science student in Northern Ireland building a small software product called HPCFlow. Please treat everything below as context for my next questions.
>
> **What HPCFlow does (built and tested):** it reads Slurm job accounting data (`sacct` exports) and shows, per job, per user, per partition and per job array, how much of the requested CPU, memory and time was actually used, how many core-hours were wasted, how long jobs waited in the queue, and the exact resources to request next time (e.g. `--cpus-per-task`, `--mem`, `--time`). It runs as a local web app or as a single-file command-line tool on a cluster login node (Python, standard library only). No job data leaves the cluster. It has an anonymised-report option for sharing.
>
> **What it does not do yet:** GPU efficiency, hardware-counter (Roofline) analysis, history over months, multi-user hosted service.
>
> **Stage:** working prototype, not yet tested on a live cluster (access requested). No users, no revenue, no company registered.
>
> **Goal:** find out whether this can become a business that earns enough to pay my rent, and how.
>
> **Rules for your answers:** give a source link for every number and every claim about a named product or organisation. If something is unknown or you are estimating, say so explicitly. Do not invent survey results, market sizes or prices. Prefer primary sources (vendor pages, papers, official reports) over blogs.

---

## 2. Deep Research prompts (run one at a time)

### 2.1 Who already solves this? (do this first)
> Find existing tools that report Slurm job efficiency (CPU, memory and time used vs requested) or help users right-size their requests. Include open-source tools (for example seff, reportseff, jobstats, Open XDMoD) and commercial products or features of commercial HPC management suites. For each: who makes it, licence and price (if paid), what it shows, whether it gives concrete "request X instead" advice, how widely it is used (with evidence), and its weaknesses. End with a table, and a short list of gaps none of them cover.

### 2.2 How big is the market?
> Estimate the number of Slurm-managed HPC clusters (a) in the UK, (b) in Europe, (c) worldwide, split by universities, national centres, and companies. Then estimate how many research-computing or HPC-support teams exist in UK universities. Use sources like the TOP500 list, Slurm/SchedMD statements, UKRI/EPSRC/DiRAC/ExCALIBUR reports and university research-computing pages. Show each step of the estimate and mark which numbers are sourced and which are assumptions.

### 2.3 How much do clusters waste?
> Find published, citable evidence on how much requested CPU time, memory or wall time on HPC clusters goes unused (for example studies of Slurm accounting data, centre reports, or papers using public job traces). Give the figure, the cluster, the year, the sample size and the link. I need real sources only: if there is no good evidence for a claim, say so.

### 2.4 Who would pay, and how do they buy?
> For UK university HPC services and national facilities, who decides on buying monitoring/analytics software, how is it usually funded (central IT budget, research grants, facility operating budget), and what procurement rules apply to small purchases (for example thresholds below which no tender is needed)? Are there examples of small companies or spin-outs selling HPC tooling to universities? What do HPC centres say they want from efficiency tools?

### 2.5 Pricing and business models
> For niche research-software and HPC tooling, compare business models with real examples and prices: open-source with paid support contracts, open-core (free tool + paid features), per-cluster or per-node annual licences, hosted SaaS, consulting/training, grant-funded development. For each, give examples of companies or projects, their published prices if available, and what revenue a one-person business could realistically expect in years 1-3. Clearly separate evidence from estimates.

### 2.6 Profitability for one founder
> Using the evidence from my previous questions, build a simple break-even model for a one-person software business selling an HPC efficiency tool to UK and European universities. Inputs I will set: monthly rent and living costs = £[FILL IN], hours available per week = [FILL IN] (I am a full-time student). Show: required number of customers at each price point you found, sales-cycle length, likely conversion rates (with sources or marked as assumptions), and the main risks. Then suggest the cheapest way to test whether anyone will pay before building more.

### 2.7 Funding that does not need customers yet
> List UK and EU funding open to a student founder or early-stage research-software project relevant to HPC efficiency: university enterprise/start-up schemes (including at Queen's University Belfast), Invest Northern Ireland programmes, Innovate UK, UKRI/EPSRC research-software or ExCALIBUR calls, student competitions and hackathons with prize money. For each: amount, eligibility, deadline pattern, and link.

---

## 3. NotebookLM notebook "HPCFlow market"

Add as sources (links or PDFs):
- The Slurm `sacct` documentation (slurm.schedmd.com/sacct.html).
- The project pages or papers of the tools Gemini found in 2.1.
- The IN2P3 Computing Center 2024 workload dataset paper (arXiv 2606.05914) and any job-trace studies found in 2.3.
- Your own `docs/architecture.md`, `docs/progress-report.md` and `company_plan.md` from this project.

Ask:
1. "Based only on these sources, what does HPCFlow do that the other tools do not? Quote the sources."
2. "What evidence in these sources shows that wasted HPC resources cost money or research time?"
3. "Which claims in company_plan.md are not supported by any source here?"

---

## 4. What to bring back to Claude

For each prompt, paste Gemini's answer **with its links**. Claude will:
- spot-check the key numbers against their sources,
- mark each claim as verified, unverified or wrong,
- update `company_plan.md` with verified facts only (replacing the current unverified prices: $20/month per lab, $500-2,000/year per site, which came from an early AI draft with no evidence).

Do not paste anyone else's data, usernames or your CIUK teammates' files into Gemini.
