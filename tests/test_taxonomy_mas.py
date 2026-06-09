"""maswe_masvs_parents() — {MASWE-NNNN: [MASVS-...]} projection of maswe.json."""
from __future__ import annotations

from apd_gauntlet.report import taxonomy


def test_maswe_masvs_parents_accessor_shape() -> None:
    parents = taxonomy.maswe_masvs_parents()
    assert isinstance(parents, dict)
    # Every value is a list of MASVS-* control ids.
    for weakness_id, masvs_ids in parents.items():
        assert weakness_id.startswith("MASWE-")
        assert isinstance(masvs_ids, list)
        for mid in masvs_ids:
            assert mid.startswith("MASVS-")
    # MASWE-0001 maps to its masvs_v2 parents per the bundled catalog.
    assert parents.get("MASWE-0001"), "MASWE-0001 must carry masvs_v2 parents"


def test_maswe_masvs_parents_is_empty_dict_when_catalog_absent(monkeypatch, tmp_path) -> None:
    # Point the loader at a dir with no maswe.json; loader degrades to {}.
    monkeypatch.setattr(taxonomy, "_PKG_DATA", tmp_path)
    taxonomy.maswe_masvs_parents.cache_clear()
    assert taxonomy.maswe_masvs_parents() == {}
    taxonomy.maswe_masvs_parents.cache_clear()
