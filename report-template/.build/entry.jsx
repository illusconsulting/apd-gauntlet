// report-template/.build/entry.jsx
// Single entry point esbuild bundles. Each screen module historically attached
// itself to `window.<Name>`; under the bundle they're imported by app.jsx
// through the same window assignment, kept for symmetry with the dev template.
//
// CRITICAL: react-globals.js MUST be the first import. Its side effects set
// window.React / window.ReactDOM / window.mermaid, which the JSX modules below
// reference as module-top free variables (e.g. components.jsx does
// `const { useState } = React;` at line 4). ES module post-order evaluation
// guarantees the globals are set before any subsequent import body runs.

import "./react-globals.js";
import "./reviewer-stubs.js";

// Side-effect imports register window.<ComponentName>.
import "../components.jsx";
import "../screens/Overview.jsx";
import "../screens/Findings.jsx";
import "../screens/Capabilities.jsx";
import "../screens/Coverage.jsx";
import "../screens/Annexes.jsx";
import "../screens/AttackPaths.jsx";
import "../app.jsx";
