"""Compose .claude/skills/apd-domain/SKILL.md from a domain pack."""
from __future__ import annotations

import datetime
import json
import pathlib
from collections.abc import Iterable
from typing import Any

import yaml
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
DOMAIN_SCHEMA = json.loads((REPO / "schemas" / "domain.schema.json").read_text(encoding="utf-8"))


SemverTuple = tuple[int, int, int]


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
    Draft202012Validator(DOMAIN_SCHEMA).validate(meta)
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


def build_domain_skill(
    domain_names: str | Iterable[str],
    domains_dir: pathlib.Path,
    out_dir: pathlib.Path,
    framework_version: str,
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
    requested: list[tuple[str, str]] = [(n, str(m["version"])) for (n, m, _) in metas]
    if _existing_pack_signature(out_path) == (requested, framework_version):
        return out_path  # idempotent: already current for this pack set

    sections: list[str] = []
    for name, meta, pack_dir in metas:
        for include_glob in meta["includes"]:
            for f in sorted(pack_dir.glob(include_glob)):
                sections.append(f"\n\n## Domain: {name} — Source: `{f.relative_to(pack_dir)}`\n\n")
                sections.append(f.read_text(encoding="utf-8").rstrip())

    surfaces = _render_surfaces_section(_merge_surfaces([(n, m) for (n, m, _) in metas]))

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    packs_yaml = "".join(f"    - name: {n}\n      version: {m['version']}\n" for (n, m, _) in metas)
    frontmatter = (
        "---\n"
        "name: apd-domain\n"
        "description: Active domain pack content — severity rubric, consequential actions,"
        " common patterns. Generated from one or more domain packs at build time;"
        " do not edit by hand.\n"
        "metadata:\n"
        "  packs:\n"
        f"{packs_yaml}"
        f"  framework_version: {framework_version}\n"
        f"  generated: {timestamp}\n"
        "---\n"
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(frontmatter + "".join(sections) + surfaces + "\n", encoding="utf-8")
    return out_path
