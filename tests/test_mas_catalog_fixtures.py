"""The bundled MASVS/MASWE catalogs must ship with the exact contract shape so
the report taxonomy loaders and offline tests have a real (if small) subset to
read. Mirrors the discipline of the bundled atlas-techniques.json fixture."""
from __future__ import annotations

import json
import pathlib

_DATA = pathlib.Path(__file__).resolve().parents[1] / "tools" / "apd_gauntlet" / "data"

# All eight MASVS category prefixes from the v2.1.0 release.
_CATEGORIES = {
    "MASVS-STORAGE", "MASVS-CRYPTO", "MASVS-AUTH", "MASVS-NETWORK",
    "MASVS-PLATFORM", "MASVS-CODE", "MASVS-RESILIENCE", "MASVS-PRIVACY",
}


def test_masvs_json_has_meta_and_all_categories() -> None:
    doc = json.loads((_DATA / "masvs.json").read_text(encoding="utf-8"))
    meta = doc["_meta"]
    assert meta["version"] == "v2.1.0"
    assert meta["source"]
    assert meta["source_sha256"]
    assert meta["fetched_at"]
    controls = doc["controls"]
    assert meta["count"] == len(controls)
    # At least one control per category, with the contract field set.
    seen = set()
    for cid, body in controls.items():
        assert cid.startswith(body["category"] + "-"), cid
        assert body["title"]
        assert body["category_title"]
        seen.add(body["category"])
    assert seen == _CATEGORIES
    # Spot-check a known control.
    assert "MASVS-STORAGE-1" in controls


def test_maswe_json_has_meta_and_weakness_shape() -> None:
    doc = json.loads((_DATA / "maswe.json").read_text(encoding="utf-8"))
    meta = doc["_meta"]
    assert meta["source"]
    assert meta["commit"]
    assert meta["fetched_at"]
    weaknesses = doc["weaknesses"]
    assert meta["count"] == len(weaknesses)
    for wid, body in weaknesses.items():
        assert wid.startswith("MASWE-")
        assert body["title"]
        assert body["category"] in _CATEGORIES
        # The real OWASP/maswe front-matter uses this status vocabulary
        # (note: "placeholder" + "deprecated" appear alongside "new"; "draft"
        # is reserved by upstream but unused in the pinned snapshot).
        assert body["status"] in {"new", "draft", "deprecated", "placeholder"}
        assert isinstance(body["masvs_v2"], list)
        assert isinstance(body["cwe"], list)
    # The subset must include at least one deprecated weakness for loader tests.
    assert any(b["status"] == "deprecated" for b in weaknesses.values())
    assert "MASWE-0001" in weaknesses
