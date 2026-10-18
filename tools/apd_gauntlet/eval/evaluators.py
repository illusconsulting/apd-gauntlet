"""The evaluator registry (registry R2): ``apd_gauntlet.eval.evaluators``.

An evaluator scores one corpus entry against its labels and returns an
``EvalResult``: integer ``counts`` that can be summed over entries, and the
``metrics`` they give. ``derive`` turns summed counts back into metrics, so
``eval run`` can report corpus totals. Evaluators register by name at import;
``load_builtin_evaluators`` imports the modules that ship with the engine.

A name is used as a directory under ``eval/results/``, so it must match
``^[a-z0-9][a-z0-9-]*$``.
"""
from __future__ import annotations

import importlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from .corpus import CorpusEntry, Labels

NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")

# Modules that register built-in evaluators when imported.
_BUILTIN_MODULES: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvalResult:
    entry_id: str
    counts: dict[str, int]
    metrics: dict[str, float | None]
    notes: tuple[str, ...] = ()
    derive: Callable[[Mapping[str, int]], dict[str, float | None]] | None = field(
        default=None, compare=False, repr=False
    )


Evaluator = Callable[[CorpusEntry, Labels], EvalResult]
EVALUATORS: dict[str, Evaluator] = {}


def register(name: str, fn: Evaluator) -> None:
    """Register ``fn`` as ``name``; ``ValueError`` for a taken or malformed name."""
    if not NAME_PATTERN.fullmatch(name):
        raise ValueError(f"evaluator name {name!r} does not match {NAME_PATTERN.pattern}")
    if name in EVALUATORS:
        raise ValueError(f"evaluator {name!r} is already registered")
    EVALUATORS[name] = fn


def get(name: str) -> Evaluator:
    """The evaluator registered as ``name``; ``KeyError`` lists the registered names."""
    try:
        return EVALUATORS[name]
    except KeyError:
        registered = ", ".join(sorted(EVALUATORS)) or "none"
        raise KeyError(f"unknown evaluator {name!r}; registered: {registered}") from None


def load_builtin_evaluators() -> None:
    """Import the built-in evaluator modules; a second call changes nothing."""
    for module in _BUILTIN_MODULES:
        importlib.import_module(module)
