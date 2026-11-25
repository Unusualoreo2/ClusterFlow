#!/bin/bash
# Commit only when the full test suite passes (the post-commit hook then backs it up to GitHub).
# Usage: bash tools/safe-commit.sh "message"   (run from the project root)
set -u
cd "$(dirname "$0")/.."
.venv/Scripts/python scripts/build_bundle.py >/dev/null || { echo "BUNDLE BUILD FAILED - not committing"; exit 1; }
result=$(.venv/Scripts/python -m pytest -q -p no:cacheprovider 2>&1 | tail -1)
echo "tests: $result"
if ! echo "$result" | grep -q "passed" || echo "$result" | grep -qE "failed|error"; then
  echo "TESTS NOT GREEN - not committing"
  exit 1
fi
git add -A
git -c user.name="HPCFlow" -c user.email="hpcflow@localhost" commit -q -m "$1

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" 2>&1 | grep -v "LF will"
sleep 3
tail -1 .git/autopush.log
