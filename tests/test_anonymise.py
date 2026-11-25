"""--anonymise (v0.6): output that can be shared without exposing people. Written by the architect."""
import csv
import json
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
CLI = os.path.join(ROOT, "backend", "clusterflow_cli.py")
EXAMPLE = os.path.join(ROOT, "data", "example_sacct.txt")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402

SECRETS = ["amurphy", "jkelly", "sobrien", "cfd_mesh", "md_run", "post_proc", "train_nn", "sweep_7", "4471201", "4471388"]


def run(*args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, CLI, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env, timeout=60)


def example():
    return analysis.analyze(open(EXAMPLE, encoding="utf-8").read())


def test_anonymise_function_replaces_people_and_jobs():
    original = example()
    anon = clusterflow_cli.anonymise(original)
    text = json.dumps(anon)
    for s in SECRETS:
        assert s not in text, s
    assert [j["user"] for j in anon["jobs"]] == ["user1", "user2", "user1", "user3", "user2"]
    assert [j["name"] for j in anon["jobs"]] == ["job1", "job2", "job3", "job4", "job5"]
    assert [j["job_id"] for j in anon["jobs"]] == ["J1", "J2", "J3", "J4", "J5"]
    # partitions are cluster names, not personal: kept
    assert [j["partition"] for j in anon["jobs"]] == [j["partition"] for j in original["jobs"]]
    # groups use the same mapping and keep their numbers
    assert [g["name"] for g in anon["summary"]["by_user"]] == ["user1", "user2", "user3"]
    assert anon["summary"]["by_user"][0]["wasted_core_hours"] == original["summary"]["by_user"][0]["wasted_core_hours"]


def test_anonymise_does_not_modify_the_input():
    original = example()
    before = json.dumps(original, sort_keys=True)
    clusterflow_cli.anonymise(original)
    assert json.dumps(original, sort_keys=True) == before


def test_anonymise_keeps_unknown_and_same_name_same_label():
    result = {"jobs": [{"job_id": "1", "name": "a", "user": "", "partition": "p"},
                       {"job_id": "2", "name": "a", "user": "x", "partition": "p"}],
              "skipped": 0, "summary": {"by_user": [{"name": "(unknown)"}, {"name": "x"}], "by_partition": []}}
    anon = clusterflow_cli.anonymise(result)
    assert [j["user"] for j in anon["jobs"]] == ["", "user1"]
    assert [j["name"] for j in anon["jobs"]] == ["job1", "job1"]
    assert [g["name"] for g in anon["summary"]["by_user"]] == ["(unknown)", "user1"]


def test_cli_text_json_csv_are_anonymised(tmp_path):
    out_csv = tmp_path / "r.csv"
    for args in ([EXAMPLE, "--anonymise"], [EXAMPLE, "--anonymise", "--json"], [EXAMPLE, "--anonymize"]):
        r = run(*args)
        assert r.returncode == 0, r.stderr
        for s in SECRETS:
            assert s not in r.stdout, (args, s)
    r = run(EXAMPLE, "--anonymise", "--csv", str(out_csv))
    body = out_csv.read_text(encoding="utf-8")
    for s in SECRETS:
        assert s not in body, s
    assert "user1" in body and "compute" in body
    # recommendations (no personal data) are kept
    assert "--cpus-per-task=14" in r.stdout


def test_without_flag_names_are_shown():
    assert "amurphy" in run(EXAMPLE).stdout
