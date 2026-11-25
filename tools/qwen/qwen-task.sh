#!/bin/bash
# Run one Qwen task against the HPCFlow project, then verify.
# Success = the whole test suite passes AND the task's own check command (if given) succeeds.
# On failure, Qwen's edits outside tests/ and data/ are rolled back to the last commit and the task is
# retried once, so a retry never stacks on a half-finished attempt. Commit specs/tests BEFORE calling this.
# Usage: qwen-task.sh <task-file> [max_tokens] [check-command]
TASK="$1"; MAXTOK="${2:-4000}"; CHECK="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
PROJ="$(cd "$HERE/../.." && pwd)"   # repository root (this script lives in tools/qwen/)
verify() {
  (cd "$PROJ" && .venv/Scripts/python scripts/build_bundle.py >/dev/null 2>&1)   # keep dist/hpcflow.py in sync
  local r; r=$(cd "$PROJ" && .venv/Scripts/python -m pytest -q -p no:cacheprovider 2>&1 | tail -1)
  echo "tests: $r"
  echo "$r" | grep -qE "failed|error" && return 1
  if [ -n "$CHECK" ]; then
    (cd "$PROJ" && bash -c "$CHECK") || { echo "check FAILED: $CHECK"; return 1; }
    echo "check passed"
  fi
  return 0
}
rollback() {
  (cd "$PROJ" && git checkout -q -- backend frontend scripts docs README.md Dockerfile 2>/dev/null
   git clean -fdq -- backend frontend scripts docs 2>/dev/null
   git ls-files --others --exclude-standard | grep -vE "^(tests|data)/" | xargs -r rm -f)
  echo "=== rolled back Qwen's edits"
}
for attempt in 1 2; do
  echo "=== Qwen attempt $attempt: $(basename "$TASK")"
  QWEN_TIMEOUT_S=240 QWEN_MAX_TOKENS=$MAXTOK node "$HERE/qwen-worker.mjs" "$PROJ" "$TASK" qwen3-coder-30b 2>&1 \
    | grep -E "^\[|->|QWEN|GAVE|cut off|froze|CRASH|Stopped|DONE|request failed|retrying"
  echo "=== verify after attempt $attempt"
  if verify; then echo "=== SUCCESS"; exit 0; fi
  [ "$attempt" = 1 ] && rollback
done
echo "=== FAILED after 2 attempts (edits left in place for review)"
exit 1
