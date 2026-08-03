// report-template/.build/source-hash.mjs
// The ONE Node-side definition of the source-hash walk. build.mjs imports it;
// the pytest parity test runs it via `node source-hash.mjs <dir>`. Python's
// tools/check_report_template_freshness.py mirrors these semantics — the
// parity test is what keeps the two honest.
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

export function computeSourceHash(rootDir) {
  const hash = createHash("sha256");
  function walk(d, prefix = "") {
    for (const e of readdirSync(d).sort()) {
      if (e === ".build" || e === "node_modules" || e.startsWith(".")) continue;
      const p = join(d, e);
      const rel = prefix ? `${prefix}/${e}` : e;
      if (statSync(p).isDirectory()) walk(p, rel);
      else {
        hash.update(rel);
        hash.update(Buffer.from([0])); // NUL separator matches Python
        hash.update(readFileSync(p));
      }
    }
  }
  walk(rootDir);
  return hash.digest("hex");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.stdout.write(computeSourceHash(process.argv[2]) + "\n");
}
