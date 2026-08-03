// report-template/.build/build.mjs
import { build } from "esbuild";
import { mkdirSync, copyFileSync, writeFileSync, readFileSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { computeSourceHash } from "./source-hash.mjs";

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

// 4. Source hash of report-template/ JSX + CSS sources (rule lives in source-hash.mjs).
writeFileSync(join(OUT_DIR, ".source-hash"), computeSourceHash(TEMPLATE_DIR));

// 5. Vendor-licenses.txt.
writeFileSync(join(OUT_DIR, "vendor-licenses.txt"), [
  "React 18.3.1 — MIT — https://github.com/facebook/react/blob/main/LICENSE",
  "Cytoscape.js 3.30.2 — MIT — https://github.com/cytoscape/cytoscape.js/blob/master/LICENSE",
  "cytoscape-dagre 2.5.0 — MIT — https://github.com/cytoscape/cytoscape.js-dagre/blob/master/LICENSE",
  "cytoscape-fcose 2.2.0 — MIT — https://github.com/iVis-at-Bilkent/cytoscape.js-fcose/blob/master/LICENSE",
  "",
  "Vendored fonts (woff2, latin subset) — SIL Open Font License 1.1",
  "  Newsreader v26 — Production Type / Google Fonts",
  "    https://fonts.google.com/specimen/Newsreader",
  "    https://github.com/productiontype/Newsreader/blob/master/OFL.txt",
  "  IBM Plex Sans v23 — IBM Corp.",
  "    https://fonts.google.com/specimen/IBM+Plex+Sans",
  "    https://github.com/IBM/plex/blob/master/LICENSE.txt",
  "  IBM Plex Mono v20 — IBM Corp.",
  "    https://fonts.google.com/specimen/IBM+Plex+Mono",
  "    https://github.com/IBM/plex/blob/master/LICENSE.txt",
].join("\n") + "\n");

console.log(`Wrote bundle to ${OUT_DIR}`);
