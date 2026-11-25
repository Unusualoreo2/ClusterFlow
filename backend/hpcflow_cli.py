import os
import sys
import argparse
import subprocess
import shutil
import json
import csv
import copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analysis import analyze


def sacct_command(days, all_users=False):
    cmd = ["sacct", "-P", "--units=M", "-S", "now-%ddays" % days,
            "--format=JobID,JobName,User,Partition,State,Submit,Start,Elapsed,Timelimit,AllocCPUS,TotalCPU,ReqMem,MaxRSS,AllocTRES,TRESUsageInAve"]
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
    print("hpcflow: " + msg, file=sys.stderr)
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


def pct(v):
    return "-" if v is None else "%d%%" % round(v)


def _group_table(title, groups):
    """Text table for summary["by_user"] / summary["by_partition"]."""
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
    head = "HPCFlow report: %d jobs analysed" % summary["job_count"]
    if skipped > 0:
        head += " (%d running/pending skipped)" % skipped
    lines = [
        head,
        "Avg CPU efficiency:    %s" % pct(summary["avg_cpu_efficiency"]),
        "Avg memory efficiency: %s" % pct(summary["avg_memory_efficiency"]),
        "Wasted core-hours:     %s" % ("-" if summary["total_wasted_core_hours"] is None
                                        else "%.1f" % summary["total_wasted_core_hours"]),
    ]
    if summary.get("avg_wait_s") is not None:
        lines.append("Avg queue wait:        %s" % fmt_wait(summary["avg_wait_s"]))
        lines.append("Max queue wait:        %s" % fmt_wait(summary["max_wait_s"]))
    if summary.get("gpu_job_count"):
        lines.append("GPU jobs:              %d" % summary["gpu_job_count"])
        lines.append("GPU-hours:             %s" % ("-" if summary["total_gpu_hours"] is None
                                                    else "%.1f" % summary["total_gpu_hours"]))
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
    for w in result.get("warnings", []):
        lines.append("Note: " + w)
    lines.append("")
    if summary.get("by_user"):
        lines += _group_table("By user", summary["by_user"])
    if summary.get("by_partition"):
        lines += _group_table("By partition", summary["by_partition"])
    trend = summary.get("trend") or {"period": None, "rows": []}
    if len(trend["rows"]) >= 2:
        lines += _group_table("Trend by %s" % trend["period"], trend["rows"])
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
    lines.append("Top %d jobs by wasted core-hours" % len(jobs))
    for j in jobs:
        wasted = "-" if j["wasted_core_hours"] is None else "%.1f" % j["wasted_core_hours"]
        lines.append("  %s  %s  CPU %s  MEM %s  TIME %s  WASTED %s" % (
            j["job_id"], j["name"], pct(j["cpu_efficiency"]), pct(j["memory_efficiency"]),
            pct(j["time_used"]), wasted))
        for rec in j["recommendations"]:
            lines.append("    - " + rec)
    return "\n".join(lines)


def write_csv(result, path):
    """Write every analysed job to a CSV file."""
    def num(v):
        return "" if v is None else round(v, 1)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["job_id", "name", "state", "user", "partition", "cpu_efficiency",
                    "memory_efficiency", "time_used", "wasted_core_hours", "recommendations"])
        for j in result["jobs"]:
            w.writerow([j["job_id"], j["name"], j["state"], j.get("user", ""), j.get("partition", ""),
                        num(j["cpu_efficiency"]), num(j["memory_efficiency"]), num(j["time_used"]),
                        num(j["wasted_core_hours"]), " | ".join(j["recommendations"])])


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
    return "%s%.2f" % (currency, value)


def _rate(currency, value):
    return "%s%s" % (currency, ("%.2f" % value) if round(value, 2) == value else ("%g" % value))


def anonymise(result):
    """Copy of an analyze() result with users, job names and job IDs replaced by user1/job1/J1 labels.
    Same value -> same label, numbered in order of first appearance in result["jobs"].
    Empty users stay empty and the "(unknown)" group stays as it is. Partitions and numbers are kept."""
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
    for g in out.get("summary", {}).get("by_user", []):
        if g["name"] != "(unknown)":
            g["name"] = label(users, g["name"], "user")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(prog="hpcflow")
    parser.add_argument("file", nargs="?", default=None, help="path to a sacct export, or '-' for stdin")
    parser.add_argument("--days", type=int, help="ignore FILE and run sacct for the last N days (default when FILE is omitted: 7 days)")
    parser.add_argument("--all-users", action="store_true", help="add '-a' to sacct (admins)")
    parser.add_argument("--top", type=int, default=5, help="how many jobs to list (default 5)")
    parser.add_argument("--json", action="store_true", help="print json.dumps(result, indent=2) instead of the text report")
    parser.add_argument("--csv", help="also write a CSV report to PATH")
    parser.add_argument("--anonymise", "--anonymize", action="store_true",
                        help="replace user names, job names and job IDs with neutral labels (safe to share)")
    parser.add_argument("--cpu-hour-cost", type=float, default=None,
                        help="your centre's price per core-hour, to show what wasted CPU time costs")
    parser.add_argument("--gpu-hour-cost", type=float, default=None,
                        help="your centre's price per GPU-hour, to show what idle GPU time costs")
    parser.add_argument("--currency", default="£", help="currency symbol for costs (default: £)")

    args = parser.parse_args(argv)

    text = read_input(args)
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
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(report(result, args.top))

    if args.csv:
        write_csv(result, args.csv)

    return 0


if __name__ == "__main__":
    sys.exit(main())