import sys
import os
sys.path.insert(0, 'backend')

import analysis

HDR = "JobID|State|Submit|Start|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"

def job(jid, wait_min, limit):
    start = "2026-11-20T%02d:%02d:00" % (9 + wait_min // 60, wait_min % 60)
    return ("%s|COMPLETED|2026-11-20T09:00:00|%s|00:30:00|%s|1|00:30:00|1G|\n" % (jid, start, limit)
            + "%s.batch|COMPLETED||%s|00:30:00||1|00:30:00||500M\n" % (jid, start))

DATA = HDR + job(1, 5, "01:00:00") + job(2, 15, "00:45:00") + job(3, 120, "08:00:00")

result = analysis.analyze(DATA)
print("Jobs:")
for j in result["jobs"]:
    print(f"  {j['job_id']}: wait_s={j.get('wait_s')}, timelimit_s={j.get('timelimit_s')}")

print("\nSummary:")
summary = result["summary"]
print(f"Wait by limit: {summary.get('wait_by_limit')}")