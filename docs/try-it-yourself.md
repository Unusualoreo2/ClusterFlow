# Try ClusterFlow yourself (about 15 minutes)

A hands-on check of everything ClusterFlow does, on this PC, with no cluster needed. Run the commands in PowerShell
from the project folder (`MVP`). All the data here is made up.

Before you start, set this once per PowerShell window so the `£` sign prints correctly:

```powershell
$env:PYTHONIOENCODING = "utf-8"
```

## 1. The report (2 min)

```powershell
.venv\Scripts\python.exe dist\clusterflow.py --demo
```

Check:
- The first line says the data is made up.
- "What to fix first" lists 7 kinds of problem, most common first.
- "Typical jobs" has a "Paste into your job script" block with `#SBATCH` lines.
- Do the numbers make sense? Example: amurphy asks for 32 cores but uses about 10.

## 2. Put a price on the waste (1 min)

```powershell
.venv\Scripts\python.exe dist\clusterflow.py --demo --cpu-hour-cost 0.02 --gpu-hour-cost 0.50
```

Check the "Cost of wasted CPU time" and "Cost of idle GPU time" lines near the top.

## 3. A report to open, print or email (2 min)

```powershell
.venv\Scripts\python.exe dist\clusterflow.py --demo --html demo.html
start demo.html
```

Check: it opens in your browser, and Print preview (Ctrl+P) looks tidy.

## 4. Safe to share (1 min)

```powershell
.venv\Scripts\python.exe dist\clusterflow.py --demo --anonymise
```

Check: no real names (amurphy, jkelly, ...) and no job names appear anywhere: users become user1, user2, ...

## 5. One report per researcher, for HPC teams (2 min)

```powershell
.venv\Scripts\python.exe dist\clusterflow.py --demo --split-by-user reports
start reports\amurphy.html
```

Check: 5 files in `reports`, and amurphy's file shows only amurphy's 8 jobs.

## 6. Show what improved (2 min)

`data\try-it\before.txt` is the demo month; `after.txt` is the same researchers a month later, after following the
advice (made up).

```powershell
.venv\Scripts\python.exe dist\clusterflow.py data\try-it\after.txt --compare data\try-it\before.txt
```

Check the "Change since before" section at the end: CPU efficiency 53% -> 76%, waste per job -70%, no more
out-of-memory or timed-out jobs.

## 7. The web app (3 min)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run.ps1
```

Open http://127.0.0.1:8000 and:
- Click "Try the demo (made-up data)".
- Type a rate into "Price the waste" and watch the cost appear.
- Drop `data\try-it\after.txt` onto the page, then "Download CSV".
Stop it with Ctrl+C.

## 8. Try to break it (as long as you like)

- Give it a file that is not sacct output (any text file): you should get a clear message, not a crash.
- Delete a few columns from `before.txt` in Notepad (keep `JobID` and `State`): you should get a report plus notes saying what is missing.
- Mix `--demo` with a file name: it should refuse politely.

Anything confusing, wrong or ugly: note what you ran and what you expected. That is exactly the feedback to bring back.

## On a real cluster later

Copy the single file `dist\clusterflow.py` to the cluster and run `python3 clusterflow.py` there: it runs `sacct`
itself for your last 7 days. The Kelvin2 pilot steps are in `docs/pilot-guide.md`.
