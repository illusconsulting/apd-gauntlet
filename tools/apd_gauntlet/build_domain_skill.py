"""Compose .claude/skills/apd-domain/SKILL.md from a domain pack."""
from __future__ import annotations
import datetime
import json
import pathlib
import yaml
from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
DOMAIN_SCHEMA = json.loads((REPO / "schemas" / "domain.schema.json").read_text())


def _parse_semver_range(spec: str) -> tuple[tuple[int, int, int] | None, tuple[int, int, int] | None]:
    """Minimal '>=1.0.0,<2.0.0'-style range parser."""
    lo: tuple[int, int, int] | None = None
    hi: tuple[int, int, int] | None = None
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
    if hi is not None and v >= hi:
        return False
    return True


def build_domain_skill(
    domain_name: str,
    domains_dir: pathlib.Path,
    out_dir: pathlib.Path,
    framework_version: str,
) -> pathlib.Path:
    pack_dir = domains_dir / domain_name
    meta_path = pack_dir / "domain.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"Domain pack '{domain_name}' not found at {pack_dir}")
    meta = yaml.safe_load(meta_path.read_text())
    Draft202012Validator(DOMAIN_SCHEMA).validate(meta)

    if not _version_in_range(framework_version, meta["framework_compat"]):
        raise ValueError(
            f"Framework {framework_version} incompatible with pack '{domain_name}' "
            f"framework_compat: {meta['framework_compat']}"
        )

    sections: list[str] = []
    for include_glob in meta["includes"]:
        for f in sorted(pack_dir.glob(include_glob)):
            sections.append(f"\n\n## Source: `{f.relative_to(pack_dir)}`\n\n")
            sections.append(f.read_text())

    timestamp = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    frontmatter = (
        "---\n"
        "name: apd-domain\n"
        "description: Active domain pack content — severity rubric, consequential actions, common patterns. "
        "Generated from a domain pack at build time; do not edit by hand.\n"
        "metadata:\n"
        f"  pack: {meta['name']}\n"
        f"  pack_version: {meta['version']}\n"
        f"  framework_version: {framework_version}\n"
        f"  generated: {timestamp}\n"
        "---\n"
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "SKILL.md"
    out_path.write_text(frontmatter + "".join(sections))
    return out_path
