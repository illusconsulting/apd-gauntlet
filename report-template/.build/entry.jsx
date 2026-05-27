// report-template/.build/entry.jsx
// Single entry point esbuild bundles. Each screen module historically attached
// itself to `window.<Name>`; under the bundle they're imported by app.jsx
// through the same window assignment, kept for symmetry with the dev template.

import React from "react";
import { createRoot } from "react-dom/client";
import mermaid from "mermaid";

window.React = React;
window.ReactDOM = { createRoot };
window.mermaid = mermaid;

// Side-effect imports register window.<ComponentName>.
import "../components.jsx";
import "../screens/Overview.jsx";
import "../screens/Findings.jsx";
import "../screens/Capabilities.jsx";
import "../screens/Coverage.jsx";
import "../screens/Annexes.jsx";
import "../screens/AttackPaths.jsx";
import "../app.jsx";
