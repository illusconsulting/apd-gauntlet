"""canonicalize mints the ``cev-`` (code-evidence index) and ``tm-`` (normalized threat
model) ids and the derived ``inferred_apd_goals``; ``validate`` requires them.

Review Focus 3: an id that is already present is never rewritten, because findings,
``c4-recon.yaml`` and tmeval keys may already cite it.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import yaml
from apd_gauntlet.canonicalize import canonicalize_run
from apd_gauntlet.cli import main
from apd_gauntlet.linters import compute_cev_id, compute_tm_entry_id
from apd_gauntlet.resources import read_schema
from apd_gauntlet.threat_model.author import entry_id_for
from apd_gauntlet.threat_model.mappings import linddun_letter_to_apd_goals
from apd_gauntlet.validate import build_registry
from click.testing import CliRunner
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parent.parent
FIX = REPO / "tests" / "fixtures"

ENTRY = {"qualified_name": "svc.auth.verify", "kind": "function", "file_path": "src/auth.py",
         "line_range": "L10-L20", "excerpt": "if not verify(token): raise",
         "apd_relevance": ["authenticity"]}
TM = {"asset": "pricing-service", "threat": "Spoofed caller at the pricing API",
      "source_locator": "inventory:pricing-service", "extraction_confidence": "medium",
      "methodology": "stride", "framework_refs": {"stride_letter": "S"}, "mitigation": "mTLS"}


def _write(run, name, doc):
    p = run / "00-context" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return p


def _index_doc(entries, repos=None):
    idx = {"indexed_commit_sha": "abc1234", "cbm_project": "p",
           "generated_at": "2026-10-11T00:00:00Z", "entries": entries}
    return {"code_evidence_index": {**idx, "repos": repos} if repos else idx}


def _tm_doc(entries, generated_by="threat_model_author"):
    return {"schema_version": 1, "generated_by": generated_by, "methodology": "stride",
            "source_artifact": "00-context/asset-inventory.yaml", "entries": entries}


def _index(run, entries, repos=None):
    return _write(run, "code-evidence-index.yaml", _index_doc(entries, repos))


def _tm(run, entries, name="threat-model-normalized.yaml", generated_by="threat_model_author"):
    return _write(run, name, _tm_doc(entries, generated_by))


def _entries(path):
    doc = yaml.safe_load(path.read_text())
    return (doc.get("code_evidence_index") or doc)["entries"]


def test_cev_formula():
    expected = "cev-" + hashlib.sha256(b"svc.auth.verify|L10-L20").hexdigest()[:8]
    assert compute_cev_id("svc.auth.verify", "L10-L20") == expected
    assert compute_cev_id("a", "L1", repo="core") == (
        "cev-" + hashlib.sha256(b"core|a|L1").hexdigest()[:8]
    )


def test_tm_formula_matches_skeleton_helper():
    expected = "tm-" + hashlib.sha256(b"atl").hexdigest()[:8]
    assert compute_tm_entry_id("a", "t", "l") == entry_id_for("a", "t", "l") == expected


def test_mints_missing_cev_id(tmp_path):
    p = _index(tmp_path, [dict(ENTRY)])
    res = canonicalize_run(tmp_path)
    e = _entries(p)[0]
    assert e["id"] == compute_cev_id("svc.auth.verify", "L10-L20") and list(e)[0] == "id"
    assert res.context_ids_minted == 1


def test_multi_repo_ids_include_repo(tmp_path):
    repos = [{"cbm_project": r, "indexed_commit_sha": "abc1234"} for r in ("core", "supervisor")]
    entries = [dict(ENTRY, repo="core"), dict(ENTRY, repo="supervisor")]
    p = _index(tmp_path, entries, repos=repos)
    canonicalize_run(tmp_path)
    ids = [e["id"] for e in _entries(p)]
    assert ids == [
        compute_cev_id("svc.auth.verify", "L10-L20", repo=r) for r in ("core", "supervisor")
    ]
    assert ids[0] != ids[1]


def test_repo_is_ignored_when_the_index_declares_no_repos(tmp_path):
    p = _index(tmp_path, [dict(ENTRY, repo="core")])
    canonicalize_run(tmp_path)
    assert _entries(p)[0]["id"] == compute_cev_id("svc.auth.verify", "L10-L20")


def test_mints_tm_entry_id_and_stride_goals(tmp_path):
    p = _tm(tmp_path, [dict(TM)])
    canonicalize_run(tmp_path)
    e = _entries(p)[0]
    assert e["entry_id"] == entry_id_for(TM["asset"], TM["threat"], TM["source_locator"])
    assert e["inferred_apd_goals"] == ["authenticity"]


def test_linddun_maestro_and_authored_goals(tmp_path):
    p = _tm(tmp_path, [dict(TM, threat="t1", methodology="linddun",
                            framework_refs={"linddun_letter": "L"}),
                       dict(TM, threat="t2", methodology="maestro", framework_refs={}),
                       dict(TM, threat="t3", inferred_apd_goals=["integrity", "availability"])])
    canonicalize_run(tmp_path)
    goals = [e["inferred_apd_goals"] for e in _entries(p)]
    assert goals == [linddun_letter_to_apd_goals("L"), [], ["integrity", "availability"]]


def test_authored_goals_are_never_replaced_by_the_letter_mapping(tmp_path):
    # The recon agent sets goals by judgement (PBM N_compliance override, attack-tree,
    # MAESTRO, free-form); an authored value, even [], must survive a STRIDE letter.
    authored = dict(TM, entry_id="tm-0badc0de", inferred_apd_goals=[])
    p = _tm(tmp_path, [authored])
    before = p.read_bytes()
    assert canonicalize_run(tmp_path).context_ids_minted == 0
    assert p.read_bytes() == before
    p = _tm(tmp_path, [dict(TM, inferred_apd_goals=[]),
                       dict(TM, threat="t2", inferred_apd_goals=["integrity"])])
    assert canonicalize_run(tmp_path).context_ids_minted == 2
    entries = _entries(p)
    assert [e["inferred_apd_goals"] for e in entries] == [[], ["integrity"]]
    assert all(e["entry_id"].startswith("tm-") for e in entries)


def test_inferred_apd_goals_is_agent_authorable_in_the_schema():
    props = read_schema("threat-model-normalized.schema.json")["properties"]["entries"]["items"]
    assert "readOnly" not in props["properties"]["inferred_apd_goals"]
    assert props["properties"]["entry_id"]["readOnly"] is True
    assert "inferred_apd_goals" not in props["required"]


def test_supplied_sibling_is_minted_too(tmp_path):
    p = _tm(tmp_path, [dict(TM)], name="threat-model-supplied-normalized.yaml",
            generated_by="threat_model_recon")
    canonicalize_run(tmp_path)
    assert _entries(p)[0]["entry_id"].startswith("tm-")


def test_existing_context_ids_are_never_rewritten(tmp_path):  # Review Focus 3
    run = shutil.copytree(REPO / "examples/apd-20260612-home-assistant/expected", tmp_path / "run")
    names = ("code-evidence-index.yaml", "threat-model-normalized.yaml", "c4-recon.yaml")
    files = [run / "00-context" / n for n in names]
    before = [f.read_bytes() for f in files]
    assert canonicalize_run(run).context_ids_minted == 0
    assert [f.read_bytes() for f in files] == before


def test_existing_ids_survive_when_a_sibling_entry_is_minted(tmp_path):
    kept = dict(ENTRY, id="cev-a1000008")
    p = _index(tmp_path, [kept, dict(ENTRY, qualified_name="svc.auth.other")])
    canonicalize_run(tmp_path)
    ids = [e["id"] for e in _entries(p)]
    assert ids[0] == "cev-a1000008"
    assert ids[1] == compute_cev_id("svc.auth.other", "L10-L20")


def test_second_pass_is_a_no_op(tmp_path):
    p = _index(tmp_path, [dict(ENTRY)])
    canonicalize_run(tmp_path)
    first = p.read_bytes()
    assert canonicalize_run(tmp_path).context_ids_minted == 0 and p.read_bytes() == first


def test_context_ids_minted_counts_ids_not_files(tmp_path):
    _index(tmp_path, [dict(ENTRY, qualified_name=f"svc.f{i}") for i in range(3)])
    _tm(tmp_path, [dict(TM, threat="t1"), dict(TM, threat="t2")])
    _tm(tmp_path, [dict(TM, threat="t3")], name="threat-model-supplied-normalized.yaml",
        generated_by="threat_model_recon")
    assert canonicalize_run(tmp_path).context_ids_minted == 6


def test_filling_only_goals_rewrites_the_file_but_counts_no_id(tmp_path):
    p = _tm(tmp_path, [dict(TM, entry_id="tm-0badc0de")])
    res = canonicalize_run(tmp_path)
    e = _entries(p)[0]
    assert e["entry_id"] == "tm-0badc0de" and e["inferred_apd_goals"] == ["authenticity"]
    assert res.context_ids_minted == 0


def test_missing_source_locator_hashes_as_empty(tmp_path):
    entry = {k: v for k, v in TM.items() if k != "source_locator"}
    p = _tm(tmp_path, [entry])
    canonicalize_run(tmp_path)
    assert _entries(p)[0]["entry_id"] == compute_tm_entry_id(TM["asset"], TM["threat"], "")


def test_unparseable_context_file_is_reported(tmp_path):
    (tmp_path / "00-context").mkdir()
    (tmp_path / "00-context/code-evidence-index.yaml").write_text(
        "code_evidence_index: [unclosed\n"
    )
    assert any(
        "code-evidence-index.yaml" in p for p, _ in canonicalize_run(tmp_path).parse_errors
    )


def test_unparseable_context_file_is_left_untouched_and_the_pass_continues(tmp_path):
    bad = tmp_path / "00-context" / "code-evidence-index.yaml"
    bad.parent.mkdir(parents=True)
    bad.write_text("code_evidence_index: [unclosed\n")
    p = _tm(tmp_path, [dict(TM)])
    res = canonicalize_run(tmp_path)
    assert bad.read_text() == "code_evidence_index: [unclosed\n"
    assert res.context_parse_errors == ["00-context/code-evidence-index.yaml"]
    assert _entries(p)[0]["entry_id"].startswith("tm-") and res.context_ids_minted == 1


def test_cli_reports_minted_ids_only_when_there_are_some(tmp_path):
    _index(tmp_path, [dict(ENTRY)])
    first = CliRunner().invoke(main, ["canonicalize", str(tmp_path)])
    assert first.exit_code == 0 and ", 1 context ids minted" in first.output
    second = CliRunner().invoke(main, ["canonicalize", str(tmp_path)])
    assert second.exit_code == 0 and "context ids minted" not in second.output


def test_relaxed_schemas_accept_id_less_entries_but_reject_bad_ids():
    reg = build_registry()
    cev = Draft202012Validator(read_schema("code-evidence-index.schema.json"), registry=reg)
    tm = Draft202012Validator(read_schema("threat-model-normalized.schema.json"), registry=reg)
    assert list(cev.iter_errors(_index_doc([dict(ENTRY)]))) == []
    assert list(tm.iter_errors(_tm_doc([dict(TM)]))) == []
    assert list(cev.iter_errors(_index_doc([dict(ENTRY, id="cev-XYZ")])))
    assert list(tm.iter_errors(_tm_doc([dict(TM, entry_id="tm-nothex!")])))


def test_validate_requires_minted_context_ids(tmp_path):
    run = shutil.copytree(FIX / "runs/clean-run", tmp_path / "run")
    _index(run, [dict(ENTRY)])
    r = CliRunner().invoke(main, ["validate", str(run)])
    assert r.exit_code == 1 and "has no id" in r.output
    canonicalize_run(run)
    assert "has no id" not in CliRunner().invoke(main, ["validate", str(run)]).output


def test_validate_names_the_file_and_entry_and_the_fix(tmp_path):
    run = shutil.copytree(FIX / "runs/clean-run", tmp_path / "run")
    _index(run, [dict(ENTRY)])
    _tm(run, [dict(TM, entry_id="tm-0badc0de"), dict(TM, threat="t2")])
    out = CliRunner().invoke(main, ["validate", str(run), "--errors-only"]).output
    msgs = [ln.split(": ", 1)[1] for ln in out.splitlines() if "context id missing" in ln]
    suffix = "; run 'apd-gauntlet canonicalize'"
    assert msgs == [
        "context id missing: 00-context/code-evidence-index.yaml: entries[0] has no id" + suffix,
        "context id missing: 00-context/threat-model-normalized.yaml: entries[0]"
        " has no inferred_apd_goals" + suffix,
        "context id missing: 00-context/threat-model-normalized.yaml: entries[1]"
        " has no entry_id and inferred_apd_goals" + suffix,
    ], out


def test_adr_0020_records_the_mint_when_absent_amendment():
    text = next((REPO / "docs" / "adrs").glob("0020-*.md")).read_text(encoding="utf-8")
    section = text.split("## Amendment (v1.7.1)", 1)[1]
    assert "cev-" in section and "tm-" in section and "minted only when absent" in section
