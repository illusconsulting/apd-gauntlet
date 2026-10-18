"""measure.attempts: the ``.apd-state/attempts.yaml`` file and the run-attempts schema."""
from __future__ import annotations

import pathlib

import pytest
import yaml
from apd_gauntlet.measure.attempts import (
    ATTEMPTS_RELPATH,
    Attempts,
    AttemptsError,
    read_attempts,
    write_attempts,
)
from apd_gauntlet.measure.runs import RunLoadError, load_run
from apd_gauntlet.resources import read_schema
from jsonschema import Draft202012Validator

GOOD = {
    "schema_version": 1,
    "recorded_by": "workflow",
    "lens_retries": {"integrity": 1, "availability": 0},
    "first_pass_invalid": ["integrity"],
    "tier_gate_failures": ["20-scalability"],
    "skipped": [],
    "audit_iterations": 2,
    "tier_repairs": {"20-scalability": 1},
    "lens_reruns": {},
}


def test_round_trip(tmp_path):
    write_attempts(tmp_path, GOOD)
    a = read_attempts(tmp_path)
    assert a.first_pass_validator_errors == 2 and a.lens_retries_total == 1
    assert a.audit_iterations == 2
    assert a.tier_repairs_total == 1 and a.lens_reruns_total == 0


def test_absent_is_none(tmp_path):
    assert read_attempts(tmp_path) is None


@pytest.mark.parametrize(
    "bad", [{"lens_retries": {"integrity": -1}}, {"audit_iterations": 0}, {"extra": 1}]
)
def test_invalid_rejected(tmp_path, bad):
    with pytest.raises(AttemptsError):
        write_attempts(tmp_path, {**GOOD, **bad})
    assert not (tmp_path / ".apd-state/attempts.yaml").exists()


# --- beyond the plan's tests: the rest of the Interfaces line ---------------


def test_schema_id_and_required_keys():
    schema = read_schema("run-attempts.schema.json")
    assert schema["$id"] == (
        "https://github.com/illusconsulting/apd-gauntlet/schemas/run-attempts.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(GOOD) == set(schema["properties"])
    Draft202012Validator.check_schema(schema)


def test_relpath_and_returned_path(tmp_path):
    assert pathlib.Path(".apd-state/attempts.yaml") == ATTEMPTS_RELPATH
    path = write_attempts(tmp_path, GOOD)
    assert path == tmp_path / ATTEMPTS_RELPATH
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == GOOD


def test_read_returns_every_field(tmp_path):
    write_attempts(tmp_path, GOOD)
    assert read_attempts(tmp_path) == Attempts(
        recorded_by="workflow",
        lens_retries={"integrity": 1, "availability": 0},
        first_pass_invalid=("integrity",),
        tier_gate_failures=("20-scalability",),
        skipped=(),
        audit_iterations=2,
        tier_repairs={"20-scalability": 1},
        lens_reruns={},
    )


def test_totals_sum_every_entry(tmp_path):
    write_attempts(
        tmp_path,
        {
            **GOOD,
            "lens_retries": {"integrity": 2, "availability": 3},
            "first_pass_invalid": ["integrity", "availability"],
            "tier_gate_failures": [],
            "tier_repairs": {"10-trustworthiness": 2, "20-scalability": 4},
            "lens_reruns": {"integrity": 1, "authenticity": 1},
        },
    )
    a = read_attempts(tmp_path)
    assert a.lens_retries_total == 5 and a.first_pass_validator_errors == 2
    assert a.tier_repairs_total == 6 and a.lens_reruns_total == 2


@pytest.mark.parametrize("key", sorted(GOOD))
def test_every_key_is_required(tmp_path, key):
    data = {k: v for k, v in GOOD.items() if k != key}
    with pytest.raises(AttemptsError, match=key):
        write_attempts(tmp_path, data)
    assert not (tmp_path / ".apd-state").exists()


@pytest.mark.parametrize(
    "bad",
    [
        {"schema_version": 2},
        {"recorded_by": "agent"},
        {"lens_retries": {"integrity": True}},
        {"lens_retries": {"integrity": 1.5}},
        {"lens_retries": {"": 1}},
        {"lens_retries": []},
        {"first_pass_invalid": ["integrity", "integrity"]},
        {"tier_gate_failures": [""]},
        {"skipped": [3]},
        {"skipped": "apd-code-recon"},
        {"audit_iterations": "2"},
        {"audit_iterations": True},
        {"tier_repairs": {"20-scalability": -1}},
        {"lens_reruns": {"integrity": -1}},
        {"lens_reruns": None},
    ],
)
def test_more_invalid_values_rejected(tmp_path, bad):
    with pytest.raises(AttemptsError):
        write_attempts(tmp_path, {**GOOD, **bad})
    assert not (tmp_path / ".apd-state").exists()


def test_non_mapping_rejected(tmp_path):
    with pytest.raises(AttemptsError, match="not of type 'object'"):
        write_attempts(tmp_path, [GOOD])  # type: ignore[arg-type]
    assert not (tmp_path / ".apd-state").exists()


def test_error_lists_every_schema_message(tmp_path):
    with pytest.raises(AttemptsError) as info:
        write_attempts(tmp_path, {**GOOD, "audit_iterations": 0, "lens_retries": {"x": -1}})
    message = str(info.value)
    assert "audit_iterations: 0 is less than the minimum of 1" in message
    assert "lens_retries/x: -1 is less than the minimum of 0" in message


def test_integral_floats_are_written_and_read_as_integers(tmp_path):
    path = write_attempts(
        tmp_path, {**GOOD, "audit_iterations": 2.0, "lens_retries": {"integrity": 1.0}}
    )
    assert "audit_iterations: 2\n" in path.read_text(encoding="utf-8")
    a = read_attempts(tmp_path)
    assert type(a.audit_iterations) is int and type(a.lens_retries["integrity"]) is int


def test_rewrite_replaces_and_a_rejected_write_keeps_the_file(tmp_path):
    write_attempts(tmp_path, GOOD)
    write_attempts(tmp_path, {**GOOD, "audit_iterations": 3})
    with pytest.raises(AttemptsError):
        write_attempts(tmp_path, {**GOOD, "audit_iterations": 0})
    assert read_attempts(tmp_path).audit_iterations == 3
    assert sorted(p.name for p in (tmp_path / ".apd-state").iterdir()) == ["attempts.yaml"]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"audit_iterations: [\n", "invalid YAML"),
        (b"[" * 5000, "nested too deeply to parse"),
        (b"\xff\xfe", "not UTF-8"),
        (b"", "None is not of type 'object'"),
        (yaml.safe_dump({**GOOD, "audit_iterations": 0}).encode(), "minimum of 1"),
        (yaml.safe_dump({**GOOD, "lens_retries": {1: 1}}).encode(), "lens_retries"),
    ],
)
def test_invalid_file_raises_naming_it(tmp_path, content, expected):
    path = tmp_path / ATTEMPTS_RELPATH
    path.parent.mkdir()
    path.write_bytes(content)
    with pytest.raises(AttemptsError, match=expected) as info:
        read_attempts(tmp_path)
    assert str(info.value).startswith(f"{path}:")


def test_unreadable_file_raises_naming_it(tmp_path):
    (tmp_path / ATTEMPTS_RELPATH).mkdir(parents=True)  # a directory where the file goes
    with pytest.raises(AttemptsError) as info:
        read_attempts(tmp_path)
    assert str(info.value).startswith(f"{tmp_path / ATTEMPTS_RELPATH}: cannot read")


def test_unwritable_location_raises(tmp_path):
    (tmp_path / ".apd-state").write_text("not a directory")
    with pytest.raises(AttemptsError, match="cannot write"):
        write_attempts(tmp_path, GOOD)


def test_load_run_carries_the_attempts(make_run):
    run = make_run("run")
    assert load_run(run).attempts is None
    write_attempts(run, GOOD)
    assert load_run(run).attempts == read_attempts(run)


def test_load_run_maps_an_invalid_attempts_file_to_run_load_error(make_run):
    run = make_run("run")
    (run / ".apd-state").mkdir()
    (run / ATTEMPTS_RELPATH).write_text("audit_iterations: 0\n", encoding="utf-8")
    with pytest.raises(RunLoadError) as info:
        load_run(run)
    assert str(info.value).startswith(f"{run / ATTEMPTS_RELPATH}:")
