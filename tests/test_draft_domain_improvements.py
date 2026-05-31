"""Tests for the on-demand draft-domain-improvements command (§6, §12)."""
from __future__ import annotations

import pathlib
import subprocess

import yaml
from apd_gauntlet.cli import main
from apd_gauntlet.linters import compute_improvement_id
from click.testing import CliRunner

FROZEN = pathlib.Path("tests/fixtures/frozen-domains").resolve()


def _record(itype, pack, tfile, ref, snippet, *, kind="asset_inventory",
            apd_goal=None, hint=None, priority="high"):
    rid = compute_improvement_id(itype, pack, tfile, ref)
    rec = {
        "id": rid,
        "improvement_type": itype,
        "target_pack": pack,
        "target_file": tfile,
        "source": "deterministic" if kind == "asset_inventory" else "judgment",
        "priority": priority,
        "evidence": [{"kind": kind, "ref": ref}],
        "rationale": "The run exercised something no selected pack fully declares here.",
        "suggested_action": "add the missing item to the pack",
        "draft_snippet": snippet,
    }
    if apd_goal:
        rec["apd_goal"] = apd_goal
    if hint:
        rec["insertion_hint"] = hint
    return rec


def _write_run(tmp_path, records, examined=("api-security", "pbm")):
    run_dir = tmp_path / "run"
    (run_dir / "40-synthesis").mkdir(parents=True)
    doc = {
        "schema_version": 1,
        "generated_by": "domain-auditor",
        "examined_domains": list(examined),
        "improvements": records,
    }
    (run_dir / "40-synthesis" / "domain-improvements.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False), encoding="utf-8"
    )
    return run_dir


def _invoke(run_dir, *extra):
    return CliRunner().invoke(
        main,
        ["draft-domain-improvements", str(run_dir),
         "--domains-dir", str(FROZEN), *extra],
    )


def _git_apply_check(patch_path, frozen_copy):
    """Return True if `git apply --check` accepts the patch against frozen_copy."""
    r = subprocess.run(
        ["git", "apply", "--check", str(patch_path)],
        cwd=frozen_copy, capture_output=True, text=True,
    )
    return r.returncode == 0, r.stderr


def _frozen_git_tree(tmp_path):
    """A git-initialized copy of the frozen packs (parent of a `domains/` dir),
    so `git apply --check` on an a/domains/... patch resolves."""
    import shutil
    root = tmp_path / "tree"
    (root / "domains").mkdir(parents=True)
    for pack in ("api-security", "pbm"):
        shutil.copytree(FROZEN / pack, root / "domains" / pack)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "frozen"], cwd=root, check=True)
    return root


def test_happy_path_domain_yaml(tmp_path):
    rec = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: payment_methods_store\n  description: \"PCI-scope cardholder data store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [rec])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 drafted, 0 dropped" in result.output
    patch = run_dir / "40-synthesis" / "domain-improvements.patch"
    assert patch.exists()
    text = patch.read_text()
    assert "a/domains/api-security/domain.yaml" in text
    assert "payment_methods_store" in text
    tree = _frozen_git_tree(tmp_path)
    ok, err = _git_apply_check(patch, tree)
    assert ok, err


def test_determinism_byte_identical(tmp_path):
    rec = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: payment_methods_store\n  description: \"PCI-scope cardholder data store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [rec])
    _invoke(run_dir, "--out", str(run_dir / "a.patch"))
    _invoke(run_dir, "--out", str(run_dir / "b.patch"))
    assert (run_dir / "a.patch").read_text() == (run_dir / "b.patch").read_text()


def test_new_file_common_pattern(tmp_path):
    # availability.md is absent from the frozen api-security pack.
    rec = _record(
        "missing_common_pattern", "api-security", "common-patterns/availability.md",
        "avail-11112222", "### Rate limiting\nIllustrative availability pattern.\n",
        kind="finding", apd_goal="availability",
    )
    run_dir = _write_run(tmp_path, [rec])
    # The cross-file validator would flag the finding ref; the draft command does
    # NOT re-resolve evidence — it trusts the captured artifact. So no corpus needed.
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert "new file mode 100644" in patch
    assert "--- /dev/null" in patch
    assert "b/domains/api-security/common-patterns/availability.md" in patch
    # Coupled domain.yaml include edit appears (includes did not glob common-patterns/*.md).
    assert "a/domains/api-security/domain.yaml" in patch
    tree = _frozen_git_tree(tmp_path)
    ok, err = _git_apply_check(run_dir / "40-synthesis" / "domain-improvements.patch", tree)
    assert ok, err


def test_new_file_common_pattern_glob_covered_no_domain_yaml_edit(tmp_path):
    # pbm's includes already globs common-patterns/*.md, so a new common-patterns
    # file needs NO domain.yaml edit (_ensure_include_glob `covered` short-circuit).
    # availability.md is absent from the frozen pbm pack.
    rec = _record(
        "missing_common_pattern", "pbm", "common-patterns/availability.md",
        "avail-33334444", "### Bulkheads\nIllustrative availability pattern.\n",
        kind="finding", apd_goal="availability",
    )
    run_dir = _write_run(tmp_path, [rec])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert "new file mode 100644" in patch
    assert "b/domains/pbm/common-patterns/availability.md" in patch
    # The glob already covers it, so NO domain.yaml modify hunk for pbm.
    assert "a/domains/pbm/domain.yaml" not in patch
    tree = _frozen_git_tree(tmp_path)
    ok, err = _git_apply_check(run_dir / "40-synthesis" / "domain-improvements.patch", tree)
    assert ok, err


def test_drop_on_fail_domain_yaml_target(tmp_path):
    bad = _record(  # crown_jewels item missing required `description`
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-bad00000",
        "- pattern: broken_store\n", hint={"yaml_path": "crown_jewels"}, priority="medium",
    )
    good = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: payment_methods_store\n  description: \"PCI-scope cardholder data store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [bad, good])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 drafted, 1 dropped" in result.output
    assert bad["id"] in result.output  # dropped id reported
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert "payment_methods_store" in patch
    assert "broken_store" not in patch


def test_drop_on_fail_md_target_reserved_marker(tmp_path):
    # An .md snippet introducing the builder's reserved `## Domain:` marker is
    # dropped by the draft.py structural check (validate-domain does NOT gate .md).
    bad = _record(
        "missing_severity_clause", "api-security", "severity-rubric.md", "conf-22223333",
        "## Domain: spoofed — Source: `x`\nmalicious heading collision\n",
        kind="finding", priority="medium",
        hint={"markdown_section": {"level": 2, "text": "High"}},
    )
    run_dir = _write_run(tmp_path, [bad])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 dropped" in result.output
    assert "markdown structural check" in result.output


def test_rebuild_isolation_second_snippet_dropped(tmp_path):
    good = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: payment_methods_store\n  description: \"PCI-scope cardholder data store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    bad = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-bad00000",
        "- pattern: broken_store\n", hint={"yaml_path": "crown_jewels"}, priority="medium",
    )
    run_dir = _write_run(tmp_path, [good, bad])
    result = _invoke(run_dir)
    assert "1 drafted, 1 dropped" in result.output


def test_already_declared_duplicate_dropped(tmp_path):
    dup = _record(  # audit_log_store already declared in frozen api-security
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-dup00000",
        "- pattern: audit_log_store\n  description: \"Duplicate of an existing crown jewel.\"\n",
        hint={"yaml_path": "crown_jewels"}, priority="medium",
    )
    run_dir = _write_run(tmp_path, [dup])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "already declared in api-security" in result.output


def test_unknown_target_pack_dropped(tmp_path):
    rec = _record(
        "missing_crown_jewel", "no-such-pack", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: x_store\n  description: \"A store in a pack that does not exist.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [rec], examined=("no-such-pack",))
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "unknown target_pack" in result.output


def test_no_opportunities_path(tmp_path):
    run_dir = _write_run(tmp_path, [])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "0 opportunities selected; nothing to draft" in result.output
    assert not (run_dir / "40-synthesis" / "domain-improvements.patch").exists()


def test_id_filter_selects_subset(tmp_path):
    a = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: payment_methods_store\n  description: \"PCI-scope cardholder data store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    b = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-2b3c4d5e",
        "- pattern: secrets_store\n  description: \"Secrets store grounded in the inventory.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [a, b])
    result = _invoke(run_dir, "--id", a["id"])
    assert "1 drafted" in result.output
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert "payment_methods_store" in patch and "secrets_store" not in patch


def test_regulatory_anchor_happy_path(tmp_path):
    # A new regulatory_anchors string lands (the scalar-append branch, distinct from
    # the mapping-item append the crown-jewel tests exercise).
    rec = _record(
        "missing_regulatory_anchor", "api-security", "domain.yaml", "conf-aaaa1111",
        "PCI DSS v4.0\n", kind="finding",
        hint={"yaml_path": "regulatory_anchors"}, priority="medium",
    )
    run_dir = _write_run(tmp_path, [rec])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 drafted, 0 dropped" in result.output
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert "PCI DSS v4.0" in patch


def test_regulatory_anchor_already_declared_dropped(tmp_path):
    # "OWASP API Top 10 (2023)" is already in the frozen api-security regulatory_anchors.
    dup = _record(
        "missing_regulatory_anchor", "api-security", "domain.yaml", "conf-bbbb2222",
        "OWASP API Top 10 (2023)\n", kind="finding",
        hint={"yaml_path": "regulatory_anchors"}, priority="medium",
    )
    run_dir = _write_run(tmp_path, [dup])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "already declared in api-security" in result.output


def test_regulatory_anchor_shape_mismatch_dropped(tmp_path):
    # A regulatory_anchors snippet that safe_loads to a MAPPING (not a string) is
    # dropped with the scalar-shape reason 'expected one string'.
    bad = _record(
        "missing_regulatory_anchor", "api-security", "domain.yaml", "conf-cccc3333",
        "- anchor: HIPAA\n  note: wrong shape\n", kind="finding",
        hint={"yaml_path": "regulatory_anchors"}, priority="medium",
    )
    run_dir = _write_run(tmp_path, [bad])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 dropped" in result.output
    assert "expected one string" in result.output


def test_md_unbalanced_code_fence_dropped(tmp_path):
    # Structural-check branch (a): a single unbalanced ``` fence.
    bad = _record(
        "missing_severity_clause", "api-security", "severity-rubric.md", "conf-dddd4444",
        "```\nunterminated fence\n", kind="finding", priority="medium",
        hint={"markdown_section": {"level": 2, "text": "High"}},
    )
    run_dir = _write_run(tmp_path, [bad])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 dropped" in result.output
    assert "unbalanced code fences" in result.output


def test_md_oversized_snippet_dropped(tmp_path):
    # Structural-check branch (c): a snippet over _MAX_SNIPPET_BYTES (8192).
    bad = _record(
        "missing_severity_clause", "api-security", "severity-rubric.md", "conf-eeee5555",
        "- **Harm** — " + ("x" * 9000) + "\n", kind="finding", priority="medium",
        hint={"markdown_section": {"level": 2, "text": "High"}},
    )
    run_dir = _write_run(tmp_path, [bad])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 dropped" in result.output
    assert "snippet exceeds size cap" in result.output


def test_md_retarget_eof_fallback_on_no_heading_match(tmp_path):
    # §6.3 EOF fallback: an insertion_hint whose heading matches ZERO headings in the
    # frozen file. The snippet still LANDS (drafted, not dropped) under a generated
    # '## Captured improvement (<dimpr-id>)' heading, and RETARGETED is surfaced.
    rec = _record(
        "missing_severity_clause", "api-security", "severity-rubric.md", "conf-ffff6666",
        "- **Novel harm** — disrupts a service tier the rubric does not name.\n",
        kind="finding", priority="medium",
        hint={"markdown_section": {"level": 2, "text": "Nonexistent Heading"}},
    )
    run_dir = _write_run(tmp_path, [rec])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 drafted, 0 dropped" in result.output
    assert f"RETARGETED {rec['id']}" in result.output
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert f"## Captured improvement ({rec['id']})" in patch
    assert "Novel harm" in patch


def test_invalid_target_pack_name_dropped(tmp_path):
    # ACT-path defence-in-depth (Guard 0): a corrupted artifact whose target_pack is a
    # traversal name is dropped with 'invalid target_pack name' BEFORE any path build,
    # so the §12 path-safety claim holds at draft time too. We bypass the schema by
    # hand-writing the doc (the schema would reject '../x' at capture, but the draft
    # command does NOT re-validate the on-disk artifact).
    run_dir = tmp_path / "run"
    (run_dir / "40-synthesis").mkdir(parents=True)
    (run_dir / "40-synthesis" / "domain-improvements.yaml").write_text(
        "schema_version: 1\n"
        "generated_by: domain-auditor\n"
        "examined_domains:\n  - api-security\n"
        "improvements:\n"
        "  - id: dimpr-00000000\n"
        "    improvement_type: missing_crown_jewel\n"
        "    target_pack: ../x\n"
        "    target_file: domain.yaml\n"
        "    source: deterministic\n    priority: medium\n"
        "    evidence:\n      - kind: asset_inventory\n        ref: asset-1a2b3c4d\n"
        "    rationale: \"corrupted artifact carrying a traversal pack name\"\n"
        "    suggested_action: \"must be dropped, not path-built\"\n"
        "    draft_snippet: \"- pattern: x\\n  description: escaping pack name\"\n",
        encoding="utf-8",
    )
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "invalid target_pack name" in result.output
    assert not (run_dir / "40-synthesis" / "domain-improvements.patch").exists()


def test_inline_flow_blocks_append_unit():
    """The up-front anchorability check returns True only for populated/commented inline
    flow lists; the un-inline cases (`[]`/`[ ]`/bare header) and key-absent return False."""
    from apd_gauntlet.synthesis.draft import _inline_flow_blocks_append

    assert _inline_flow_blocks_append('regulatory_anchors: ["HIPAA"]\n', "regulatory_anchors")
    assert _inline_flow_blocks_append("regulatory_anchors: [HIPAA, GDPR]\n", "regulatory_anchors")
    assert _inline_flow_blocks_append("regulatory_anchors: []  # none\n", "regulatory_anchors")
    # Un-inline / safe shapes -> False (still block-appendable as today).
    assert not _inline_flow_blocks_append("regulatory_anchors: []\n", "regulatory_anchors")
    assert not _inline_flow_blocks_append("regulatory_anchors: [ ]\n", "regulatory_anchors")
    assert not _inline_flow_blocks_append(
        'regulatory_anchors:\n  - "OWASP API Top 10 (2023)"\n', "regulatory_anchors")
    # Key absent -> False (the append-fresh-block path handles that).
    assert not _inline_flow_blocks_append("crown_jewels:\n  - pattern: x\n", "regulatory_anchors")


def _inline_flow_domains_dir(tmp_path):
    """A --domains-dir copy of the frozen packs whose api-security pack has a POPULATED
    INLINE FLOW `regulatory_anchors` list (the exotic shape that used to crash the
    unguarded validate-domain load). The pbm pack is left as a block-list pack so a
    second, VALID opportunity can still be drafted in the same run."""
    import shutil
    ddir = tmp_path / "domains-in"
    shutil.copytree(FROZEN, ddir)
    meta = ddir / "api-security" / "domain.yaml"
    raw = meta.read_text(encoding="utf-8")
    raw = raw.replace(
        'regulatory_anchors:\n  - "OWASP API Top 10 (2023)"\n',
        'regulatory_anchors: ["OWASP API Top 10 (2023)"]\n',
    )
    assert 'regulatory_anchors: ["OWASP API Top 10 (2023)"]' in raw, "fixture mutation failed"
    meta.write_text(raw, encoding="utf-8")
    return ddir


def test_inline_flow_list_drops_cleanly_no_crash(tmp_path):
    """An EXISTING pack whose target key is a populated INLINE FLOW list must DROP cleanly
    (no crash / no traceback, exit 0) with the documented hand-edit reason — while a
    SEPARATE valid opportunity in another pack is still drafted into the emitted patch.
    Previously the textual splice produced unparseable YAML and validate-domain's unguarded
    yaml.safe_load raised an unhandled ParserError, crashing the whole command."""
    ddir = _inline_flow_domains_dir(tmp_path)

    inline_flow = _record(  # targets the inline-flow regulatory_anchors in api-security
        "missing_regulatory_anchor", "api-security", "domain.yaml", "conf-inline01",
        "PCI DSS v4.0\n", kind="finding", priority="medium",
        hint={"yaml_path": "regulatory_anchors"},
    )
    valid = _record(  # a block-list crown_jewel in pbm — a normal, draftable insert
        "missing_crown_jewel", "pbm", "domain.yaml", "asset-9f9f9f9f",
        "- pattern: claims_adjudication_store\n"
        "  description: \"Adjudicated pharmacy claims record store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [inline_flow, valid])
    result = CliRunner().invoke(
        main,
        ["draft-domain-improvements", str(run_dir), "--domains-dir", str(ddir)],
    )
    # No crash / no traceback: the command exits 0.
    assert result.exit_code == 0, result.output
    assert "Traceback" not in result.output

    # The inline-flow opportunity is DROPPED with the clean reason...
    assert inline_flow["id"] in result.output
    assert "cannot insert into inline/flow-style list at regulatory_anchors" in result.output
    assert "1 drafted, 1 dropped" in result.output

    # ...and the OTHER valid opportunity is still drafted into the emitted patch.
    patch = (run_dir / "40-synthesis" / "domain-improvements.patch").read_text()
    assert "claims_adjudication_store" in patch
    assert "PCI DSS v4.0" not in patch
    assert "a/domains/pbm/domain.yaml" in patch


def test_command_registered():
    result = CliRunner().invoke(main, ["draft-domain-improvements", "--help"])
    assert result.exit_code == 0
    assert "draft-domain-improvements" in result.output or "Usage" in result.output


def _domain_yaml_hunk_lines(patch_text, pack):
    """Return the body lines (` `/`+`/`-` prefixed) of the per-file modify hunk for the
    given pack's domain.yaml, excluding the `---`/`+++`/`@@` headers. An existing-file
    hunk starts at its `--- a/domains/<pack>/domain.yaml` line (no `diff --git` header —
    that is emitted only for the new-file branch)."""
    lines = patch_text.splitlines()
    start = next(
        i for i, ln in enumerate(lines)
        if ln == f"--- a/domains/{pack}/domain.yaml"
    )
    body = []
    for ln in lines[start + 1:]:
        # The next per-file hunk begins with its own `diff --git` or `--- a/...` header.
        if ln.startswith(("diff --git ", "--- ")):
            break
        if ln.startswith(("+++ ", "@@ ")):
            continue
        body.append(ln)
    return body


def test_domain_yaml_diff_is_minimal(tmp_path):
    """The domain.yaml hunk for an existing-pack list insert is a MINIMAL textual diff:
    a pure addition (0 removed lines) of exactly the new item, leaving every other line
    byte-identical — and it still `git apply --check`s clean. This is Subsystem B's core
    value (a clean, reviewable patch); the old whole-file safe_dump round-trip reformatted
    ~70 lines for a 1-line insert."""
    rec = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: payment_methods_store\n  description: \"PCI-scope cardholder data store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [rec])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    patch_path = run_dir / "40-synthesis" / "domain-improvements.patch"
    patch = patch_path.read_text()

    body = _domain_yaml_hunk_lines(patch, "api-security")
    added = [ln[1:] for ln in body if ln.startswith("+")]
    removed = [ln[1:] for ln in body if ln.startswith("-")]
    # Pure addition (no reformat reflow): zero removed lines, exactly the new item added.
    assert removed == [], f"expected 0 removed lines, got {removed!r}"
    assert added == [
        "  - pattern: payment_methods_store",
        '    description: "PCI-scope cardholder data store."',
    ], f"added lines were not exactly the new item: {added!r}"

    # And the minimal patch still applies cleanly.
    tree = _frozen_git_tree(tmp_path)
    ok, err = _git_apply_check(patch_path, tree)
    assert ok, err


def test_live_domains_tree_byte_unchanged(tmp_path):
    """draft-domain-improvements must never modify the live --domains-dir tree."""
    before = {p: p.read_bytes() for p in FROZEN.rglob("*") if p.is_file()}
    # Use a record that produces >=1 KEPT opportunity so the engine actually does
    # insertion work inside its TemporaryDirectory copy.
    rec = _record(
        "missing_crown_jewel", "api-security", "domain.yaml", "asset-1a2b3c4d",
        "- pattern: payment_methods_store\n  description: \"PCI-scope cardholder data store.\"\n",
        hint={"yaml_path": "crown_jewels"},
    )
    run_dir = _write_run(tmp_path, [rec])
    result = _invoke(run_dir)
    assert result.exit_code == 0, result.output
    assert "1 drafted" in result.output  # confirms real insertion work happened
    after = {p: p.read_bytes() for p in FROZEN.rglob("*") if p.is_file()}
    assert before == after, "draft-domain-improvements must not modify the live --domains-dir tree"
