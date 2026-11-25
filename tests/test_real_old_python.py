"""Run the cluster bundle on real old Pythons (RHEL/Rocky 8 ships 3.6). Written by the architect.

Uses the official embeddable builds unpacked at %LOCALAPPDATA%/Programs/python-embed/<version>/ (or the folder in
CLUSTERFLOW_OLD_PYTHONS); skipped where they are not installed. Output must match the current Python (JSON up to float rounding)."""
import glob
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUNDLE = os.path.join(ROOT, "dist", "clusterflow.py")
EXAMPLE = os.path.join(ROOT, "data", "example_sacct.txt")
BASE = os.environ.get("CLUSTERFLOW_OLD_PYTHONS",
                      os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "python-embed"))
PYTHONS = sorted(glob.glob(os.path.join(BASE, "3.*", "python.exe")) + glob.glob(os.path.join(BASE, "3.*", "bin", "python3")))

pytestmark = pytest.mark.skipif(not PYTHONS, reason="no old Python builds installed")

CASES = [
    ["--demo"],
    ["--demo", "--anonymise", "--cpu-hour-cost", "0.02", "--gpu-hour-cost", "0.5"],
    [EXAMPLE, "--top", "3"],
]


def run(python, args, cwd):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([python, BUNDLE] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, encoding="utf-8", env=env, cwd=cwd, timeout=120)


@pytest.mark.parametrize("python", PYTHONS, ids=lambda p: os.path.basename(os.path.dirname(p)))
@pytest.mark.parametrize("args", CASES, ids=lambda a: " ".join(os.path.basename(x) for x in a))
def test_same_output_as_current_python(python, args, tmp_path):
    old = run(python, args, str(tmp_path))
    assert old.returncode == 0, old.stderr
    new = run(sys.executable, args, str(tmp_path))
    assert old.stdout == new.stdout


@pytest.mark.parametrize("python", PYTHONS, ids=lambda p: os.path.basename(os.path.dirname(p)))
def test_json_matches_up_to_float_rounding(python, tmp_path):
    """Python 3.12 sums floats more exactly (10.999999999999998 vs 11.0); text, HTML and CSV round these away."""
    old = run(python, ["--demo", "--json"], str(tmp_path))
    assert old.returncode == 0, old.stderr
    new = run(sys.executable, ["--demo", "--json"], str(tmp_path))
    assert _close(json.loads(old.stdout), json.loads(new.stdout))


def _close(a, b):
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= 1e-9 * max(1, abs(b))
    return a == b


@pytest.mark.parametrize("python", PYTHONS, ids=lambda p: os.path.basename(os.path.dirname(p)))
def test_html_and_csv_files_match(python, tmp_path):
    for exe, tag in ((python, "old"), (sys.executable, "new")):
        p = run(exe, ["--demo", "--html", "%s.html" % tag, "--csv", "%s.csv" % tag], str(tmp_path))
        assert p.returncode == 0, p.stderr
    for ext in ("html", "csv"):
        assert (tmp_path / ("old." + ext)).read_bytes() == (tmp_path / ("new." + ext)).read_bytes()
