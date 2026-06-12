import hashlib

import yaml
from apd_gauntlet.linters import (
    compute_asset_id,
    compute_boundary_id,
    compute_identity_id,
)


def _sha8(s):
    return hashlib.sha256(s.encode()).hexdigest()[:8]


def test_asset_id_deterministic():
    assert compute_asset_id("Postgres PHI store", "tech_plan.md#L10") == "asset-" + _sha8(
        "Postgres PHI store|tech_plan.md#L10"
    )


def test_identity_id_deterministic():
    assert compute_identity_id("worker-sa", "iac/sa.yaml#L3") == "idn-" + _sha8(
        "worker-sa|iac/sa.yaml#L3"
    )


def test_boundary_id_deterministic():
    assert compute_boundary_id("dmz->app", "diagram.md#L5") == "tb-" + _sha8(
        "dmz->app|diagram.md#L5"
    )


def test_inventory_id_handles_empty_locator():
    # domain_default provenance may have no locator -> id is name|"" (still deterministic)
    assert compute_asset_id("abstract-jewel", "") == "asset-" + _sha8("abstract-jewel|")


def _inv():
    return {
        "schema_version": 1, "generated_by": "intake",
        "assets": [
            {"name": "API gateway", "asset_type": "service",
             "provenance": {"source": "artifact", "artifact": "tech_plan.md", "locator": "L1"},
             "confidence": "high"},
            {"name": "PHI DB", "asset_type": "data_store",
             "provenance": {"source": "artifact", "artifact": "tech_plan.md", "locator": "L2"},
             "confidence": "high"},
        ],
        "identities": [
            {"name": "worker-sa", "identity_type": "service_account",
             "provenance": {"source": "artifact", "artifact": "tech_plan.md", "locator": "L3"},
             "confidence": "medium"},
        ],
        "trust_boundaries": [
            {"name": "edge", "crosses": ["API gateway", "PHI DB"],
             "provenance": {"source": "artifact", "artifact": "tech_plan.md", "locator": "L4"}},
        ],
    }


def _write_inv(run_dir, inv):
    import yaml as _y
    d = run_dir / "00-context"
    d.mkdir(parents=True, exist_ok=True)
    (d / "asset-inventory.yaml").write_text(_y.safe_dump(inv, sort_keys=False), encoding="utf-8")


def test_assemble_inventory_mints_ids_and_wires_crosses_by_name(tmp_path):
    from apd_gauntlet.assemble_inventory import assemble_inventory
    _write_inv(tmp_path, _inv())
    assemble_inventory(tmp_path)
    out = yaml.safe_load((tmp_path / "00-context" / "asset-inventory.yaml").read_text())
    ids = {a["name"]: a["asset_id"] for a in out["assets"]}
    assert ids["API gateway"] == compute_asset_id("API gateway", "L1")
    assert ids["PHI DB"] == compute_asset_id("PHI DB", "L2")
    assert out["identities"][0]["identity_id"] == compute_identity_id("worker-sa", "L3")
    assert out["trust_boundaries"][0]["boundary_id"] == compute_boundary_id("edge", "L4")
    # crosses rewritten from names to the minted asset ids, in order
    assert out["trust_boundaries"][0]["crosses"] == [ids["API gateway"], ids["PHI DB"]]


def test_assemble_inventory_is_idempotent(tmp_path):
    from apd_gauntlet.assemble_inventory import assemble_inventory
    _write_inv(tmp_path, _inv())
    p = tmp_path / "00-context" / "asset-inventory.yaml"
    assemble_inventory(tmp_path)
    first = p.read_bytes()
    assemble_inventory(tmp_path)
    second = p.read_bytes()
    assert first == second  # second run is a no-op (ids stable; crosses already ids pass through)


def test_assemble_inventory_absent_file_is_noop(tmp_path):
    from apd_gauntlet.assemble_inventory import assemble_inventory
    assert assemble_inventory(tmp_path) == 0


def test_assemble_inventory_identity_no_provenance(tmp_path):
    """Identity with no provenance key at all gets a deterministic id (locator='')."""
    from apd_gauntlet.assemble_inventory import assemble_inventory
    inv = {
        "schema_version": 1,
        "identities": [
            {"name": "anon-worker", "identity_type": "service_account"},
        ],
    }
    _write_inv(tmp_path, inv)
    assemble_inventory(tmp_path)
    out = yaml.safe_load((tmp_path / "00-context" / "asset-inventory.yaml").read_text())
    assert out["identities"][0]["identity_id"] == compute_identity_id("anon-worker", "")


def test_assemble_inventory_crosses_unknown_name_passes_through(tmp_path):
    """A crosses entry that doesn't match any asset name is left unchanged."""
    from apd_gauntlet.assemble_inventory import assemble_inventory
    inv = {
        "schema_version": 1,
        "assets": [
            {"name": "svc", "asset_type": "service",
             "provenance": {"source": "artifact", "artifact": "x.md", "locator": "L1"}},
        ],
        "trust_boundaries": [
            {"name": "tb1",
             "crosses": ["svc", "ghost-asset"],
             "provenance": {"source": "artifact", "artifact": "x.md", "locator": "L9"}},
        ],
    }
    _write_inv(tmp_path, inv)
    assemble_inventory(tmp_path)
    out = yaml.safe_load((tmp_path / "00-context" / "asset-inventory.yaml").read_text())
    crosses = out["trust_boundaries"][0]["crosses"]
    assert crosses[0].startswith("asset-")   # known name resolved
    assert crosses[1] == "ghost-asset"        # unknown name passes through
