"""Compose .claude/skills/apd-domain/SKILL.md from a domain pack."""
from __future__ import annotations

import datetime
import pathlib
import re
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from . import resources as _resources


@lru_cache(maxsize=1)
def _domain_schema() -> dict[str, Any]:
    return _resources.read_schema("domain.schema.json")


SemverTuple = tuple[int, int, int]

# The nine APD goals, keyed by their common-patterns file stem (hyphenated form,
# which also names the per-goal sidecar). ``non-repudiation`` is the only stem
# that differs from the canonical underscored ``apd_goal`` name.
GOAL_FILE_STEMS: tuple[str, ...] = (
    "confidentiality", "integrity", "availability",
    "distributed", "resilient", "ephemeral",
    "authenticity", "non-repudiation", "immutability",
)


def _goal_name(stem: str) -> str:
    """Canonical underscored apd_goal name for a common-patterns file stem."""
    return stem.replace("-", "_")


def _iter_pack_files(
    metas: list[tuple[str, dict[str, Any], pathlib.Path]],
) -> Iterable[tuple[str, str, str | None, str, str]]:
    """Yield ``(pack_name, rel_path, goal_stem | None, section_header, body)`` for
    every included file, in the exact declared pack/include/glob order.

    ``goal_stem`` is set when the file lives under ``common-patterns/`` (its stem
    is one of :data:`GOAL_FILE_STEMS`); ``None`` for the calibration files. The
    header/body match the full-skill rendering byte-for-byte so the full build is
    unchanged and the per-goal sidecars reuse the same chunks.
    """
    for name, meta, pack_dir in metas:
        for include_glob in meta["includes"]:
            for f in sorted(pack_dir.glob(include_glob)):
                rel = f.relative_to(pack_dir)
                goal_stem = rel.stem if rel.parent.name == "common-patterns" else None
                header = f"\n\n## Domain: {name} — Source: `{rel}`\n\n"
                body = f.read_text(encoding="utf-8").rstrip()
                yield name, str(rel), goal_stem, header, body


def _parse_semver_range(spec: str) -> tuple[SemverTuple | None, SemverTuple | None]:
    """Minimal '>=1.0.0,<2.0.0'-style range parser."""
    lo: SemverTuple | None = None
    hi: SemverTuple | None = None
    for tok in spec.split(","):
        tok = tok.strip()
        if tok.startswith(">="):
            parts = tok[2:].split(".")
            lo = (int(parts[0]), int(parts[1]), int(parts[2]))
        elif tok.startswith("<"):
            parts = tok[1:].split(".")
            hi = (int(parts[0]), int(parts[1]), int(parts[2]))
    return lo, hi


def _version_in_range(version: str, spec: str) -> bool:
    parts = version.split(".")
    v = (int(parts[0]), int(parts[1]), int(parts[2]))
    lo, hi = _parse_semver_range(spec)
    if lo is not None and v < lo:
        return False
    return not (hi is not None and v >= hi)


def _load_pack_meta(pack_dir: pathlib.Path, domain_name: str) -> dict[str, Any]:
    meta_path = pack_dir / "domain.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"Domain pack '{domain_name}' not found at {pack_dir}")
    meta: dict[str, Any] = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    Draft202012Validator(_domain_schema()).validate(meta)
    return meta


def _merge_surfaces(metas: list[tuple[str, dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    """Union crown_jewels/attacker_positions/default_trust_boundaries across packs,
    dedup by key in declared order, accumulate contributing-pack provenance."""
    specs = [
        ("crown_jewels", "pattern"),
        ("attacker_positions", "position"),
        ("default_trust_boundaries", "boundary"),
    ]
    merged: dict[str, list[dict[str, Any]]] = {}
    for field, key in specs:
        seen: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for name, meta in metas:
            for item in meta.get(field, []) or []:
                kv = item[key]
                if kv not in seen:
                    seen[kv] = {key: kv, "description": item["description"], "domains": [name]}
                    order.append(kv)
                else:
                    entry = seen[kv]
                    if name not in entry["domains"]:
                        entry["domains"].append(name)
                    if item["description"] != entry["description"]:
                        entry["note"] = "description varies across packs; first-declared kept"
        merged[field] = [seen[k] for k in order]
    return merged


def _render_surfaces_section(merged: dict[str, list[dict[str, Any]]]) -> str:
    if not any(merged.values()):
        return ""
    label = {
        "crown_jewels": "Crown jewels",
        "attacker_positions": "Attacker positions",
        "default_trust_boundaries": "Default trust boundaries",
    }
    parts = [
        "\n\n## Domain attack-path defaults (merged across packs)\n\n",
        "Unioned and deduplicated from the selected packs' `domain.yaml`. Run-config "
        "`crown_jewels` / `attacker_positions` still override these. Each entry's "
        "`domains` lists the contributing pack(s).\n",
    ]
    for field in ("crown_jewels", "attacker_positions", "default_trust_boundaries"):
        items = merged[field]
        if not items:
            continue
        block = yaml.safe_dump({field: items}, sort_keys=False).rstrip()
        parts.append(f"\n### {label[field]}\n\n```yaml\n{block}\n```\n")
    return "".join(parts)


def _existing_pack_signature(
    out_path: pathlib.Path,
) -> tuple[list[tuple[str, str]], str | None] | None:
    """Return ([(name, version), ...], framework_version) from an existing skill's
    frontmatter, or None when absent/unparseable."""
    if not out_path.exists():
        return None
    text = out_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    try:
        fm: dict[str, Any] = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError:
        return None
    meta = fm.get("metadata", {}) or {}
    packs: list[tuple[str, str]] = [
        (str(p["name"]), str(p["version"])) for p in meta.get("packs", []) or []
    ]
    return (packs, meta.get("framework_version"))


def _finalize(text: str) -> str:
    """Collapse builder join artifacts and end with exactly one newline.

    Section headers begin with ``\\n\\n`` and bodies are rstripped, so mid-document
    joins yield a single blank line. The only places that can produce 3+ newlines
    are the frontmatter→first-section seam and the trailing surfaces seam — collapse
    them to a single blank line (markdownlint MD012) and trim to one EOF newline
    (MD047). Pack bodies are already MD012-clean (linted via ``domains/**/*.md``),
    so collapsing never disturbs intended in-body spacing.
    """
    return re.sub(r"\n{3,}", "\n\n", text).rstrip() + "\n"


def _packs_yaml(metas: list[tuple[str, dict[str, Any], pathlib.Path]]) -> str:
    return "".join(f"    - name: {n}\n      version: {m['version']}\n" for (n, m, _) in metas)


def _merge_taxonomies(metas: list[tuple[str, dict[str, Any], pathlib.Path]]) -> list[str]:
    """Union the packs' declared ``taxonomies`` in declared-pack/declared-entry order,
    deduped. Empty when no pack declares any."""
    seen: dict[str, None] = {}
    for _, meta, _ in metas:
        for tax in meta.get("taxonomies", []) or []:
            seen.setdefault(tax, None)
    return list(seen)


def _sidecar_frontmatter(
    goal_stem: str,
    metas: list[tuple[str, dict[str, Any], pathlib.Path]],
    framework_version: str,
    timestamp: str,
    *,
    retained_calibration: list[str],
    omitted_goal_patterns: list[str],
) -> str:
    """Frontmatter for a per-goal sidecar, carrying the explicit `pruned` manifest
    (no silent caps: every omitted goal-pattern file is listed)."""
    goal = _goal_name(goal_stem)
    omitted_yaml = (
        "".join(f"      - {g}\n" for g in omitted_goal_patterns) or "      []\n"
    )
    retained_yaml = "".join(f"      - {c}\n" for c in retained_calibration)
    return (
        "---\n"
        f"name: apd-domain-{goal_stem}\n"
        f"description: Goal-scoped domain calibration for the apd-{goal_stem} lens —"
        " full severity rubric, consequential actions, immutability classes, data"
        f" taxonomy, and ONLY the {goal_stem} common-patterns. Generated at build"
        " time; do not edit by hand. The full cross-goal skill is at ../SKILL.md.\n"
        "metadata:\n"
        "  packs:\n"
        f"{_packs_yaml(metas)}"
        f"  framework_version: {framework_version}\n"
        f"  generated: {timestamp}\n"
        "  pruned:\n"
        f"    scoped_to_goal: {goal}\n"
        "    retained_calibration:\n"
        f"{retained_yaml}"
        "    omitted_goal_patterns:\n"
        f"{omitted_yaml}"
        "    full_skill: ../SKILL.md\n"
        "    note: \"Per-lens view; other goals' common-patterns are intentionally"
        " omitted to bound context. Calibration files and attack-path defaults are"
        " retained in full. intake / attack-path / domain-auditor read ../SKILL.md.\"\n"
        "---\n"
    )


def build_domain_skill(
    domain_names: str | Iterable[str],
    domains_dir: pathlib.Path,
    out_dir: pathlib.Path,
    framework_version: str,
    *,
    emit_sidecars: bool = True,
) -> pathlib.Path:
    if isinstance(domain_names, str):
        domain_names = [domain_names]
    domain_names = list(domain_names)
    if not domain_names:
        raise ValueError("build_domain_skill requires at least one domain name")
    domain_names = list(dict.fromkeys(domain_names))

    metas: list[tuple[str, dict[str, Any], pathlib.Path]] = []
    for name in domain_names:
        pack_dir = domains_dir / name
        meta = _load_pack_meta(pack_dir, name)
        if not _version_in_range(framework_version, meta["framework_compat"]):
            raise ValueError(
                f"Framework {framework_version} incompatible with pack '{name}' "
                f"framework_compat: {meta['framework_compat']}"
            )
        metas.append((name, meta, pack_dir))

    out_path = out_dir / "SKILL.md"
    by_goal_dir = out_dir / "by-goal"
    requested: list[tuple[str, str]] = [(n, str(m["version"])) for (n, m, _) in metas]
    # Collect the rendered file chunks once; reused by the full skill and every
    # sidecar so a sidecar is a strict subset of the full skill's sections.
    files = list(_iter_pack_files(metas))
    present_goal_stems = [s for s in GOAL_FILE_STEMS if any(g == s for _, _, g, _, _ in files)]
    calibration_stems = sorted(
        {pathlib.PurePosixPath(rel).stem for _, rel, g, _, _ in files if g is None}
    )

    # Idempotency: skip the rebuild only when the full skill is current AND every
    # expected sidecar already exists (else a stale/partial by-goal/ would persist).
    sidecars_ok = (not emit_sidecars) or all(
        (by_goal_dir / f"{s}.md").exists() for s in present_goal_stems
    )
    if _existing_pack_signature(out_path) == (requested, framework_version) and sidecars_ok:
        return out_path

    surfaces = _render_surfaces_section(_merge_surfaces([(n, m) for (n, m, _) in metas]))
    taxonomies = _merge_taxonomies(metas)
    taxonomies_yaml = (
        "  taxonomies:\n" + "".join(f"    - {t}\n" for t in taxonomies)
        if taxonomies
        else ""
    )
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    frontmatter = (
        "---\n"
        "name: apd-domain\n"
        "description: Active domain pack content — severity rubric, consequential actions,"
        " common patterns. Generated from one or more domain packs at build time;"
        " do not edit by hand.\n"
        "metadata:\n"
        "  packs:\n"
        f"{_packs_yaml(metas)}"
        f"{taxonomies_yaml}"
        f"  framework_version: {framework_version}\n"
        f"  generated: {timestamp}\n"
        "---\n"
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    full_sections = [chunk for _, _, _, header, body in files for chunk in (header, body)]
    out_path.write_text(
        _finalize(frontmatter + "".join(full_sections) + surfaces), encoding="utf-8"
    )

    if emit_sidecars:
        by_goal_dir.mkdir(parents=True, exist_ok=True)
        for stem in present_goal_stems:
            scoped = [
                chunk
                for _, _, g, header, body in files
                if g is None or g == stem
                for chunk in (header, body)
            ]
            omitted = [s for s in present_goal_stems if s != stem]
            sc_front = _sidecar_frontmatter(
                stem, metas, framework_version, timestamp,
                retained_calibration=calibration_stems,
                omitted_goal_patterns=omitted,
            )
            (by_goal_dir / f"{stem}.md").write_text(
                _finalize(sc_front + "".join(scoped) + surfaces), encoding="utf-8"
            )

    return out_path
