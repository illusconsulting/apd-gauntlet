"""Guard: no apd_gauntlet module resolves schemas/ or domains/ via a repo-root
walk-up. Such reads must go through apd_gauntlet.resources (wheel-safe)."""
from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "tools" / "apd_gauntlet"
_BANNED = {"schemas", "domains"}


def _is_walk_up(node: ast.AST) -> bool:
    """True if node is a chain of >=3 .parent attrs or .parents[n>=3]."""
    hops = 0
    cur = node
    while isinstance(cur, ast.Attribute):
        if cur.attr == "parent":
            hops += 1
        cur = cur.value
    if hops >= 3:
        return True
    if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
            and node.value.attr == "parents"):
        idx = node.slice
        return isinstance(idx, ast.Constant) and isinstance(idx.value, int) and idx.value >= 3
    return False


def _banned_join_offenders(tree: ast.AST) -> list[int]:
    """Line numbers where a walk-up is `/`-joined (or .joinpath'd) to schemas/domains."""
    out: list[int] = []
    for n in ast.walk(tree):
        # X / "schemas"   (and nested: X / "schemas" / "y.json" -> the inner BinOp)
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
            right = n.right
            if isinstance(right, ast.Constant) and right.value in _BANNED and _is_walk_up(n.left):
                out.append(n.lineno)
        # X.joinpath("schemas", ...)
        if (
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "joinpath"
            and n.args
            and isinstance(n.args[0], ast.Constant)
            and n.args[0].value in _BANNED
            and _is_walk_up(n.func.value)
        ):
            out.append(n.lineno)
    return out


def test_no_module_resolves_schemas_or_domains_above_package() -> None:
    offenders: list[str] = []
    for path in PKG.rglob("*.py"):
        if path.name == "resources.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for line in _banned_join_offenders(tree):
            offenders.append(f"{path.relative_to(PKG)}:{line}")
    assert not offenders, (
        "Route schemas/domains reads through apd_gauntlet.resources; offenders:\n"
        + "\n".join(offenders)
    )


def test_detector_flags_a_synthetic_offender() -> None:
    """Proves the guard actually catches the bad pattern (not vacuously passing)."""
    bad = (
        "from pathlib import Path\n"
        'p = Path(__file__).resolve().parent.parent.parent / "schemas" / "x.json"\n'
    )
    assert _banned_join_offenders(ast.parse(bad)), "detector failed to flag a known-bad pattern"
    good = (
        "from pathlib import Path\n"
        'p = Path(__file__).resolve().parent.parent.parent / "report-template"\n'
    )
    assert not _banned_join_offenders(ast.parse(good)), (
        "detector false-positived on a non-schema walk-up"
    )
