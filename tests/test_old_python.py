"""The cluster file must run on old system Pythons (RHEL/Rocky 8 ship Python 3.6).
Python 3.6 is not installed on the dev machine, so this scans for syntax and stdlib features newer than 3.6."""
import ast
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FILES = [os.path.join(ROOT, "backend", "analysis.py"), os.path.join(ROOT, "backend", "hpcflow_cli.py")]

# (pattern, reason) - features added after Python 3.6
NEWER_THAN_36 = [
    (r"capture_output\s*=", "subprocess.run(capture_output=) is 3.7+"),
    (r"\btext\s*=\s*True", "subprocess text=True is 3.7+ (use universal_newlines=True)"),
    (r"fromisoformat\(", "datetime.fromisoformat is 3.7+"),
    (r"\bdataclass", "dataclasses are 3.7+"),
    (r"from __future__ import annotations", "3.7+"),
    (r"nullcontext", "contextlib.nullcontext is 3.7+"),
    (r"\.isascii\(", "str.isascii is 3.7+"),
    (r"breakpoint\(", "3.7+"),
    (r"math\.(isqrt|prod|dist|comb|perm)\(", "3.8+"),
    (r"functools\.cached_property", "3.8+"),
    (r"\.removeprefix\(|\.removesuffix\(", "3.9+"),
    (r"zoneinfo|graphlib", "3.9+"),
    (r"^\s*match\s+\S.*:\s*$", "match statement is 3.10+"),
    (r":=", "walrus operator is 3.8+"),
    (r"f\"[^\"]*\{[^}]*=\}", "f-string '=' specifier is 3.8+"),
    (r"(list|dict|tuple|set)\[[A-Za-z]", "builtin generics in annotations are 3.9+"),
    (r"argparse\.BooleanOptionalAction", "3.9+"),
    (r"\bdatetime\.UTC\b", "3.11+"),
]


def code_only(src):
    """Source with string literals and comments blanked, so docstrings don't trigger false matches."""
    out = []
    import io
    import tokenize
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in (tokenize.STRING, tokenize.COMMENT):
            out.append(" ")
        else:
            out.append(tok.string)
        out.append(" " if tok.type != tokenize.NEWLINE else "\n")
    return "".join(out)


def test_no_features_newer_than_python_36():
    problems = []
    for path in FILES:
        src = open(path, encoding="utf-8").read()
        code = code_only(src)
        for pat, why in NEWER_THAN_36:
            if re.search(pat, code, re.M):
                problems.append("%s: %s" % (os.path.basename(path), why))
        ast.parse(src, feature_version=(3, 7))  # oldest grammar the checker supports
    assert not problems, problems


def test_scanner_catches_violations():
    bad = 'import subprocess\nsubprocess.run(["x"], capture_output=True, text=True)\nif (n := 3): pass\n'
    hits = [why for pat, why in NEWER_THAN_36 if re.search(pat, code_only(bad), re.M)]
    assert len(hits) == 3, hits
    match_stmt = "match x:\n    case 1:\n        pass\n"
    match_var = "for a, match in b:\n    pass\n"
    assert any(re.search(p, code_only(match_stmt), re.M) for p, w in NEWER_THAN_36)
    assert not any(re.search(p, code_only(match_var), re.M) for p, w in NEWER_THAN_36)
    assert not [w for p, w in NEWER_THAN_36 if re.search(p, code_only('"""capture_output= in a docstring"""\n'), re.M)]


def test_bundle_is_up_to_date():
    """dist/hpcflow.py must match what build_bundle.py produces from the current sources."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "hpcflow.py")
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_bundle.py"), out], check=True,
                       stdout=subprocess.PIPE)
        fresh = open(out, encoding="utf-8").read()
    committed = open(os.path.join(ROOT, "dist", "hpcflow.py"), encoding="utf-8").read()
    assert fresh == committed, "dist/hpcflow.py is stale: run python scripts/build_bundle.py"
