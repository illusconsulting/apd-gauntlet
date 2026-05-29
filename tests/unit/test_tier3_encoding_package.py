# tests/unit/test_tier3_encoding_package.py
"""Regression tests for explicit UTF-8 encoding across the non-report parts
of the apd_gauntlet package (T3-F).

T2-E covered the report/ subpackage. T3-F extends the discipline to the
rest of tools/apd_gauntlet/ so the package as a whole works under LC_ALL=C
or Windows cp1252 default locales.
"""
from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
PKG = REPO / "tools" / "apd_gauntlet"


def _iter_calls(body: str, method: str):
    """Yield ``(line_number, args_text)`` for every ``.method(...)`` call in
    ``body``. ``args_text`` is the substring between the call's outer parens,
    with balanced nesting respected so wrappers like
    ``.write_text(json.dumps(x), encoding="utf-8")`` are extracted in full
    rather than truncated at the first inner ``)``.
    """
    needle = "." + method + "("
    i = 0
    while True:
        idx = body.find(needle, i)
        if idx < 0:
            return
        start = idx + len(needle)
        depth = 1
        j = start
        while j < len(body) and depth:
            ch = body[j]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            j += 1
        if depth:
            return  # unbalanced; bail
        args = body[start : j - 1]
        line_no = body.count("\n", 0, idx) + 1
        yield line_no, args
        i = j


def test_no_bare_read_text_in_package():
    """No `.read_text()` call without explicit encoding outside report/."""
    violations = []
    for py in PKG.rglob("*.py"):
        if "report" in py.relative_to(PKG).parts:
            continue
        body = py.read_text(encoding="utf-8")
        for line_no, args in _iter_calls(body, "read_text"):
            stripped = args.strip()
            if not stripped:
                violations.append(f"{py.relative_to(REPO)}:{line_no} bare read_text()")
                continue
            if "encoding=" in args:
                continue
            # Allow positional shorthand `.read_text("utf-8")`.
            if re.match(r"^\s*['\"]utf-8['\"]\s*$", stripped):
                continue
            violations.append(
                f"{py.relative_to(REPO)}:{line_no} read_text without encoding="
            )
    assert not violations, "bare read_text outside report/: " + "; ".join(violations[:5])


def test_no_bare_write_text_in_package():
    """No `.write_text(...)` call without explicit encoding outside report/."""
    violations = []
    for py in PKG.rglob("*.py"):
        if "report" in py.relative_to(PKG).parts:
            continue
        body = py.read_text(encoding="utf-8")
        for line_no, args in _iter_calls(body, "write_text"):
            if "encoding=" in args:
                continue
            violations.append(
                f"{py.relative_to(REPO)}:{line_no} write_text without encoding="
            )
    assert not violations, "bare write_text outside report/: " + "; ".join(violations[:5])


def test_cli_help_works_under_c_locale(monkeypatch):
    """`apd-gauntlet --help` must run cleanly under LC_ALL=C.

    Uses the in-process Click runner so this works in CI environments
    that lack a .venv/bin/apd-gauntlet executable. Locale variance is
    simulated by patching locale.getpreferredencoding to 'ascii'.
    """
    import locale

    from apd_gauntlet.cli import main as cli
    from click.testing import CliRunner
    monkeypatch.setattr(locale, "getpreferredencoding", lambda *_: "ascii")
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output


def test_validate_runs_under_c_locale(monkeypatch):
    """`apd-gauntlet validate` must run cleanly under LC_ALL=C against a
    shipped run. Uses in-process Click runner (no subprocess)."""
    import locale

    from apd_gauntlet.cli import main as cli
    from click.testing import CliRunner
    monkeypatch.setattr(locale, "getpreferredencoding", lambda *_: "ascii")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["validate", str(REPO / "runs" / "apd-20260527-crapi-owasp-api-top10")],
    )
    assert result.exit_code == 0, result.output
