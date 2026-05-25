"""Integration test: the bundled example must validate cleanly."""

from __future__ import annotations

import pathlib
import subprocess


def test_claim_event_bus_example_validates():
    repo = pathlib.Path(__file__).parent.parent
    example = repo / "examples" / "apd-20260601-claim-event-bus" / "expected"
    result = subprocess.run(
        ["apd-gauntlet", "validate", str(example)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Validation failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
