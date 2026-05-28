// react-globals.js — must execute BEFORE components.jsx and screen modules.
//
// The JSX modules under report-template/ (components.jsx, screens/*.jsx, app.jsx)
// historically run inside the dev template via Babel-in-browser after CDN-loaded
// React/ReactDOM scripts have already set the globals. Their module-top code
// references `React` (e.g. `const { useState } = React;`) and `ReactDOM` as free
// variables resolved against `window`.
//
// In the precompiled IIFE bundle, ES module post-order evaluation runs each
// import's body BEFORE the importer's body. By making this module the FIRST
// import in entry.jsx, its window-global assignments complete before any JSX
// module loads — restoring the dev-template invariant that React is global at
// module-top evaluation time.
import React from "react";
import { createRoot } from "react-dom/client";
import mermaid from "mermaid";

window.React = React;
window.ReactDOM = { createRoot };
window.mermaid = mermaid;

// The dev template's JSX modules use React hooks as bare free identifiers
// (`useState(...)`, `useEffect(...)`, etc.) because the unbundled scripts share
// a global Babel-in-browser scope where components.jsx's module-top destructure
// effectively leaks. Each IIFE module has its own scope, so the bundle must
// expose the same names on `window` for free-variable lookups to resolve.
window.useState = React.useState;
window.useEffect = React.useEffect;
window.useRef = React.useRef;
window.useMemo = React.useMemo;
window.useCallback = React.useCallback;
window.useLayoutEffect = React.useLayoutEffect;
window.useReducer = React.useReducer;
window.useContext = React.useContext;
