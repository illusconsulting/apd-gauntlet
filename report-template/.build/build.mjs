// report-template/.build/build.mjs
import { build } from "esbuild";
import { mkdirSync, copyFileSync, writeFileSync, readFileSync, statSync, readdirSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { createHash } from "node:crypto";

const HERE = dirname(new URL(import.meta.url).pathname);
const TEMPLATE_DIR = resolve(HERE, "..");                   // report-template/
const OUT_DIR = resolve(HERE, "../../tools/apd_gauntlet/data/report-template");
const FONTS_DIR = join(OUT_DIR, "fonts");

mkdirSync(OUT_DIR, { recursive: true });
mkdirSync(FONTS_DIR, { recursive: true });

// 1. Bundle JSX → app.js.
await build({
  entryPoints: [join(HERE, "entry.jsx")],
  bundle: true,
  minify: true,
  format: "iife",
  jsx: "transform",
  outfile: join(OUT_DIR, "app.js"),
  loader: { ".jsx": "jsx" },
  target: ["es2020"],
  define: {"process.env.NODE_ENV": '"production"'},
});

// 2. Copy css.
copyFileSync(join(TEMPLATE_DIR, "styles.css"), join(OUT_DIR, "styles.css"));
copyFileSync(join(TEMPLATE_DIR, "screens.css"), join(OUT_DIR, "screens.css"));

// 3. Strip tweaks-panel + CDN script tags from index.html, point at app.js.
const html = readFileSync(join(TEMPLATE_DIR, "APD Gauntlet Report.html"), "utf8");
const stripped = html
  // Strip all script tags except the data.js placeholder.
  .replace(/<script src="https:[^"]+"[^>]*><\/script>\s*/g, "")
  .replace(/<script type="text\/babel"[^>]*src="[^"]+"[^>]*><\/script>\s*/g, "")
  .replace(/<script src="tweaks-panel\.jsx"[^>]*><\/script>\s*/g, "")
  // Replace the original <script src="data.js"></script> with one app.js wiring.
  .replace(
    '<script src="data.js"></script>',
    '<script src="data.js"></script>\n<script src="app.js"></script>'
  )
  // Switch font import to local fonts/ (done in the CSS too, but if there were
  // any inline link rel=stylesheet to Google Fonts, strip them).
  .replace(/<link[^>]*fonts\.googleapis\.com[^>]*>\s*/g, "")
  .replace(/<link[^>]*fonts\.gstatic\.com[^>]*>\s*/g, "");
writeFileSync(join(OUT_DIR, "index.html"), stripped);

// 4. Vendor mermaid.
copyFileSync(
  resolve(HERE, "node_modules/mermaid/dist/mermaid.min.js"),
  join(OUT_DIR, "mermaid.min.js"),
);

// 5. Source hash of report-template/ JSX + CSS sources.
const hash = createHash("sha256");
function walk(d) {
  for (const e of readdirSync(d).sort()) {
    if (e === ".build" || e === "node_modules" || e.startsWith(".")) continue;
    const p = join(d, e);
    if (statSync(p).isDirectory()) walk(p);
    else { hash.update(e); hash.update(readFileSync(p)); }
  }
}
walk(TEMPLATE_DIR);
writeFileSync(join(OUT_DIR, ".source-hash"), hash.digest("hex"));

// 6. Vendor-licenses.txt.
writeFileSync(join(OUT_DIR, "vendor-licenses.txt"), [
  "React 18.3.1 — MIT — https://github.com/facebook/react/blob/main/LICENSE",
  "Mermaid 10.9.1 — MIT — https://github.com/mermaid-js/mermaid/blob/develop/LICENSE",
  "Fonts: Google Fonts — see SIL OFL / Apache 2.0 license files alongside each .woff2",
].join("\n") + "\n");

console.log(`Wrote bundle to ${OUT_DIR}`);
