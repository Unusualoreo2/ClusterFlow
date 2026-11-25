# HPCFlow User Guide

As an HPC user, you can improve your job efficiency by analyzing sacct exports.

## Export jobs

Run this command to export your jobs:
```
sacct -P --units=M -S now-7days --format=JobID,JobName,User,Partition,State,Submit,Start,Elapsed,Timelimit,AllocCPUS,TotalCPU,ReqMem,MaxRSS,AllocTRES,TRESUsageInAve > jobs.txt
```

Do not add `-X`: memory usage is recorded on the job steps, and HPCFlow merges them into each job automatically. Change `now-7days` to cover a different period.

## If some figures are missing

If your export lacks some columns, HPCFlow still analyses it and shows a yellow note listing what is not available (for example "TotalCPU column missing: CPU efficiency is not available"). Re-export with the full command above to get every figure.

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

## By user and by partition

If your export includes the User and Partition columns, HPCFlow also shows two small tables: one row per user and one row per partition, with the number of jobs, average CPU and memory efficiency, and wasted core-hours. The rows with the most wasted core-hours come first, so you can see where resources are lost.

## Queue wait

The "Avg queue wait" card and the "Queue wait" column show how long jobs waited between submission and start (for example "45m" or "1d 02h"). Long waits often mean the job asked for more CPUs, memory or time than the scheduler could find quickly: requesting what the job really needs usually starts it sooner.

## GPU jobs

If you used GPUs, the "GPU-hours" card shows how many GPU-hours your jobs held and, when your cluster records it, how busy the GPUs were on average. A job that kept GPUs mostly idle gets advice such as "request --gpus=1 instead". GPUs are usually the most expensive resource on a cluster, so this is often the biggest saving.

## Recommendations

HPCFlow suggests how to improve your next job:

- If CPU efficiency is low (under 50%), request fewer CPUs (HPCFlow gives the number) or check that your code really runs in parallel.
- If memory efficiency is low (under 50%), request less memory next time: HPCFlow gives the exact --mem value.
- If memory efficiency is high (>90%), warn that the job is near its limit.
- If time used is low, suggest a shorter time limit.
- If a job ran out of memory or timed out, suggest more resources.