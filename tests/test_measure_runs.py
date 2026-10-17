"""measure.runs: the RunSnapshot loader and the inputs digest."""
from __future__ import annotations

import pathlib

from apd_gauntlet.measure.runs import inputs_digest, load_run

REPO = pathlib.Path(__file__).parent.parent
HA = REPO / "examples/apd-20260612-home-assistant/expected"
CEB = REPO / "examples/apd-20260601-claim-event-bus/expected"


def test_load_run_home_assistant():
    s = load_run(HA)
    assert len(s.findings) == 94 and len(s.capabilities) == 28
    assert s.graph_targets["avail-4be2dd70"] == ["recorder_history_db"]
    assert len(s.headlines) == 10 and len(s.headlines[1]) == 8      # merged-1119b0be
    assert s.inputs_sha256 is None                                   # expected/ has no inputs/


def test_inputs_digest_changes_with_content(tmp_path):
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs/a.md").write_text("x")
    d1 = inputs_digest(tmp_path)
    (tmp_path / "inputs/a.md").write_text("y")
    assert d1 != inputs_digest(tmp_path) and len(d1) == 64
