"""On-demand draft-domain-improvements engine (Subsystem B, spec §6).

PURE PYTHON, deterministic — the LLM already did all judgment at capture. The
command never edits a real pack file: it operates on a tempfile copy of domains/
and emits a unified, `git apply`-able diff. Each selected improvement's
draft_snippet is inserted and gated INDIVIDUALLY (validate-domain for the 4
domain.yaml types; a markdown structural check for the 5 .md types) plus a fresh
build-domain-skill rebuild; a failing snippet is reverted and DROPPED (reported).
"""
from __future__ import annotations

import difflib
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .. import resources as _resources

# Reserved builder markers a .md snippet must NOT introduce (build_domain_skill).
_RESERVED_MARKERS = (
    "## Domain: ",
    "## Domain attack-path defaults",
)
_MAX_SNIPPET_BYTES = 8192

# Defence-in-depth pack-name guard on the ACT path. The CAPTURE path is protected by
# the schema's ^[a-z][a-z0-9-]*$ target_pack pattern, but _load_improvements only
# yaml.safe_loads the on-disk artifact and does NOT re-validate it against the schema.
# A hand-edited/corrupted artifact carrying target_pack '../x' would otherwise build
# pack_dir = copy_domains/'../x', resolving OUTSIDE the temp domains/ subtree. Re-apply
# the same pattern here so the §12 path-safety claim ("a traversal pack name never
# reaches the draft.py path builder") holds at draft time too, not only at capture.
_PACK_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")

_YAML_PATH_BY_TYPE = {
    "missing_crown_jewel": "crown_jewels",
    "missing_attacker_position": "attacker_positions",
    "missing_trust_boundary": "default_trust_boundaries",
    "missing_regulatory_anchor": "regulatory_anchors",
}
_ITEM_KEY_BY_PATH = {
    "crown_jewels": "pattern",
    "attacker_positions": "position",
    "default_trust_boundaries": "boundary",
}
# apd_goal -> on-disk common-patterns file stem. This is the INVERSE-EXCEPTION of
# the nine `apd_goal` -> `target_file` allOf branches in
# schemas/domain-improvement.schema.json (Task 1 Step 3): the schema enumerates the
# full nine-row table; here we encode only the ONE goal whose stem differs from its
# enum spelling (non_repudiation -> non-repudiation.md), and _GOAL_FILE.get(goal, goal)
# passes the other eight through unchanged. These two encodings MUST stay consistent:
# if a goal is ever renamed, update BOTH the schema allOf branch and this dict (they
# are the single underscore/hyphen contract the rest of the system honors, §4.1).
_GOAL_FILE = {
    "non_repudiation": "non-repudiation",
}


@dataclass
class DraftResult:
    drafted: list[str] = field(default_factory=list)        # dimpr- ids kept
    dropped: list[tuple[str, str, str]] = field(default_factory=list)  # (id, target_file, reason)
    retargeted: list[tuple[str, str]] = field(default_factory=list)    # (id, note)
    patch_text: str = ""
    patch_written: bool = False


class DraftError(Exception):
    """Internal error (artifact missing/malformed, temp-copy failure)."""


def _load_improvements(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "40-synthesis" / "domain-improvements.yaml"
    if not path.exists():
        raise DraftError(f"domain-improvements.yaml not found at {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise DraftError(f"domain-improvements.yaml is not valid YAML: {e}") from e
    if not isinstance(data, dict):
        raise DraftError("domain-improvements.yaml is not a mapping")
    return data


def _select(
    improvements: list[dict[str, Any]],
    ids: tuple[str, ...],
    types: tuple[str, ...],
    packs: tuple[str, ...],
) -> list[dict[str, Any]]:
    out = improvements
    if ids:
        out = [i for i in out if i.get("id") in ids]
    if types:
        out = [i for i in out if i.get("improvement_type") in types]
    if packs:
        out = [i for i in out if i.get("target_pack") in packs]
    return out


def _resolve_target_file(imp: dict[str, Any]) -> str:
    """For missing_common_pattern, derive target_file from apd_goal (§4.1 rule)."""
    if imp.get("improvement_type") == "missing_common_pattern":
        goal = imp.get("apd_goal", "")
        stem = _GOAL_FILE.get(goal, goal)
        return f"common-patterns/{stem}.md"
    return str(imp.get("target_file", ""))


def _validate_domain(pack: str, domains_dir: Path) -> tuple[bool, str]:
    """Run the same schema + include-resolution check validate_domain_cmd runs."""
    from jsonschema import Draft202012Validator

    schema = _resources.read_schema("domain.schema.json")
    pack_dir = domains_dir / pack
    meta_path = pack_dir / "domain.yaml"
    if not meta_path.exists():
        return False, f"domain pack '{pack}' not found"
    # Backstop: a textual insert may (for an exotic pack shape the up-front check does not
    # cover) leave domain.yaml unparseable. Guard the load so ANY unparseable temp YAML is
    # a clean DROP (matching the schema-error return shape) rather than an unhandled
    # ParserError that crashes the whole command and discards every valid snippet's patch.
    try:
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return False, f"validate-domain: unparseable domain.yaml after insert: {e}"
    errors = list(Draft202012Validator(schema).iter_errors(meta))
    if errors:
        return False, "; ".join(e.message for e in errors[:3])
    missing = [g for g in meta.get("includes", []) if not list(pack_dir.glob(g))]
    if missing:
        return False, f"unresolved includes: {missing}"
    return True, ""


_FALLBACK_FRAMEWORK_VERSION = "1.0.0"


def _framework_version(run_dir: Path) -> str:
    """Read framework_version from <run_dir>/.apd-run.yaml (the same source
    coverage_delta reads), falling back to a constant only when absent. Passing the
    live floor keeps the rebuild gate honest against a real pack whose framework_compat
    floor is above 1.0.0 (a hardcoded 1.0.0 would spuriously fail the build and drop
    every snippet, §6.4 / Issue: hardcoded framework version)."""
    cfg_path = run_dir / ".apd-run.yaml"
    if cfg_path.exists():
        try:
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            cfg = {}
        fv = cfg.get("framework_version")
        if isinstance(fv, str) and fv:
            return fv
    return _FALLBACK_FRAMEWORK_VERSION


def _rebuild(
    packs: list[str], domains_dir: Path, out_dir: Path, framework_version: str
) -> tuple[bool, str]:
    """Fresh-out-dir build (§6.4 step 3) so _existing_pack_signature never skips."""
    from ..build_domain_skill import build_domain_skill

    try:
        build_domain_skill(packs, domains_dir, out_dir, framework_version)
    except (FileNotFoundError, ValueError) as e:
        return False, str(e)
    return True, ""


def _markdown_structural_check(snippet: str) -> tuple[bool, str]:
    if len(snippet.encode("utf-8")) > _MAX_SNIPPET_BYTES:
        return False, "snippet exceeds size cap"
    if snippet.count("```") % 2 != 0:
        return False, "unbalanced code fences"
    for line in snippet.splitlines():
        for marker in _RESERVED_MARKERS:
            if line.startswith(marker):
                return False, f"collides with reserved builder marker {marker!r}"
    return True, ""


_KEY_LINE_RE = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")


def _block_bounds(lines: list[str], key: str) -> tuple[int, int, int, str] | None:
    """Locate `key:` at column 0 and the extent of its block list in `lines`.

    Returns (key_idx, end_idx, item_indent, inline) where:
      * key_idx is the index of the `^<key>:` line,
      * end_idx is the index one past the last line belonging to the block (so the
        new item is spliced at lines[:end_idx] + [item] + lines[end_idx:]),
      * item_indent is the leading-space count of the existing `-` items (2 when the
        list is currently empty/inline, the project default),
      * inline is the trailing scalar/flow value on the key line itself (e.g. "[]" for
        `regulatory_anchors: []`), or "" for a pure `key:` block header.
    Returns None when the key is absent. The block runs from the line after the key
    up to (but not including) the next column-0 `key:` line or EOF; trailing blank
    lines are excluded so the item lands tight against the last real entry."""
    key_idx = None
    inline = ""
    for i, ln in enumerate(lines):
        m = _KEY_LINE_RE.match(ln)
        if m and m.group(1) == key:
            key_idx = i
            inline = m.group(2).strip()
            break
    if key_idx is None:
        return None

    end_idx = len(lines)
    for j in range(key_idx + 1, len(lines)):
        ln = lines[j]
        if ln and not ln[0].isspace():
            # A column-0 non-space char starts the next top-level key (or document
            # content); the block ends here.
            end_idx = j
            break
    # Trim trailing blank lines out of the block so the insert hugs the last entry.
    while end_idx > key_idx + 1 and lines[end_idx - 1].strip() == "":
        end_idx -= 1

    item_indent = 2
    for j in range(key_idx + 1, end_idx):
        m = re.match(r"^(\s*)-\s", lines[j])
        if m:
            item_indent = len(m.group(1))
            break
    return key_idx, end_idx, item_indent, inline


def _inline_flow_blocks_append(raw: str, key: str) -> bool:
    """True when `key` EXISTS as a top-level key whose value is a populated/commented
    INLINE flow list that a block `- item` splice cannot be safely appended under.

    The two already-handled un-inline cases — a bare `key:` block header and the empty
    inline `key: []` / `key: [ ]` (rewritten to a block header by `_append_yaml_list_item`)
    — return False. Everything else with non-block inline content after `key:` (e.g.
    `key: [A, B]`, `key: []  # comment`, any `[...]` flow) returns True: block-appending
    under it produces unparseable YAML, so the caller should DROP rather than corrupt the
    file. Returns False when the key is absent (the append-fresh-block path handles that)."""
    bounds = _block_bounds(raw.split("\n"), key)
    if bounds is None:
        return False
    _key_idx, _end_idx, _indent, inline = bounds
    # "" is a pure `key:` block header (safe to append a block item); `[]`/`[ ]` is an
    # empty inline list that `_append_yaml_list_item` un-inlines. Any OTHER inline
    # scalar/flow content (`[A, B]`, `[]  # note`, `[ x ]`, …) cannot be block-appended
    # without producing garbage YAML, so the caller must DROP.
    return inline not in ("", "[]", "[ ]")


def _render_snippet_lines(snippet: str, indent: int) -> list[str]:
    """Re-indent an authored list-item snippet (whose `-` sits at column 0) to the
    file's existing item indent, preserving the author's quoting/formatting verbatim.
    Blank lines stay blank (no trailing whitespace)."""
    pad = " " * indent
    out: list[str] = []
    for raw in snippet.rstrip("\n").split("\n"):
        out.append(pad + raw if raw else "")
    return out


def _quote_scalar(value: str) -> str:
    """Double-quote a regulatory-anchor string the way the frozen packs do, escaping
    embedded backslashes/quotes. The validate gate is the backstop for exotic input."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _insert_domain_yaml(
    pack_dir: Path, imp: dict[str, Any], declared: set[str]
) -> tuple[bool, str]:
    """Append exactly one list item to the right domain.yaml key as TEXT, leaving
    every other line of the file byte-identical (a minimal, reviewable diff). Returns
    (ok, reason). On failure NOTHING is written (the caller's snapshot is intact).

    Validation (duplicate-check + shape-check) is still driven by yaml.safe_load on the
    snippet and the current file; only the WRITE is line-anchored instead of a full
    safe_dump round-trip (which reformatted ~70 lines for a 1-line insert)."""
    yaml_path = (imp.get("insertion_hint") or {}).get("yaml_path") or \
        _YAML_PATH_BY_TYPE.get(imp["improvement_type"], "")
    if not yaml_path:
        return False, "no yaml_path for domain.yaml target"
    try:
        node = yaml.safe_load(imp["draft_snippet"])
    except yaml.YAMLError as e:
        return False, f"snippet not valid YAML: {e}"

    # A list-target snippet is authored as a YAML list item (§7.2: "a YAML list item"),
    # so safe_load yields a one-element list. Unwrap it to the single item for the
    # mapping-item branches; the regulatory_anchors branch still expects a bare string.
    if isinstance(node, list) and len(node) == 1:
        node = node[0]

    meta_path = pack_dir / "domain.yaml"
    raw = meta_path.read_text(encoding="utf-8")

    # Shape/duplicate validation — UNCHANGED ok/drop decisions (now decided up front,
    # before any textual edit, so a malformed snippet never reaches the write).
    item_lines_factory: Any
    if yaml_path == "regulatory_anchors":
        if not isinstance(node, str):
            return False, "snippet shape: expected one string"
        if node.strip().lower() in declared:
            return False, f"already declared in {pack_dir.name}"
        scalar = node

        def item_lines_factory(indent: int) -> list[str]:
            return [" " * indent + "- " + _quote_scalar(scalar)]
    else:
        if not isinstance(node, dict):
            return False, "snippet shape: expected one mapping"
        key = _ITEM_KEY_BY_PATH[yaml_path]
        if key not in node:
            return False, f"snippet shape: expected one mapping with '{key}'"
        if str(node[key]).strip().lower() in declared:
            return False, f"already declared in {pack_dir.name}"
        snippet = imp["draft_snippet"]

        def item_lines_factory(indent: int) -> list[str]:
            return _render_snippet_lines(snippet, indent)

    # Up-front anchorability: a populated/commented INLINE flow list at the target key
    # cannot be block-appended without producing unparseable YAML. Drop cleanly (with a
    # hand-edit hint) BEFORE writing rather than splicing garbage the validate gate would
    # otherwise have to catch as an opaque parse error.
    if _inline_flow_blocks_append(raw, yaml_path):
        return False, (
            f"cannot insert into inline/flow-style list at {yaml_path}; "
            "edit the pack by hand"
        )

    new_text = _append_yaml_list_item(raw, yaml_path, item_lines_factory)
    meta_path.write_text(new_text, encoding="utf-8")
    return True, ""


def _append_yaml_list_item(raw: str, key: str, item_lines_factory: Any) -> str:
    """Textually splice one list item under `key` in `raw`, byte-preserving the rest.

    `item_lines_factory(indent)` renders the item's lines at the resolved indent. When
    `key` exists with a block list the item lands after the last block line at the
    existing item indent; an inline-EMPTY list (`key: []`) is converted to a block by
    rewriting the key line to `key:` and spliced as a 2-space block (1 removed + ≥1
    added — the minimal cost of un-inlining); when `key` is absent entirely a fresh
    `key:` block is appended at EOF (2-space indent). A single trailing newline is
    preserved either way."""
    had_trailing_nl = raw.endswith("\n")
    lines = raw.split("\n")
    # raw ending in "\n" yields a trailing "" element from split(); strip it so indices
    # address only real content lines, then re-join with a single trailing newline.
    if lines and lines[-1] == "":
        lines = lines[:-1]

    bounds = _block_bounds(lines, key)
    if bounds is None:
        # Key absent: append a fresh block at EOF.
        item = item_lines_factory(2)
        new_lines = lines + [f"{key}:"] + item
    else:
        key_idx, end_idx, item_indent, inline = bounds
        if inline in ("[]", "[ ]") and end_idx == key_idx + 1:
            # `key: []` — un-inline to a block header so the new item is valid YAML.
            item = item_lines_factory(2)
            new_lines = (
                lines[:key_idx] + [f"{key}:"] + item + lines[key_idx + 1:]
            )
        else:
            item = item_lines_factory(item_indent)
            new_lines = lines[:end_idx] + item + lines[end_idx:]

    text = "\n".join(new_lines)
    return text + "\n" if (had_trailing_nl or not raw) else text


def _declared_keys(pack_dir: Path, yaml_path: str) -> set[str]:
    meta = yaml.safe_load((pack_dir / "domain.yaml").read_text(encoding="utf-8")) or {}
    if yaml_path == "regulatory_anchors":
        return {str(x).strip().lower() for x in (meta.get("regulatory_anchors") or [])}
    key = _ITEM_KEY_BY_PATH.get(yaml_path)
    out: set[str] = set()
    for item in (meta.get(yaml_path) or []):
        if isinstance(item, dict) and item.get(key):
            out.add(str(item[key]).strip().lower())
    return out


def _ensure_trailing_newline(text: str) -> str:
    return text.rstrip("\n") + "\n"


def _insert_markdown(
    target: Path, imp: dict[str, Any], dimpr_id: str
) -> tuple[bool, str, str | None]:
    """Insert the snippet into a .md file (creating it if absent). Returns
    (ok, reason, retarget_note). Level-aware anchor with EOF fallback (§6.3)."""
    snippet = _ensure_trailing_newline(imp["draft_snippet"])
    new_file = not target.exists()
    if new_file:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(snippet, encoding="utf-8")
        return True, "", None

    body = target.read_text(encoding="utf-8")
    lines = body.splitlines()
    hint = (imp.get("insertion_hint") or {}).get("markdown_section")
    retarget: str | None = None
    insert_at: int | None = None
    if hint:
        level, text = hint["level"], hint["text"]
        prefix = "#" * level + " "
        matches = [k for k, ln in enumerate(lines) if ln.strip() == (prefix + text).strip()]
        if len(matches) == 1:
            start = matches[0]
            insert_at = len(lines)
            for k in range(start + 1, len(lines)):
                stripped = lines[k].lstrip("#")
                hlevel = len(lines[k]) - len(stripped)
                if lines[k].startswith("#") and hlevel <= level:
                    insert_at = k
                    break
        else:
            retarget = (
                f"{len(matches)} heading matches at level {level} for {text!r}; "
                "appended at EOF"
            )
    if insert_at is None:
        # EOF fallback under a generated heading.
        block = _ensure_trailing_newline(body) + "\n" + \
            f"## Captured improvement ({dimpr_id})\n\n" + snippet
        target.write_text(_ensure_trailing_newline(block), encoding="utf-8")
        return True, "", retarget

    new_lines = lines[:insert_at] + ["", snippet.rstrip("\n")] + lines[insert_at:]
    target.write_text(_ensure_trailing_newline("\n".join(new_lines)), encoding="utf-8")
    return True, "", retarget


def _ensure_include_glob(pack_dir: Path, target_file: str) -> bool:
    """Couple a new common-patterns/<goal>.md into domain.yaml includes (§6.3).
    Returns True if domain.yaml was edited (the include was appended), False if the
    file was already covered by an existing glob/explicit include (the `covered`
    short-circuit — spec §6.3 "If the pack's includes already globs
    common-patterns/*.md, only the new file is created, no domain.yaml edit needed").
    The caller uses the return to decide whether a domain.yaml modify hunk is emitted."""
    meta_path = pack_dir / "domain.yaml"
    raw = meta_path.read_text(encoding="utf-8")
    meta = yaml.safe_load(raw)
    includes = meta.get("includes", [])
    covered = any(
        g == target_file
        or (g == "common-patterns/*.md" and target_file.startswith("common-patterns/"))
        for g in includes
    )
    if covered:
        return False
    # Line-anchored append (same minimal-diff approach as _insert_domain_yaml): splice
    # `  - <target_file>` after the last existing includes entry, byte-preserving the
    # rest of the file rather than safe_dump round-tripping it.
    new_text = _append_yaml_list_item(
        raw, "includes", lambda indent: [" " * indent + "- " + target_file])
    meta_path.write_text(new_text, encoding="utf-8")
    return True


def _unified_diff(orig_root: Path, copy_root: Path, rel: str) -> str:
    """Per-file unified diff. Emits a git new-file hunk when the original is absent.

    `rel` is always `domains/<pack>/<file>`. The copy tree (`copy_root`) literally
    contains a `domains/` dir, so `copy_root / rel` resolves directly. The ORIGINAL
    pack tree, however, is `orig_root` itself (the live --domains-dir, whose own name
    need NOT be `domains`), so the original file is `orig_root / <pack>/<file>` — i.e.
    `rel` with its leading `domains/` segment stripped. Looking the original up via
    `orig_root / rel` would only work when --domains-dir happens to be named `domains`
    and would otherwise mis-fire the new-file branch for an existing file."""
    rel_in_domains = rel[len("domains/"):] if rel.startswith("domains/") else rel
    a_path = orig_root / rel_in_domains
    b_path = copy_root / rel
    b_text = b_path.read_text(encoding="utf-8")
    if not a_path.exists():
        body = "".join(
            difflib.unified_diff(
                [], b_text.splitlines(keepends=True),
                fromfile="/dev/null", tofile="b/" + rel,
            )
        )
        return (
            f"diff --git a/{rel} b/{rel}\n"
            "new file mode 100644\n"
            "--- /dev/null\n"
            f"+++ b/{rel}\n"
            + "".join(body.splitlines(keepends=True)[2:])  # drop difflib's --- /+++ header
        )
    a_text = a_path.read_text(encoding="utf-8")
    return "".join(
        difflib.unified_diff(
            a_text.splitlines(keepends=True),
            b_text.splitlines(keepends=True),
            fromfile="a/" + rel, tofile="b/" + rel,
        )
    )


def draft_domain_improvements(
    run_dir: Path,
    domains_dir: Path,
    out: Path,
    *,
    ids: tuple[str, ...] = (),
    types: tuple[str, ...] = (),
    packs: tuple[str, ...] = (),
) -> DraftResult:
    data = _load_improvements(run_dir)
    framework_version = _framework_version(run_dir)
    selected = _select(list(data.get("improvements") or []), ids, types, packs)
    result = DraftResult()
    if not selected:
        return result  # no-op; caller prints the message and exits 0

    # Stable processing order (§6.6): (target_pack, resolved target_file, dimpr-id).
    selected.sort(key=lambda i: (
        i.get("target_pack", ""), _resolve_target_file(i), i.get("id", "")))

    all_packs = sorted({i["target_pack"] for i in selected
                        if _PACK_NAME_RE.match(i.get("target_pack", ""))
                        and (domains_dir / i["target_pack"] / "domain.yaml").exists()})

    with tempfile.TemporaryDirectory() as tmp:
        tmproot = Path(tmp)
        copy_domains = tmproot / "domains"
        shutil.copytree(domains_dir, copy_domains)

        changed: set[str] = set()  # rel paths that were kept
        for imp in selected:
            dimpr_id = imp.get("id", "")
            pack = imp.get("target_pack", "")
            target_file = _resolve_target_file(imp)

            # Guard 0: pack-name shape (defence-in-depth on the ACT path). A traversal
            # or upper-case name from a corrupted artifact is dropped BEFORE any path
            # is constructed, so it never reaches the path builder (§12 path-safety).
            if not _PACK_NAME_RE.match(pack):
                result.dropped.append((dimpr_id, target_file, "invalid target_pack name"))
                continue

            rel = f"domains/{pack}/{target_file}"
            pack_dir = copy_domains / pack

            # Guard 1: unknown target_pack (check the COPY, before any path open).
            if not (pack_dir / "domain.yaml").exists():
                result.dropped.append((dimpr_id, target_file, "unknown target_pack"))
                continue

            # Snapshot the files this insert may touch (for revert).
            target_path = copy_domains / pack / target_file
            snap_meta = (pack_dir / "domain.yaml").read_text(encoding="utf-8")
            snap_target = target_path.read_text(encoding="utf-8") if target_path.exists() else None
            target_existed = target_path.exists()

            is_yaml = target_file == "domain.yaml"
            ok, reason = True, ""
            retarget: str | None = None
            coupled_yaml = False

            if is_yaml:
                yaml_path = (imp.get("insertion_hint") or {}).get("yaml_path") or \
                    _YAML_PATH_BY_TYPE.get(imp["improvement_type"], "")
                declared = _declared_keys(pack_dir, yaml_path) if yaml_path else set()
                ok, reason = _insert_domain_yaml(pack_dir, imp, declared)
            else:
                sc_ok, sc_reason = _markdown_structural_check(imp["draft_snippet"])
                if not sc_ok:
                    ok, reason = False, f"markdown structural check: {sc_reason}"
                else:
                    ins_ok, ins_reason, retarget = _insert_markdown(target_path, imp, dimpr_id)
                    ok, reason = ins_ok, ins_reason
                    if ok and not target_existed:
                        # coupled_yaml is True ONLY if the include was actually appended;
                        # a glob-covered pack ("common-patterns/*.md") needs no edit, so
                        # no domain.yaml hunk and no validate-domain re-gate for it.
                        coupled_yaml = _ensure_include_glob(pack_dir, target_file)

            # Gate: validate-domain (meaningful for domain.yaml + the coupled edit) + rebuild.
            if ok and (is_yaml or coupled_yaml):
                v_ok, v_reason = _validate_domain(pack, copy_domains)
                if not v_ok:
                    ok, reason = False, v_reason
            if ok:
                build_out = tmproot / f"skill-{dimpr_id}"
                b_ok, b_reason = _rebuild(all_packs, copy_domains, build_out, framework_version)
                if not b_ok:
                    ok, reason = False, f"build-domain-skill: {b_reason}"

            if not ok:
                # Revert this single snippet (restore the in-memory snapshot).
                (pack_dir / "domain.yaml").write_text(snap_meta, encoding="utf-8")
                if snap_target is None:
                    if target_path.exists():
                        target_path.unlink()
                else:
                    target_path.write_text(snap_target, encoding="utf-8")
                result.dropped.append((dimpr_id, target_file, reason))
                continue

            result.drafted.append(dimpr_id)
            changed.add(rel)
            if coupled_yaml:
                changed.add(f"domains/{pack}/domain.yaml")
            if retarget:
                result.retargeted.append((dimpr_id, retarget))

        # Build the patch from kept changes, deterministic file order. The orig root is
        # the live --domains-dir (whose name need not be `domains`); _unified_diff strips
        # the leading `domains/` from `rel` to resolve the original file under it.
        parts = [_unified_diff(domains_dir, tmproot, rel) for rel in sorted(changed)]
        result.patch_text = "".join(parts)

    if result.drafted:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.patch_text, encoding="utf-8")
        result.patch_written = True
    return result
