"""Paste-ready #SBATCH lines for typical jobs (v0.16). Written by the architect; implementation must pass it unchanged.

Each typical-job profile gets "sbatch": a list of `#SBATCH` lines, one per setting that has a recommendation
(same values as the advice text, in the order cpus, mem, time). The CLI prints them under the advice; the web page
shows them in a <pre> block."""
import os
import re
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
CLI = os.path.join(ROOT, "backend", "clusterflow_cli.py")
sys.path.insert(0, os.path.join(ROOT, "backend"))
import analysis  # noqa: E402
import clusterflow_cli  # noqa: E402


def profiles():
    return {p["name"]: p for p in analysis.analyze(clusterflow_cli.DEMO_SACCT)["summary"]["profiles"]}


def test_every_profile_has_sbatch_list():
    for p in profiles().values():
        assert isinstance(p["sbatch"], list)
        assert len(p["sbatch"]) == len(p["recommendations"])


def test_values_match_the_advice():
    p = profiles()["cfd_mesh"]
    assert p["sbatch"] == ["#SBATCH --cpus-per-task=13", "#SBATCH --mem=14160M", "#SBATCH --time=04:30:00"]
    for line, rec in zip(p["sbatch"], p["recommendations"]):
        assert line.split()[1] in rec                     # same flag=value as the sentence


def test_only_settings_with_advice():
    assert profiles()["train_net"]["sbatch"] == ["#SBATCH --mem=60000M"]
    assert profiles()["md_run"]["sbatch"] == []


def test_time_over_a_day_uses_slurm_day_format():
    assert analysis._slurm_time(30 * 3600) == "1-06:00:00"
    assert analysis._slurm_time(4 * 3600 + 30 * 60) == "04:30:00"
    assert analysis._slurm_time(0) == "00:00:00"


def test_cli_prints_paste_block():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    out = subprocess.run([sys.executable, CLI, "--demo"], stdout=subprocess.PIPE, universal_newlines=True,
                         encoding="utf-8", env=env, timeout=60).stdout
    lines = out.split("amurphy / cfd_mesh (8 runs)", 1)[1].splitlines()
    i = lines.index("    Paste into your job script:")
    assert lines[i + 1:i + 4] == ["      #SBATCH --cpus-per-task=13", "      #SBATCH --mem=14160M",
                                  "      #SBATCH --time=04:30:00"]
    assert lines[i - 1].startswith("    - Across 8 runs, 95% finished")    # after the advice


def test_no_paste_block_without_advice():
    result = analysis.analyze(clusterflow_cli.DEMO_SACCT)
    for p in result["summary"]["profiles"]:
        p["sbatch"] = [] if p["name"] != "cfd_mesh" else p["sbatch"]
    text = clusterflow_cli.report(result, 5)
    assert text.count("Paste into your job script:") == 1


def test_web_page_shows_sbatch_block():
    with open(os.path.join(ROOT, "frontend", "index.html"), encoding="utf-8") as f:
        page = f.read()
    body = re.search(r"function renderProfiles\(profiles\) \{(.*?)\n        \}", page, re.S).group(1)
    assert "p.sbatch" in body and "'pre'" in body
    assert "innerHTML" not in body
