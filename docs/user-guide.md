# HPCFlow User Guide

As an HPC user, you can improve your job efficiency by analyzing sacct exports.

## Export jobs

Run this command to export your jobs:
```
sacct -P --units=M -S now-7days --format=JobID,JobName,State,Elapsed,Timelimit,AllocCPUS,TotalCPU,ReqMem,MaxRSS > jobs.txt
```

Do not add `-X`: memory usage is recorded on the job steps, and HPCFlow merges them into each job automatically. Change `now-7days` to cover a different period.

## Upload or paste

You can upload a sacct file or paste its contents directly in the web interface.

## Read the results

Each job shows metrics and recommendations:

- **CPU %**: share of the allocated CPU time your job really used.
- **Memory %**: peak memory used as a share of the memory you requested.
- **Time used %**: run time as a share of the time limit (shown with a neutral blue bar).
- **Wasted core-h**: core-hours that were allocated but not used.

Colours of the CPU and memory bars:
- < 50%: red
- 50-79%: amber
- >= 80%: green

## Recommendations

HPCFlow suggests how to improve your next job:

- If CPU efficiency is low (under 50%), request fewer CPUs (HPCFlow gives the number) or check that your code really runs in parallel.
- If memory efficiency is low (under 50%), request less memory next time: HPCFlow gives the exact --mem value.
- If memory efficiency is high (>90%), warn that the job is near its limit.
- If time used is low, suggest a shorter time limit.
- If a job ran out of memory or timed out, suggest more resources.