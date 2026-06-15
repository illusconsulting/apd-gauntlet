"""CI gate: assert every fetched data/*.json carries provenance metadata.

The six refresh_*.py fetchers write their cache to tools/apd_gauntlet/data/ with
a provenance block — source (or source_url), source_sha256 (or commit), and
fetched_at — either nested under _meta or at the top level. This gate asserts
that block is present and complete so a citation that resolves to a pinned
source_sha256 is trustworthy.

Files with legacy/hand-maintained writers outside the six refresh_*.py modules
are explicitly EXEMPT (see EXEMPT_REASON). Closing those gaps is follow-on work.
"""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

DATA = pathlib.Path(__file__).resolve().parent / "apd_gauntlet" / "data"

# Files confirmed to carry full provenance (source|source_url + source_sha256|commit
# + fetched_at) in the committed cache.
COVERED = [
    "atlas-techniques.json",    # _meta: source, source_sha256, fetched_at
    "capec.json",                # top-level: source_url, source_sha256, fetched_at
    "mitre-attack-detection.json", # top-level: source_url, source_sha256, fetched_at
    "hipaa-800-53-crosswalk.json", # _meta: source, source_sha256, fetched_at (CPRT-grounded)
    "csf2-800-53-crosswalk.json",  # _meta: source, source_sha256, fetched_at (CPRT-grounded)
    "cwe.json",                  # top-level: source_url, source_sha256, fetched_at
    "d3fend.json",               # top-level: source_url, source_sha256, fetched_at
    "masvs.json",                # _meta: source, source_sha256, commit, fetched_at
    "maswe.json",                # _meta: source, commit, fetched_at
    "owasp_api_top10.json",      # top-level: source_url, source_sha256, fetched_at
    "owasp_llm_top10.json",      # top-level: source_url, source_sha256, fetched_at
    "owasp_top10.json",          # top-level: source_url, source_sha256, fetched_at
]

# Files that lack full provenance; backfilling is follow-on work.
EXEMPT_REASON: dict[str, str] = {
    "mitre-attack-techniques.json": (
        "refresh_mitre_attack.py stores source+fetched_at in _meta but omits "
        "source_sha256/commit (STIX bundle is live-fetched, no pinned hash yet)"
    ),
    "mitre-mitigations.json": (
        "refresh_mitre_attack.py writes only mobile_* provenance keys at top level; "
        "no top-level source, source_url, or fetched_at for the enterprise mitigations"
    ),
    "nist-controls.json": (
        "refresh_nist_controls.py stores source+fetched_at in _meta but omits "
        "source_sha256/commit (OSCAL catalog is live-fetched, no pinned hash yet)"
    ),
    "nist-families.json": (
        "Hand-maintained static family-abbreviation lookup; no fetcher writes it "
        "so provenance fields are absent by design"
    ),
}
EXEMPT = list(EXEMPT_REASON)


def metadata_block(data: dict[str, Any]) -> dict[str, Any]:
    """Return the provenance block: _meta if a dict, else the top-level object."""
    meta = data.get("_meta")
    if isinstance(meta, dict):
        return meta
    return data


def check_one(name: str, data: dict[str, Any]) -> tuple[bool, str]:
    """Return (ok, reason). ok iff source, hash, and fetched_at are all present."""
    meta = metadata_block(data)
    has_source = ("source" in meta) or ("source_url" in meta)
    has_hash = ("source_sha256" in meta) or ("commit" in meta)
    has_fetched = "fetched_at" in meta
    if has_source and has_hash and has_fetched:
        return True, ""
    missing = []
    if not has_source:
        missing.append("source|source_url")
    if not has_hash:
        missing.append("source_sha256|commit")
    if not has_fetched:
        missing.append("fetched_at")
    return False, f"{name}: missing {', '.join(missing)}"


def main() -> int:
    failures: list[str] = []

    # Detect any data/*.json that is neither COVERED nor EXEMPT.
    classified = set(COVERED) | set(EXEMPT_REASON)
    for path in sorted(DATA.glob("*.json")):
        if path.name not in classified:
            failures.append(
                f"{path.name}: unclassified — add to COVERED or EXEMPT_REASON in "
                "tools/check_kb_cache_freshness.py"
            )

    for name in COVERED:
        path = DATA / name
        if not path.exists():
            failures.append(f"{name}: covered cache file is missing")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        ok, why = check_one(name, data)
        if not ok:
            failures.append(why)

    if failures:
        print(
            "check_kb_cache_freshness: cache provenance incomplete.\n"
            "Each fetched data/*.json must carry _meta{source, "
            "source_sha256|commit, fetched_at} (or the same keys at top level).\n"
            "Re-run the relevant refresh-* command, or add the file to the "
            "documented EXEMPT set in tools/check_kb_cache_freshness.py.",
            file=sys.stderr,
        )
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print(
        f"check_kb_cache_freshness: OK ({len(COVERED)} covered, {len(EXEMPT)} exempt)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
