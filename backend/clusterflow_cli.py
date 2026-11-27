import os
import sys
import argparse
import subprocess
import shutil
import json
import csv
import copy
import html
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analysis import analyze
from analysis import analyze_by_user


def sacct_command(days, all_users=False):
    cmd = ["sacct", "-P", "--units=M", "-S", "now-%ddays" % days,
            "--format=JobID,JobName,User,Partition,State,Submit,Eligible,Start,Elapsed,Timelimit,AllocCPUS,TotalCPU,ReqMem,MaxRSS,AllocTRES,TRESUsageInAve"]
    if all_users:
        cmd.append("-a")
    return cmd


def read_input(args):
    if args.file is not None and args.days is None:
        if args.file == "-":
            return sys.stdin.read()
        else:
            try:
                with open(args.file, 'r', encoding='utf-8-sig') as f:
                    return f.read()
            except FileNotFoundError:
                fail("File not found: " + args.file)
    else:
        cmd = sacct_command(args.days or 7, args.all_users)
        if shutil.which("sacct") is None:
            fail("sacct not found: run this on a Slurm login node, or pass an exported file.")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if result.returncode != 0:
            fail("sacct failed: " + result.stderr.strip())
        return result.stdout


def fail(msg):
    print("clusterflow: " + msg, file=sys.stderr)
    sys.exit(2)


def fmt_wait(s):
    """Seconds -> short human text: None '-', under 60 s '<1m', '30m', '1h 05m', '1d 02h'."""
    if s is None:
        return "-"
    s = int(s)
    if s < 60:
        return "<1m"
    if s < 3600:
        return "%dm" % (s // 60)
    if s < 86400:
        return "%dh %02dm" % (s // 3600, (s % 3600) // 60)
    return "%dd %02dh" % (s // 86400, (s % 86400) // 3600)


def num(v, decimals=1):
    """Number with thousands separators: 195693.24 -> '195,693.2'; None -> '-'."""
    return "-" if v is None else "{:,.{}f}".format(v, decimals)


VERSION = "0.34"

FIX_CATEGORIES = [
    ("request fewer CPUs", lambda r: "--cpus-per-task=" in r),
    ("request less memory", lambda r: r.startswith("Memory efficiency is")),
    ("request a shorter time limit", lambda r: r.startswith("Only ") and "time limit" in r),
    ("request fewer GPUs or check GPU use", lambda r: r.startswith("GPU utilisation is")),
    ("ran out of memory", lambda r: r.startswith("Job ran out of memory")),
    ("hit the time limit", lambda r: r.startswith("Job hit its time limit")),
    ("close to the memory limit", lambda r: r.startswith("Peak memory is")),
    ("mostly waited instead of computing", lambda r: r.startswith("CPU was busy only")),
]


def _demo_sacct():
    """Made-up sample for `--demo`: small, but shows every kind of finding."""
    def job(jid, name, user, part, state, day, wait_min, el, tl, cpus, tot, req, rss, tres="", util=""):
        submit = "2026-11-%02dT09:00:00" % day
        start = "2026-11-%02dT%02d:%02d:00" % (day, 9 + wait_min // 60, wait_min % 60)
        alloc = tres or "billing=%d,cpu=%d,mem=%s,node=1" % (cpus, cpus, req)
        return ("%s|%s|%s|%s|%s|%s|%s|%s|%s|%d|%s|%s||%s|\n"
                % (jid, name, user, part, state, submit, start, el, tl, cpus, tot, req, alloc)
                + "%s.batch|batch|||%s||%s|%s||%d|%s||%s||%s\n" % (jid, state, start, el, cpus, tot, rss, util))

    rows = ["JobID|JobName|User|Partition|State|Submit|Start|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS"
            "|AllocTRES|TRESUsageInAve\n"]
    for i in range(8):
        rows.append(job(4471201 + i, "cfd_mesh", "amurphy", "compute", "COMPLETED", 16 + i % 5, 10 + 25 * i,
                        "03:00:00", "12:00:00", 32, "1-%02d:00:00" % (4 + i % 5), "64G", "%dM" % (9000 + 400 * i)))
    for i in range(4):
        rows.append(job(4471301 + i, "md_run", "jkelly", "compute", "COMPLETED", 16 + i, 60 * i,
                        "11:30:00", "12:00:00", 16, "7-00:00:00", "32G", "31000M"))
    for i in range(2):
        rows.append(job(4471305 + i, "md_run", "jkelly", "compute", "TIMEOUT", 19 + i, 200,
                        "12:00:00", "12:00:00", 16, "7-08:00:00", "32G", "30000M"))
    for i in range(3):
        rows.append(job(4471401 + i, "genome_align", "sdoyle", "himem", "OUT_OF_MEMORY", 17 + i, 30,
                        "00:40:00", "04:00:00", 8, "05:00:00", "16G", "16384M"))
    for i in range(3):
        rows.append(job(4471501 + i, "train_net", "ocallaghan", "gpu", "COMPLETED", 16 + 2 * i, 240,
                        "06:00:00", "08:00:00", 8, "40:00:00", "64G", "50000M",
                        tres="billing=8,cpu=8,gres/gpu=4,mem=64G,node=1",
                        util="cpu=40:00:00,gres/gpuutil=18,mem=50000M"))
    for i in range(12):
        rows.append(job("4472000_%d" % (i + 1), "param_sweep", "rbrennan", "compute", "COMPLETED", 18, 5 * i,
                        "00:20:00", "04:00:00", 4, "00:25:00", "8G", "900M"))
    return "".join(rows)


DEMO_SACCT = _demo_sacct()


def _impact(label, jobs):
    """' (N unit)' for categories with a natural unit, else ''."""
    if label == "request fewer CPUs":
        return " (%s core-hours wasted)" % num(sum(j.get("wasted_core_hours") or 0 for j in jobs))
    if label == "request less memory":
        gbh = sum((j["req_mem_mb"] - j["max_rss_mb"]) / 1024.0 * (j.get("elapsed_s") or 0) / 3600.0
                  for j in jobs if j.get("req_mem_mb") and j.get("max_rss_mb") is not None)
        return " (%s GB-hours of memory unused)" % num(gbh)
    if label == "request fewer GPUs or check GPU use":
        idle = sum((j.get("gpu_hours") or 0) * (1 - j["gpu_utilization"] / 100.0)
                   for j in jobs if j.get("gpu_utilization") is not None)
        return " (%s GPU-hours idle)" % num(idle)
    return ""


def fix_first(jobs):
    """Lines like '2 jobs: request fewer CPUs', most common first (ties keep FIX_CATEGORIES order)."""
    counts = []
    for label, match in FIX_CATEGORIES:
        hit = [j for j in jobs if any(match(r) for r in j["recommendations"])]
        n = len(hit)
        if n:
            counts.append((n, label + _impact(label, hit)))
    counts.sort(key=lambda c: -c[0])
    return ["  %s %s: %s" % (num(n, 0), "job" if n == 1 else "jobs", label) for n, label in counts]


def pct(v):
    return "-" if v is None else "%d%%" % round(v)


def _group_table(title, groups, limit=None):
    """Group table; with a limit, only the first `limit` groups (they arrive sorted by waste)."""
    if limit is not None and len(groups) > limit:
        title = "%s (%d, showing %d)" % (title, len(groups), limit)
        groups = groups[:limit]
    lines = [title, "  %-16s %5s %6s %6s %9s" % ("NAME", "JOBS", "CPU", "MEM", "WASTED")]
    for g in groups:
        lines.append("  %-16s %5d %6s %6s %9.1f" % (
            g["name"], g["job_count"], pct(g["avg_cpu_efficiency"]),
            pct(g["avg_memory_efficiency"]), g["wasted_core_hours"]))
    lines.append("")
    return lines


def report(result, top):
    """Plain-text report: summary, optional group tables, top jobs by waste."""
    summary = result["summary"]
    skipped = result.get("skipped", 0)
    head = "ClusterFlow report: %s %s analysed" % (num(summary["job_count"], 0), "job" if summary["job_count"] == 1 else "jobs")
    if skipped > 0:
        head += " (%d running/pending skipped)" % skipped
    lines = [
        head,
        "Avg CPU efficiency:    %s" % pct(summary["avg_cpu_efficiency"]),
        "Avg memory efficiency: %s" % pct(summary["avg_memory_efficiency"]),
        "Wasted core-hours:     %s" % ("-" if summary["total_wasted_core_hours"] is None
                                        else num(summary["total_wasted_core_hours"])),
    ]
    if result.get("cluster"):
        c = result["cluster"]
        lines.insert(3, "Cluster average:       CPU %s, memory %s (%d users)"
                     % (pct(c["avg_cpu_efficiency"]), pct(c["avg_memory_efficiency"]), c["users"]))
    if summary.get("avg_wait_s") is not None:
        lines.append("Avg queue wait:        %s" % fmt_wait(summary["avg_wait_s"]))
        lines.append("Max queue wait:        %s" % fmt_wait(summary["max_wait_s"]))
        if summary.get("wait_from") == "Eligible":
            lines.append("Queue wait from:      eligible time (holds and dependencies not counted)")
        else:
            lines.append("Queue wait from:      submit time (export Eligible to leave out holds and dependencies)")
    if summary.get("gpu_job_count"):
        lines.append("GPU jobs:              %s" % num(summary["gpu_job_count"], 0))
        lines.append("GPU-hours:             %s" % ("-" if summary["total_gpu_hours"] is None
                                                    else num(summary["total_gpu_hours"])))
        lines.append("Avg GPU utilisation:   %s" % pct(summary["avg_gpu_utilization"]))
    cost = result.get("cost")
    if cost:
        cur = cost["currency"]
        if cost["wasted_cpu_cost"] is not None:
            lines.append("Cost of wasted CPU time:  %s (at %s per core-hour)"
                         % (_money(cur, cost["wasted_cpu_cost"]), _rate(cur, cost["cpu_rate"])))
        if cost["idle_gpu_cost"] is not None:
            lines.append("Cost of idle GPU time:    %s (at %s per GPU-hour)"
                         % (_money(cur, cost["idle_gpu_cost"]), _rate(cur, cost["gpu_rate"])))
    dq = summary.get("data_quality")
    if dq and dq["jobs"]:
        lines.append("Usable figures:        CPU %d%%, memory %d%%, time %d%% of jobs" % (
            round(100.0 * dq["cpu"] / dq["jobs"]), round(100.0 * dq["memory"] / dq["jobs"]),
            round(100.0 * dq["time"] / dq["jobs"])))
    for w in result.get("warnings", []):
        lines.append("Note: " + w)
    lines.append("")
    fixes = fix_first(result["jobs"])
    if fixes:
        lines += ["What to fix first"] + fixes + [""]
    if summary.get("by_user"):
        lines += _group_table("By user", summary["by_user"], top)
    if summary.get("by_partition"):
        lines += _group_table("By partition", summary["by_partition"], top)
    trend = summary.get("trend") or {"period": None, "rows": []}
    if len(trend["rows"]) >= 2:
        lines += _group_table("Trend by %s" % trend["period"], trend["rows"])
    bands = summary.get("wait_by_limit") or []
    if len(bands) >= 2:
        lines.append("Queue wait by time limit")
        for b in bands:
            lines.append("  %-12s %8s %-4s  median %-8s 90%% within %s" % (b["label"], num(b["jobs"], 0), "job" if b["jobs"] == 1 else "jobs",
                                                     fmt_wait(b["median_wait_s"]), fmt_wait(b["p90_wait_s"])))
        if bands[-1]["p90_wait_s"] > bands[0]["p90_wait_s"]:
            lines.append("  Longer limits waited longer here (90% mark): shorter limits can start sooner via Slurm backfill. Not a promise.")
        else:
            lines.append("  Waits did not grow with the time limit on this data.")
        lines.append("")
    profiles = [p for p in summary.get("profiles", []) if p["recommendations"]][:max(0, top)]
    if profiles:
        lines.append("Typical jobs (sized from repeated runs)")
        for p in profiles:
            lines.append("  %s / %s (%d runs)" % (p["user"] or "-", p["name"], p["runs"]))
            for rec in p["recommendations"]:
                lines.append("    - " + rec)
            if p.get("sbatch"):
                lines.append("    Paste into your job script:")
                for s in p["sbatch"]:
                    lines.append("      " + s)
        lines.append("")
    arrays = summary.get("arrays", [])
    if arrays:
        shown = arrays[:max(0, top)]
        title = "Job arrays (%d)" % len(arrays)
        if len(shown) < len(arrays):
            title = "Job arrays (%d, showing %d)" % (len(arrays), len(shown))
        lines.append(title)
        for r in shown:
            states = ", ".join("%d %s" % (n, s) for s, n in sorted(r["states"].items(), key=lambda kv: (-kv[1], kv[0])))
            lines.append("  %s  %s  %d tasks (%s)  CPU %s  MEM %s  WASTED %.1f" % (
                r["array_id"], r["name"], r["task_count"], states, pct(r["avg_cpu_efficiency"]),
                pct(r["avg_memory_efficiency"]), r["wasted_core_hours"] or 0))
            for rec in r["recommendations"]:
                lines.append("    - " + rec)
        lines.append("")

    jobs = sorted(result["jobs"], key=lambda j: -(j["wasted_core_hours"] or 0))[:max(0, top)]
    lines.append("Top %d %s by wasted core-hours" % (len(jobs), "job" if len(jobs) == 1 else "jobs"))
    for j in jobs:
        wasted = "-" if j["wasted_core_hours"] is None else "%.1f" % j["wasted_core_hours"]
        lines.append("  %s  %s  CPU %s  MEM %s  TIME %s  WASTED %s" % (
            j["job_id"], j["name"] or "-", pct(j["cpu_efficiency"]), pct(j["memory_efficiency"]),
            pct(j["time_used"]), wasted))
        for rec in j["recommendations"]:
            lines.append("    - " + rec)
    if result.get("comparison"):
        lines += [""] + comparison_lines(result["comparison"])
    return "\n".join(lines)


def html_report(result, top, banner=None):
    """Return a complete self-contained HTML page for the report."""
    text = report(result, top)
    lines = text.split("\n")
    
    # Extract header lines before first empty line
    head_lines = []
    i = 0
    while i < len(lines) and lines[i].strip():
        head_lines.append(lines[i])
        i += 1
    
    # Build the head section
    head = []
    summary_rows = []
    
    for line in head_lines:
        if line.startswith("Note: "):
            head.append('<p class="note">%s</p>' % html.escape(line[6:]))
        elif ":" in line and not line.startswith("ClusterFlow report:"):
            label, value = line.split(":", 1)
            summary_rows.append('<tr><th>%s</th><td>%s</td></tr>' % (html.escape(label.strip()), html.escape(value.strip())))
        else:
            head.append('<h1>%s</h1>' % html.escape(line))
    
    # Add banner if provided
    if banner:
        head.insert(0, '<p class="banner">%s</p>' % html.escape(banner))
    
    # Build fixes section
    fixes = fix_first(result["jobs"])
    fixes_html = ""
    if fixes:
        fixes_html = '<h2>What to fix first</h2><ul class="fix-first">'
        for fix in fixes:
            fixes_html += '<li>%s</li>' % html.escape(fix.strip())
        fixes_html += '</ul>'
    
    # Build details section
    rest = lines[i + 1:]
    if rest and rest[0] == "What to fix first":
        end = rest.index("") if "" in rest else len(rest)
        rest = rest[end + 1:]
    details_lines = rest
    
    details_html = ""
    if details_lines:
        details_html = '<h2>Details</h2><pre>%s</pre>' % html.escape("\n".join(details_lines))
    
    # Build the complete HTML page
    html_content = ("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>ClusterFlow report</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 60rem; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; background: #fff; }
table.summary { border-collapse: collapse; margin: 1rem 0; }
table.summary th { text-align: left; padding: .25rem 1.5rem .25rem 0; font-weight: 600; }
table.summary td { padding: .25rem 0; }
.banner { background: #fff4d6; padding: .5rem .75rem; border-radius: 4px; }
.note { color: #6b4e00; }
pre { background: #f5f5f5; padding: 1rem; overflow-x: auto; font-size: .85rem; }
@media print { body { margin: 0; max-width: none; } pre { white-space: pre-wrap; background: none; } }
</style>
</head>
<body>
%s
%s
%s
<p class="footer">Generated by ClusterFlow """ + VERSION + """. Nothing in this file was sent anywhere.</p>
</body>
</html>""") % ("\n".join(head), '<table class="summary">%s</table>' % "\n".join(summary_rows) if summary_rows else "", fixes_html + details_html)
    
    return html_content


def comparison_metrics(result):
    """Headline numbers used to compare two periods."""
    s = result["summary"]
    n = s["job_count"]
    waste = s["total_wasted_core_hours"]
    return {
        "job_count": n,
        "avg_cpu_efficiency": s["avg_cpu_efficiency"],
        "avg_memory_efficiency": s["avg_memory_efficiency"],
        "wasted_core_hours_per_job": waste / n if (waste is not None and n) else None,
        "oom_jobs": sum(1 for j in result["jobs"] if j["state"].startswith("OUT_OF_MEMORY")),
        "timeout_jobs": sum(1 for j in result["jobs"] if j["state"].startswith("TIMEOUT")),
    }


def comparison_lines(comparison):
    """'Change since before' section for the text report."""
    b, a = comparison["before"], comparison["after"]
    lines = ["Change since before (%s jobs -> %s jobs)" % (num(b["job_count"], 0), num(a["job_count"], 0))]

    def row(label, value):
        lines.append("  %-27s %s" % (label, value))

    for label, key in (("Avg CPU efficiency:", "avg_cpu_efficiency"), ("Avg memory efficiency:", "avg_memory_efficiency")):
        value = "%s -> %s" % (pct(b[key]), pct(a[key]))
        if b[key] is not None and a[key] is not None:
            points = round(a[key]) - round(b[key])
            value += " (no change)" if points == 0 else " (%+d points)" % points
        row(label, value)
    bw, aw = b["wasted_core_hours_per_job"], a["wasted_core_hours_per_job"]
    value = "%s -> %s" % ("-" if bw is None else "%.1f" % bw, "-" if aw is None else "%.1f" % aw)
    if bw is not None and aw is not None and bw > 0:
        value += " (%+d%%)" % round((aw - bw) / bw * 100)
    row("Wasted core-hours per job:", value)
    row("Out-of-memory jobs:", "%d -> %d" % (b["oom_jobs"], a["oom_jobs"]))
    row("Timed-out jobs:", "%d -> %d" % (b["timeout_jobs"], a["timeout_jobs"]))
    return lines


def write_csv(result, path):
    """Write every analysed job to a CSV file, with the raw figures behind each verdict at the end."""
    def num(v):
        return "" if v is None else round(v, 1)

    def whole(v):
        return "" if v is None else int(round(v))

    def text(v):
        # Stop spreadsheets running cell text as a formula (same rule as the web page's CSV)
        v = "" if v is None else str(v)
        return "'" + v if v[:1] in ("=", "+", "-", "@") else v

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["job_id", "name", "state", "user", "partition", "cpu_efficiency",
                    "memory_efficiency", "time_used", "wasted_core_hours", "recommendations",
                    "alloc_cpus", "mem_requested_mb", "mem_used_mb", "elapsed_s", "time_limit_s",
                    "queue_wait_s", "alloc_gpus", "gpu_hours"])
        for j in result["jobs"]:
            w.writerow([text(j["job_id"]), text(j["name"]), text(j["state"]), text(j.get("user", "")),
                        text(j.get("partition", "")),
                        num(j["cpu_efficiency"]), num(j["memory_efficiency"]), num(j["time_used"]),
                        num(j["wasted_core_hours"]), text(" | ".join(j["recommendations"])),
                        whole(j.get("alloc_cpus")), whole(j.get("req_mem_mb")), whole(j.get("max_rss_mb")),
                        whole(j.get("elapsed_s")), whole(j.get("timelimit_s")), whole(j.get("wait_s")),
                        whole(j.get("alloc_gpus")), num(j.get("gpu_hours"))])


def estimate_cost(summary, cpu_rate, gpu_rate, currency="£"):
    """Price wasted CPU time and idle GPU time at the user's own rates. None if no rate is given."""
    if cpu_rate is None and gpu_rate is None:
        return None
    wasted = summary.get("total_wasted_core_hours")
    idle = summary.get("idle_gpu_hours")
    return {
        "currency": currency,
        "cpu_rate": cpu_rate,
        "gpu_rate": gpu_rate,
        "wasted_cpu_cost": wasted * cpu_rate if cpu_rate is not None and wasted is not None else None,
        "idle_gpu_cost": idle * gpu_rate if gpu_rate is not None and idle is not None else None,
    }


def _money(currency, value):
    return "%s{:,.2f}".format(value) % currency


def _rate(currency, value):
    return "%s%s" % (currency, ("%.2f" % value) if round(value, 2) == value else ("%g" % value))


def anonymise(result):
    """Copy of an analyze() result with users, job names and job IDs replaced by user1/job1/J1 labels.
    Same value -> same label, numbered in order of first appearance in result["jobs"].
    Empty users stay empty and the "(unknown)" group stays as it is. Partitions and numbers are kept.
    Typical-job profiles and job arrays are relabelled too."""
    out = copy.deepcopy(result)
    users, names, ids = {}, {}, {}

    def label(table, value, prefix):
        if value not in table:
            table[value] = "%s%d" % (prefix, len(table) + 1)
        return table[value]

    for j in out["jobs"]:
        if j.get("user"):
            j["user"] = label(users, j["user"], "user")
        j["name"] = label(names, j.get("name", ""), "job")
        j["job_id"] = label(ids, j.get("job_id", ""), "J")
    arrays = {}
    for r in out.get("summary", {}).get("arrays", []):
        r["array_id"] = label(arrays, r["array_id"], "A")
        r["name"] = label(names, r.get("name", ""), "job")
        if r.get("user"):
            r["user"] = label(users, r["user"], "user")
    for j in out["jobs"]:
        if j.get("array_id"):
            j["array_id"] = label(arrays, j["array_id"], "A")
    for p in out.get("summary", {}).get("profiles", []):
        if p.get("user"):
            p["user"] = label(users, p["user"], "user")
        p["name"] = label(names, p.get("name", ""), "job")
    for g in out.get("summary", {}).get("by_user", []):
        if g["name"] != "(unknown)":
            g["name"] = label(users, g["name"], "user")
    return out


def _user_file(user):
    """Safe file name for a user's report; never 'index.html' (the overview)."""
    base = re.sub(r"[^A-Za-z0-9._-]", "_", user)
    return ("index_user" if base == "index" else base) + ".html"


def users_index_html(per_user, cluster):
    """Overview page: one row per user, most wasted core-hours first, linking to each report."""
    rows = sorted(per_user.items(), key=lambda kv: (-(kv[1]["summary"]["total_wasted_core_hours"] or 0), kv[0]))
    body = []
    for u, r in rows:
        s = r["summary"]
        body.append('<tr><td><a href="%s">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            html.escape(_user_file(u)), html.escape(u), num(s["job_count"], 0), pct(s["avg_cpu_efficiency"]),
            pct(s["avg_memory_efficiency"]), num(s["total_wasted_core_hours"])))
    return ("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>ClusterFlow per-user reports</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 60rem; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; background: #fff; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: .3rem .75rem .3rem 0; border-bottom: 1px solid #e5e5e5; }
</style>
</head>
<body>
<h1>ClusterFlow per-user reports</h1>
<p>Cluster average: """ + html.escape("CPU %s, memory %s (%d users)" % (pct(cluster["avg_cpu_efficiency"]),
                                                                     pct(cluster["avg_memory_efficiency"]), cluster["users"])) + """</p>
<table>
<tr><th>User</th><th>Jobs</th><th>CPU</th><th>Memory</th><th>Wasted core-hours</th></tr>
""" + "\n".join(body) + """
</table>
<p class="footer">Generated by ClusterFlow """ + VERSION + """. Nothing in this file was sent anywhere.</p>
</body>
</html>""")


def write_user_reports(text, args, cluster_summary):
    """One HTML report per non-empty user in DIR, each covering only that user's jobs (text parsed once)."""
    per_user = analyze_by_user(text)
    try:
        os.makedirs(args.split_by_user, exist_ok=True)
        cluster = {"avg_cpu_efficiency": cluster_summary["avg_cpu_efficiency"],
                    "avg_memory_efficiency": cluster_summary["avg_memory_efficiency"], "users": len(per_user)}
        for u, result in per_user.items():
            result["cluster"] = cluster
            cost = estimate_cost(result["summary"], args.cpu_hour_cost, args.gpu_hour_cost, args.currency)
            if cost:
                result["cost"] = cost
            name = _user_file(u)
            with open(os.path.join(args.split_by_user, name), "w", encoding="utf-8") as f:
                f.write(html_report(result, args.top, "Report for %s" % u))
    except OSError as e:
        fail("cannot write per-user reports: %s" % e)
    try:
        with open(os.path.join(args.split_by_user, "index.html"), "w", encoding="utf-8") as f:
            f.write(users_index_html(per_user, cluster))
    except OSError as e:
        fail("cannot write the overview page: %s" % e)
    print("clusterflow: wrote %d per-user reports to %s" % (len(per_user), args.split_by_user), file=sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="clusterflow",
        description="Shows how much of their Slurm requests your jobs actually used, and what to request next time.",
        epilog="Examples:\n"
               "  python3 clusterflow.py --demo                     see a report on made-up data\n"
               "  python3 clusterflow.py                            your jobs of the last 7 days\n"
               "  python3 clusterflow.py jobs.txt --html report.html\n"
               "  python3 clusterflow.py --all-users --split-by-user reports/   (admins)",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version="clusterflow " + VERSION)
    parser.add_argument("file", nargs="?", default=None, help="path to a sacct export, or '-' for stdin")
    parser.add_argument("--days", type=int, metavar="N", help="ignore FILE and run sacct for the last N days (default when FILE is omitted: 7 days)")
    parser.add_argument("--all-users", action="store_true", help="add '-a' to sacct (admins)")
    parser.add_argument("--top", type=int, default=5, metavar="N", help="how many jobs to list (default 5)")
    parser.add_argument("--json", action="store_true", help="print the full analysis as JSON instead of the text report")
    parser.add_argument("--csv", metavar="PATH", help="also write a CSV report to PATH")
    parser.add_argument("--html", metavar="PATH", help="also write a self-contained HTML report to PATH (open, print or email it)")
    parser.add_argument("--split-by-user", metavar="DIR",
                        help="also write one HTML report per user into DIR (to send each researcher their own)")
    parser.add_argument("--compare", metavar="BEFORE", help="also analyse an earlier sacct export and show what changed since then")
    parser.add_argument("--anonymise", "--anonymize", action="store_true",
                        help="replace user names, job names and job IDs with neutral labels (safe to share)")
    parser.add_argument("--cpu-hour-cost", type=float, default=None, metavar="RATE",
                         help="your centre's price per core-hour, to show what wasted CPU time costs")
    parser.add_argument("--gpu-hour-cost", type=float, default=None, metavar="RATE",
                         help="your centre's price per GPU-hour, to show what idle GPU time costs")
    parser.add_argument("--currency", default="£", metavar="SYMBOL", help="currency symbol for costs (default: £)")
    parser.add_argument("--demo", action="store_true", help="analyse a built-in sample (made-up data) to see what the report looks like")

    args = parser.parse_args(argv)

    if args.split_by_user and args.anonymise:
        fail("--split-by-user writes each user's own report: it cannot be combined with --anonymise")
    if args.demo and (args.file is not None or args.days is not None):
        fail("--demo uses built-in sample data: do not also give a file or --days")
    text = DEMO_SACCT if args.demo else read_input(args)
    try:
        result = analyze(text)
    except ValueError as e:
        fail(str(e))

    if args.anonymise:
        result = anonymise(result)
    for rate in (args.cpu_hour_cost, args.gpu_hour_cost):
        if rate is not None and rate < 0:
            fail("cost rates must be zero or positive")
    cost = estimate_cost(result["summary"], args.cpu_hour_cost, args.gpu_hour_cost, args.currency)
    if cost:
        result["cost"] = cost
    if args.compare:
        try:
            with open(args.compare, "r", encoding="utf-8-sig") as f:
                before = analyze(f.read())
        except OSError as e:
            fail("cannot read %s: %s" % (args.compare, e))
        except ValueError as e:
            fail("%s: %s" % (args.compare, e))
        result["comparison"] = {"before": comparison_metrics(before), "after": comparison_metrics(result)}
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if args.demo:
            print("Demo: built-in sample data (made up for illustration, not from a real cluster)")
        print(report(result, args.top))

    if args.csv:
        write_csv(result, args.csv)
    if args.html:
        banner = "Demo: built-in sample data (made up for illustration, not from a real cluster)" if args.demo else None
        try:
            with open(args.html, "w", encoding="utf-8") as f:
                f.write(html_report(result, args.top, banner))
        except OSError as e:
            fail("cannot write HTML report: %s" % e)
    if args.split_by_user:
        write_user_reports(text, args, result["summary"])

    return 0


if __name__ == "__main__":
    sys.exit(main())