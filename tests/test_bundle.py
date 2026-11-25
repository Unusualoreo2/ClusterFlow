"""Single-file bundle dist/hpcflow.py (v0.5). Written by the architect; implementation must pass it unchanged."""
import ast
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXAMPLE = os.path.join(ROOT, "data", "example_sacct.txt")


def build(tmp_path):
    out = tmp_path / "hpcflow.py"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_bundle.py"), str(out)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return out


def run(script, *args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env, timeout=60)


def test_bundle_runs_alone_in_an_empty_folder(tmp_path):
    bundle = build(tmp_path)
    alone = tmp_path / "alone"
    alone.mkdir()
    shutil.copy(bundle, alone / "hpcflow.py")
    shutil.copy(EXAMPLE, alone / "jobs.txt")
    r = run(alone / "hpcflow.py", str(alone / "jobs.txt"))
    assert r.returncode == 0, r.stderr
    assert "5 jobs analysed (1 running/pending skipped)" in r.stdout


def test_bundle_output_matches_cli(tmp_path):
    bundle = build(tmp_path)
    a = run(bundle, EXAMPLE, "--top", "3").stdout
    b = run(os.path.join(ROOT, "backend", "hpcflow_cli.py"), EXAMPLE, "--top", "3").stdout
    assert a == b and a


def test_bundle_has_no_local_imports_and_is_py37(tmp_path):
    src = build(tmp_path).read_text(encoding="utf-8")
    assert "from analysis import" not in src and "import analysis" not in src
    assert "sys.path.insert" not in src
    ast.parse(src, feature_version=(3, 7))
    assert src.startswith("#!/usr/bin/env python3")
    assert src.count('if __name__ == "__main__":') == 1


def test_default_output_path():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_bundle.py")],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert os.path.exists(os.path.join(ROOT, "dist", "hpcflow.py"))
