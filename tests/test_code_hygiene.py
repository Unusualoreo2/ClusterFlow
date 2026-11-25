"""Guards against AI-edit leftovers: duplicate definitions silently shadow each other."""
import ast
import glob
import os

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SOURCES = sorted(glob.glob(os.path.join(ROOT, "backend", "*.py")) + glob.glob(os.path.join(ROOT, "pilot", "*.py"))
                 + glob.glob(os.path.join(ROOT, "scripts", "*.py")))


@pytest.mark.parametrize("path", SOURCES, ids=os.path.basename)
def test_no_duplicate_top_level_definitions(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    names = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, "defined more than once: %s" % dupes
