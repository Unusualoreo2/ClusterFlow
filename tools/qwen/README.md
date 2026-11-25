# Qwen build workflow

How ClusterFlow is built: Claude (architect) writes specs and tests; a local Qwen3-Coder model (llama.cpp at http://127.0.0.1:8080/v1) implements them; nothing is accepted until the tests and a task-specific check pass.

- `qwen-worker.mjs <project> <task.md> [model]`: gives Qwen one task with file tools limited to the project folder (list/read in 200-line chunks, search, write, replace_text, run_tests). Stops Qwen when the tests pass twice with no edits in between; drops cut-off tool calls; per-request timeout (`QWEN_TIMEOUT_S`) and output cap (`QWEN_MAX_TOKENS`).
- `qwen-task.sh <task.md> [max_tokens] [check-command]`: runs the worker, rebuilds `dist/clusterflow.py`, then verifies = full test suite + the check command. On failure it rolls back Qwen's edits (outside `tests/` and `data/`) and retries once. Commit specs/tests before calling it.
- `check-frontend.js <index.html> "required" ... [-- "forbidden" ...]`: checks the page script parses, required snippets exist, forbidden ones don't, and no innerHTML is assigned from a variable.
