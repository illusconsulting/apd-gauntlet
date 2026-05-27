"""Shared fixtures for report unit tests."""
from __future__ import annotations

import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]


@pytest.fixture
def legacy_example_run() -> pathlib.Path:
    """Path to the canonical example run shipped in the repo."""
    return REPO / "runs" / "apd-legacy-example-run"
