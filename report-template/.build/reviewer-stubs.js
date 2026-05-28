// reviewer-stubs.js — globals that the dev template gets from tweaks-panel.jsx
// but the precompiled reviewer bundle has to provide directly (because the dev-
// only tweaks panel is intentionally stripped from the bundle per Task 6.2).
//
// Must execute AFTER react-globals.js (needs window.React) but BEFORE app.jsx
// and the screen modules (they reference these names as free variables).
//
// Currently:
//   - useTweaks: a state-only stub matching the dev-template's signature
//     ((key, value) or ({key: value}) updates). The dev version also
//     postMessages to a host design-tool window; that's irrelevant in
//     reviewer mode so we drop it. The layout-select event listener in
//     app.jsx still works because setTweak updates real React state.

window.useTweaks = function useTweaks(defaults) {
  const [values, setValues] = window.React.useState(defaults);
  const setTweak = window.React.useCallback(function (keyOrEdits, val) {
    const edits =
      typeof keyOrEdits === "object" && keyOrEdits !== null
        ? keyOrEdits
        : { [keyOrEdits]: val };
    setValues(function (prev) {
      return { ...prev, ...edits };
    });
  }, []);
  return [values, setTweak];
};
