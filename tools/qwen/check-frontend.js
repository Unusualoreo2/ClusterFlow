// Frontend check: the page script parses, and every required snippet is present (forbidden ones absent).
// Usage: node check-frontend.js <index.html> "required1" "required2" ... [-- "forbidden1" ...]
const fs = require("fs");
const [file, ...rest] = process.argv.slice(2);
const html = fs.readFileSync(file, "utf8");
const js = html.split("<script>")[1]?.split("</script>")[0] ?? "";
let ok = true;
try { new Function(js); } catch (e) { console.log("JS does not parse: " + e.message); ok = false; }
const cut = rest.indexOf("--");
const need = cut < 0 ? rest : rest.slice(0, cut), forbid = cut < 0 ? [] : rest.slice(cut + 1);
for (const s of need) if (!html.includes(s)) { console.log("missing: " + s); ok = false; }
for (const s of forbid) if (html.includes(s)) { console.log("must not contain: " + s); ok = false; }
if (/innerHTML\s*=\s*[^'"\s]/.test(js)) { console.log("innerHTML assigned from a variable (XSS risk)"); ok = false; }
process.exit(ok ? 0 : 1);
