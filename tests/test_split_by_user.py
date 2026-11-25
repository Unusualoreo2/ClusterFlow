"""One HTML report per user (v0.17), for HPC teams sending each researcher their own report.
Written by the architect; implementation must pass it unchanged.

- analysis.analyze(text, user=None): with a user, only that user's jobs are analysed (filter right after merging
  steps), so every summary, table and count covers that user alone.
- CLI `--split-by-user DIR`: besides the normal stdout report, writes DIR/<user>.html (html_report, banner
  "Report for <user>") for every non-empty user, creating DIR if needed. File names keep only [A-Za-z0-9._-]
  (others become "_"). Not allowed with --anonymise. Says on stderr how many files it wrote."""
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
CLI = os.path.join(ROOT, "backend", "clusterflow_cli.py")
BUNDLE = os.path.join(ROOT, "dist", "clusterflow.py")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402

DEMO_USERS = ["amurphy", "jkelly", "ocallaghan", "rbrennan", "sdoyle"]
HDR = "JobID|JobName|User|State|Elapsed|Timelimit|AllocCPUS|TotalCPU|ReqMem|MaxRSS\n"


def run(*args, script=CLI):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, script, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env, timeout=60)


def test_analyze_for_one_user():
    r = analysis.analyze(clusterflow_cli.DEMO_SACCT, user="amurphy")
    assert r["summary"]["job_count"] == 8
    assert {j["user"] for j in r["jobs"]} == {"amurphy"}
    assert [g["name"] for g in r["summary"]["by_user"]] == ["amurphy"]
    assert [p["user"] for p in r["summary"]["profiles"]] == ["amurphy"]


def test_analyze_default_unchanged():
    assert analysis.analyze(clusterflow_cli.DEMO_SACCT) == analysis.analyze(clusterflow_cli.DEMO_SACCT, user=None)


def test_unknown_user_gives_empty_result():
    r = analysis.analyze(clusterflow_cli.DEMO_SACCT, user="nobody")
    assert r["summary"]["job_count"] == 0 and r["jobs"] == []


def test_skipped_counts_only_that_user():
    text = HDR + ("1|a|ann|RUNNING|01:00:00|02:00:00|1|01:00:00|1G|\n"
                  "2|b|bob|RUNNING|01:00:00|02:00:00|1|01:00:00|1G|\n"
                  "3|b|bob|COMPLETED|01:00:00|02:00:00|1|01:00:00|1G|\n3.batch|batch||COMPLETED|01:00:00||1|01:00:00||500M\n")
    assert analysis.analyze(text, user="ann")["skipped"] == 1
    assert analysis.analyze(text, user="bob")["skipped"] == 1
    assert analysis.analyze(text, user="bob")["summary"]["job_count"] == 1


def test_cli_writes_one_file_per_user(tmp_path):
    out = tmp_path / "reports"                     # does not exist yet
    p = run("--demo", "--split-by-user", str(out), "--cpu-hour-cost", "0.02")
    assert p.returncode == 0, p.stderr
    assert sorted(os.listdir(str(out))) == [u + ".html" for u in DEMO_USERS]
    page = (out / "amurphy.html").read_text(encoding="utf-8")
    assert "Report for amurphy" in page
    assert "8 jobs analysed" in page
    assert "Cost of wasted CPU time" in page
    for other in DEMO_USERS[1:]:
        assert other not in page                    # a researcher sees only their own jobs
    assert "wrote 5 per-user reports" in p.stderr


def test_stdout_unchanged(tmp_path):
    assert run("--demo", "--split-by-user", str(tmp_path / "r")).stdout == run("--demo").stdout


def test_safe_file_names_and_empty_user(tmp_path):
    text = HDR + ("1|a|../evil user|COMPLETED|01:00:00|02:00:00|1|01:00:00|1G|\n"
                  "1.batch|batch||COMPLETED|01:00:00||1|01:00:00||500M\n"
                  "2|b||COMPLETED|01:00:00|02:00:00|1|01:00:00|1G|\n"
                  "2.batch|batch||COMPLETED|01:00:00||1|01:00:00||500M\n")
    f = tmp_path / "x.txt"
    f.write_text(text, encoding="utf-8")
    out = tmp_path / "r"
    p = run(str(f), "--split-by-user", str(out))
    assert p.returncode == 0, p.stderr
    assert os.listdir(str(out)) == [".._evil_user.html"]
    assert not (tmp_path / "evil user.html").exists()


def test_not_with_anonymise(tmp_path):
    p = run("--demo", "--anonymise", "--split-by-user", str(tmp_path / "r"))
    assert p.returncode == 2
    assert "--split-by-user" in p.stderr


def test_bundle_supports_split(tmp_path):
    p = run("--demo", "--split-by-user", str(tmp_path / "r"), script=BUNDLE)
    assert p.returncode == 0, p.stderr
    assert len(os.listdir(str(tmp_path / "r"))) == 5


def test_documented():
    for doc in ("README.md", os.path.join("docs", "user-guide.md")):
        with open(os.path.join(ROOT, doc), encoding="utf-8") as f:
            assert "--split-by-user" in f.read()


# --- Review finding: re-analysing the whole file per user is O(users x jobs) (20k jobs / 200 users: 0.7 s -> 28 s).
# analysis.analyze_by_user(text) parses once and returns {user: result} for every non-empty user, sorted by user;
# each result equals analyze(text, user=u).

def test_analyze_by_user_matches_single_user_analysis():
    by = analysis.analyze_by_user(clusterflow_cli.DEMO_SACCT)
    assert list(by) == DEMO_USERS
    for u in DEMO_USERS:
        assert by[u] == analysis.analyze(clusterflow_cli.DEMO_SACCT, user=u)


def test_analyze_by_user_is_not_quadratic():
    import time
    rows = "".join("%d|sim|u%03d|COMPLETED|01:00:00|04:00:00|8|02:00:00|16G|\n"
                   "%d.batch|batch||COMPLETED|01:00:00||8|02:00:00||3000M\n" % (i, i % 200, i) for i in range(20000))
    text = HDR + rows
    t = time.perf_counter()
    analysis.analyze(text)
    one = time.perf_counter() - t
    t = time.perf_counter()
    by = analysis.analyze_by_user(text)
    split = time.perf_counter() - t
    assert len(by) == 200
    assert split < 3 * one + 1.0, "analyze_by_user took %.1fs vs %.1fs for one analysis" % (split, one)
