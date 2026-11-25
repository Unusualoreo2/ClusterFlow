// Hand one task to the local Qwen (llama.cpp, OpenAI-compatible API) and let it
// use file tools inside one project folder until it finishes.
// Usage: node qwen-worker.mjs <project-folder> <task-file> [model]
// Env:   QWEN_URL (default http://127.0.0.1:8080/v1), QWEN_TIMEOUT_S (default 600)

import fs from "node:fs/promises";
import path from "node:path";

process.on("uncaughtException", e => { console.log(`WORKER CRASH: ${e.stack || e}`); process.exit(3); });
process.on("unhandledRejection", e => { console.log(`WORKER CRASH: ${e?.stack || e}`); process.exit(3); });

const [ROOT_ARG, TASK_FILE, MODEL = "qwen3-coder-30b"] = process.argv.slice(2);
if (!ROOT_ARG || !TASK_FILE) { console.error("usage: node qwen-worker.mjs <project> <task-file> [model]"); process.exit(2); }
const ROOT = path.resolve(ROOT_ARG);
const URL_BASE = process.env.QWEN_URL || "http://127.0.0.1:8080/v1";
const TIMEOUT_MS = Number(process.env.QWEN_TIMEOUT_S || 600) * 1000;
const MAX_ROUNDS = 25;

function safe(p = ".") {
  const full = path.resolve(ROOT, p);
  const rel = path.relative(ROOT, full);
  if (rel.startsWith("..") || path.isAbsolute(rel)) throw new Error(`Path is outside the project: ${p}`);
  return full;
}

const tools = {
  list_files: {
    d: "List files and folders in a project folder (relative path, '.' = project root).",
    p: { path: "Folder path" }, req: [],
    run: async ({ path: p = "." }) => (await fs.readdir(safe(p), { withFileTypes: true }))
      .map(i => i.isDirectory() ? i.name + "/" : i.name).join("\n") || "(empty)",
  },
  read_file: {
    d: "Read lines of a text file (max 200 lines per call). Use search_text first to find the line numbers you need.",
    p: { path: "File path", start_line: "First line to read (default 1)", max_lines: "Number of lines (default 200, max 200)" }, req: ["path"],
    run: async ({ path: p, start_line = 1, max_lines = 200 }) => {
      const lines = (await fs.readFile(safe(p), "utf8")).replace(/\r\n/g, "\n").split("\n");
      const s = Math.max(1, Number(start_line) || 1), n = Math.min(200, Math.max(1, Number(max_lines) || 200));
      const body = lines.slice(s - 1, s - 1 + n).map((l, i) => `${s + i}| ${l}`).join("\n");
      const more = s - 1 + n < lines.length ? `\n... (file has ${lines.length} lines; read more with start_line=${s + n})` : "";
      return body + more;
    },
  },
  search_text: {
    d: "Find lines containing a text in a file. Returns matching line numbers and lines.",
    p: { path: "File path", text: "Text to find (case-sensitive)" }, req: ["path", "text"],
    run: async ({ path: p, text }) => {
      const hits = (await fs.readFile(safe(p), "utf8")).replace(/\r\n/g, "\n").split("\n")
        .map((l, i) => [i + 1, l]).filter(([, l]) => l.includes(text)).slice(0, 40);
      return hits.length ? hits.map(([n, l]) => `${n}| ${l}`).join("\n") : "No matches.";
    },
  },
  write_file: {
    d: "Create or completely replace a file in the project. Always pass the COMPLETE file content.",
    p: { path: "File path", content: "Complete file content" }, req: ["path", "content"],
    run: async ({ path: p, content = "" }) => {
      const f = safe(p); await fs.mkdir(path.dirname(f), { recursive: true });
      await fs.writeFile(f, content, "utf8"); return `Wrote ${content.length} chars to ${p}`;
    },
  },
  replace_text: {
    d: "Edit a file by replacing one exact snippet with new text. Prefer this over write_file for small fixes. " +
       "old_text must match the file exactly (without the line-number prefixes read_file shows) and appear once.",
    p: { path: "File path", old_text: "Exact text to find", new_text: "Replacement text" }, req: ["path", "old_text", "new_text"],
    run: async ({ path: p, old_text, new_text = "" }) => {
      const f = safe(p); const src = (await fs.readFile(f, "utf8")).replace(/\r\n/g, "\n");
      const unprefix = t => t.replace(/\r\n/g, "\n").replace(/^ *\d+\| /gm, "");
      if (src.split(old_text).length === 1) { old_text = unprefix(old_text); new_text = unprefix(new_text); }
      const n = src.split(old_text).length - 1;
      if (n !== 1) return `Error: old_text found ${n} times (must be exactly 1). Read the file again and copy the text exactly.`;
      await fs.writeFile(f, src.replace(old_text, () => new_text), "utf8"); return `Replaced text in ${p}`;
    },
  },
  run_tests: {
    d: "Run the project's test suite (pytest) and return the result. Use it to check your work before finishing.",
    p: {}, req: [],
    run: async () => {
      const { execFile } = await import("node:child_process");
      const py = path.join(ROOT, ".venv", "Scripts", "python.exe");
      return await new Promise(resolve => execFile(py, ["-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider"],
        { cwd: ROOT, timeout: 120000, maxBuffer: 1e6 },
        (err, out, errOut) => resolve(((out || "") + (errOut || "")).split("\n").slice(-60).join("\n"))));
    },
  },
};

const toolSpecs = Object.entries(tools).map(([name, t]) => ({
  type: "function",
  function: {
    name, description: t.d,
    parameters: { type: "object", required: t.req,
      properties: Object.fromEntries(Object.entries(t.p).map(([k, d]) => [k, { type: "string", description: d }])) },
  },
}));

const task = await fs.readFile(TASK_FILE, "utf8");
const messages = [
  { role: "system", content:
    "You are a careful software engineer. You receive exact specifications from the architect and implement them " +
    "using your file tools. Follow the spec literally: same file names, function names, signatures and behaviour. " +
    "Do not invent features, statistics or files that were not asked for. Write complete files, never placeholders. " +
    "When finished, reply with a short list of the files you wrote." },
  { role: "user", content: task },
];

async function chat() {
  const res = await fetch(`${URL_BASE}/chat/completions`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(TIMEOUT_MS),
    body: JSON.stringify({ model: MODEL, messages, tools: toolSpecs, temperature: 0.3, max_tokens: Number(process.env.QWEN_MAX_TOKENS || 12000) }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${(await res.text()).slice(0, 500)}`);
  return (await res.json()).choices[0];
}

const t0 = Date.now();
let greenRuns = 0;
for (let round = 1; round <= MAX_ROUNDS; round++) {
  let choice;
  for (let attempt = 1; ; attempt++) {
    try { choice = await chat(); break; }
    catch (e) {
      console.log(`[round ${round}] request failed (${e.name === "TimeoutError" ? "froze: timed out" : e.message})`);
      if (attempt >= 2) { console.log("GAVE UP"); process.exit(1); }
      console.log("retrying...");
    }
  }
  const msg = choice.message;
  messages.push(msg);
  if (choice.finish_reason === "length") console.log(`[round ${round}] warning: output hit the token limit`);
  if (!msg.tool_calls?.length) {
    console.log(`\nQWEN (${Math.round((Date.now() - t0) / 1000)}s):\n${(msg.content || "").trim()}`);
    process.exit(0);
  }
  // A tool call cut off by the token limit has invalid JSON; leaving it in the history makes
  // the server reject every later request. Drop it and ask for smaller steps instead.
  const broken = msg.tool_calls.some(c => { try { JSON.parse(c.function.arguments || "{}"); return false; } catch { return true; } });
  if (broken) {
    messages.pop();
    messages.push({ role: "user", content:
      "Your last tool call was too long and got cut off, so nothing was written. Do NOT rewrite whole files. " +
      "Make the change with several small replace_text calls instead (each old_text a few lines, copied exactly from read_file without the line-number prefixes)." });
    console.log(`[round ${round}] tool call was cut off -> discarded, asked Qwen for smaller edits`);
    continue;
  }
  for (const call of msg.tool_calls) {
    const name = call.function.name;
    let result;
    try {
      const args = JSON.parse(call.function.arguments || "{}");
      console.log(`[${name}] ${args.path ?? ""}${args.content ? ` (${args.content.length} chars)` : ""}`);
      if (!tools[name]) throw new Error(`Unknown tool ${name}`);
      result = await tools[name].run(args);
    } catch (e) { result = `Error: ${e.message}`; }
    if (String(result).startsWith("Error")) console.log(`  -> ${String(result).slice(0, 160)}`);
    else if (name === "run_tests") console.log(`  -> ${String(result).trim().split("\n").pop()}`);
    messages.push({ role: "tool", tool_call_id: call.id, content: String(result) });
    // Qwen tends to keep re-running a green test suite instead of finishing: stop it.
    if (name === "run_tests") {
      const last = String(result).trim().split("\n").pop();
      greenRuns = /passed/.test(last) && !/failed|error/.test(last) ? greenRuns + 1 : 0;
      if (greenRuns >= 2) { console.log("DONE: tests passed twice with no edits in between"); process.exit(0); }
    } else if (["write_file", "replace_text"].includes(name)) greenRuns = 0;
  }
}
console.log("Stopped: too many rounds"); process.exit(1);
