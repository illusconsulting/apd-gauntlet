from __future__ import annotations

from apd_gauntlet import resources


def test_schemas_dir_has_defs_and_finding() -> None:
    sd = resources.schemas_dir()
    assert (sd / "_defs.schema.json").is_file()
    assert (sd / "finding.schema.json").is_file()
    assert sum(1 for _ in sd.glob("*.schema.json")) >= 40


def test_domains_dir_has_pbm_pack() -> None:
    assert (resources.domains_dir() / "pbm" / "domain.yaml").is_file()


def test_read_schema_parses() -> None:
    assert resources.read_schema("domain.schema.json").get("$id")


def test_read_prompt_repair_is_js_safe_and_has_placeholders() -> None:
    text = resources.read_prompt("repair")
    for ph in ("{{RUN_DIR}}", "{{FILE}}", "{{ERRORS}}"):
        assert ph in text
    assert "'" not in text and "\\" not in text
