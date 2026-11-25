#!/usr/bin/env python3
"""Check HPCFlow's verdicts on the six pilot test jobs (pilot/hpcflow_*.sh).

Usage: python3 check_pilot.py RESULT_JSON     (RESULT_JSON = output of: hpcflow.py --days 1 --json)
Python 3.6+, standard library only.
"""
import json
import sys

KINDS = ["good", "overcpu", "overmem", "overtime", "oom", "timeout"]


def pct(v):
    return "-" if v is None else "%d%%" % round(v)


def job_number(job):
    """Numeric job ID (part before '_' or '.'), or -1 if not numeric."""
    head = job.get("job_id", "").split("_")[0].split(".")[0]
    return int(head) if head.isdigit() else -1


def latest(jobs, kind):
    """The most recent job named hpcflow_<kind>, or None."""
    matches = [j for j in jobs if j.get("name") == "hpcflow_" + kind]
    if not matches:
        return None
    best = max(matches, key=job_number)
    return best if job_number(best) >= 0 else matches[-1]


def verdict(kind, job):
    """(verdict, note) for one pilot job."""
    state = job.get("state", "")
    recs = " ".join(job.get("recommendations", []))
    done = state.startswith("COMPLETED")
    if kind == "good":
        ok = done and not job.get("recommendations")
    elif kind == "overcpu":
        ok = done and "--cpus-per-task=" in recs
    elif kind == "overmem":
        ok = done and "--mem=" in recs
    elif kind == "overtime":
        ok = done and "--time=" in recs
    elif kind == "oom":
        if done:
            return "INCONCLUSIVE", "cluster did not enforce the memory limit"
        ok = state.startswith("OUT_OF_MEMORY") and "out of memory" in recs.lower()
    else:  # timeout
        ok = state.startswith("TIMEOUT") and "time limit" in recs
    return ("PASS" if ok else "FAIL"), None


def main(argv):
    if len(argv) != 1:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    try:
        with open(argv[0], encoding="utf-8") as f:
            jobs = json.load(f)["jobs"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("check_pilot: cannot read %s: %s" % (argv[0], e), file=sys.stderr)
        return 2

    verdicts = []
    for kind in KINDS:
        job = latest(jobs, kind)
        if job is None:
            v, detail = "MISSING", "not in the report - has the job finished?"
        else:
            v, note = verdict(kind, job)
            detail = "state=%s cpu=%s mem=%s time=%s" % (
                job.get("state", ""), pct(job.get("cpu_efficiency")),
                pct(job.get("memory_efficiency")), pct(job.get("time_used")))
            if note:
                detail += " (%s)" % note
        verdicts.append(v)
        print("%-12s %-9s %s" % (v, kind, detail))

    print("")
    print("%d/6 passed" % verdicts.count("PASS"))
    if "FAIL" in verdicts or "MISSING" in verdicts:
        print("Some checks did not pass: send the anonymised report "
              "(hpcflow.py --days 1 --anonymise) to the developer.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
