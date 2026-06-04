"""Shared fixtures for report unit tests."""
from __future__ import annotations

import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]


@pytest.fixture
def example_run() -> pathlib.Path:
    """Path to the canonical synthetic example run shipped under examples/.

    This is the single in-repo fixture run (the gauntlet's own output dir,
    runs/, is gitignored and never shipped). See examples/.../expected/.
    """
    return REPO / "examples" / "apd-20260601-claim-event-bus" / "expected"
