"""Refresh MITRE D3FEND reference data for the apd-gauntlet.

This module fetches D3FEND's published defensive-to-offensive technique
mappings, projects each defensive technique to a compact JSON shape, and
writes the result (with ``source_sha256``, ``fetched_at``, and ``source_url``
metadata) to ``tools/apd_gauntlet/data/d3fend.json``.

Security hardening mirrors :mod:`apd_gauntlet.refresh_cwe` and
:mod:`apd_gauntlet.refresh_owasp`:

* ``DEFAULT_TIMEOUT_SECONDS = 60`` — bounds time spent waiting for upstream.
* ``MAX_RESPONSE_BYTES = 200 MiB`` — bounds memory if upstream is compromised.
* Defense in depth: a ``Content-Length`` pre-check AND a post-read size check
  (the header may be missing, or it may lie).

**Upstream shape (verified 2026-05-25):** the URL returns SPARQL-JSON-results
(``{head:{vars:[...]}, results:{bindings:[ {var: {type, value}}, ...]}}``)
with **one row per (defensive_technique, ATT&CK_technique)** edge. The exact
field names — ``def_tech``, ``def_tech_label``, ``off_tech_id`` — are pinned
in :func:`project_d3fend_json`. The plan documents this as JSON-LD because
that's how D3FEND publishes the *ontology itself*, but this specific endpoint
delivers a precomputed SPARQL projection of the same facts. The IRI parser
in :func:`_iri_to_d3fend_id` tolerates either shape.

**D3FEND IRIs use the long defensive-technique class name** (e.g.
``...d3fend.owl#NetworkTrafficFiltering``), not the short ``D3-NTF`` code,
so :func:`_iri_to_d3fend_id` consults a seeded long-name→short-code map
harvested from the live D3FEND API. The map covers all 149 defensive
techniques in the current D3FEND release; unknown long names return
``None`` rather than fabricating a code.

**``counters_attack`` cross-reference**: this is the field that powers the
APD validator's "D3FEND counters_attack must intersect capability's
mitre_attack" check (Task 17 of the v1.2 plan). Each defensive entry's
``counters_attack`` is the set of ATT&CK technique IDs (``T####`` or
``T####.###`` sub-techniques) that the D3FEND ontology says this defensive
technique counters.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

D3FEND_JSON_URL = (
    "https://d3fend.mitre.org/api/ontology/inference/d3fend-full-mappings.json"
)
DEFAULT_TIMEOUT_SECONDS = 60
# Hard cap on the fetched payload size to bound memory if upstream misbehaves.
# The live response is ~45 MB; 200 MiB leaves comfortable headroom while still
# being a useful guardrail.
MAX_RESPONSE_BYTES = 200 * 1024 * 1024  # 200 MiB


def fetch_d3fend_json() -> bytes:
    """Fetch the D3FEND full-mappings document. Returns the raw bytes.

    Raises ``ValueError`` if the response exceeds :data:`MAX_RESPONSE_BYTES`
    (checked twice: once via ``Content-Length``, once after reading).
    """
    with urlopen(D3FEND_JSON_URL, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                advertised = int(content_length)
            except (TypeError, ValueError):
                advertised = None
            if advertised is not None and advertised > MAX_RESPONSE_BYTES:
                raise ValueError(
                    f"D3FEND response Content-Length ({advertised}) "
                    f"exceeds maximum ({MAX_RESPONSE_BYTES})"
                )
        body: bytes = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError(
            f"D3FEND response body exceeds maximum ({MAX_RESPONSE_BYTES} bytes); "
            "refusing to load. Verify the upstream feed before retrying."
        )
    return body


def project_d3fend_json(json_bytes: bytes) -> dict[str, Any]:
    """Project D3FEND's SPARQL-JSON-results payload into a compact runtime shape.

    Walks ``results.bindings``, groups rows by their ``def_tech`` IRI, and
    emits one entry per defensive technique with the merged set of
    ATT&CK techniques it counters. Rows whose ``def_tech`` IRI does not
    resolve to a known short code are skipped (rather than fabricating
    a code from the long name) — keeping the output strictly verifiable
    against the D3FEND release in use.

    Also accepts the JSON-LD ``@graph`` shape documented in the v1.2 plan,
    in case D3FEND adds that endpoint or evolves the live shape: nodes whose
    ``@type`` includes ``d3fend:Technique`` are projected the same way, with
    ``d3fend:d3f-counters`` relations yielding the ``counters_attack`` set.

    ``source_sha256`` is computed over the *raw* upstream bytes (matching
    the Task 9 fix in :mod:`apd_gauntlet.refresh_owasp`) so consumers can
    audit the exact payload received.
    """
    data = json.loads(json_bytes)
    entries: dict[str, dict[str, Any]] = {}

    # --- SPARQL-JSON-results shape (current live API) --------------------
    bindings = (
        data.get("results", {}).get("bindings", []) if isinstance(data, dict) else []
    )
    for row in bindings:
        if not isinstance(row, dict):
            continue
        def_tech_iri = _binding_value(row, "def_tech")
        if not def_tech_iri:
            continue
        d3fend_id = _iri_to_d3fend_id(def_tech_iri)
        if not d3fend_id:
            continue
        name = _binding_value(row, "def_tech_label") or ""
        off_tech_id = _binding_value(row, "off_tech_id")
        attack_id = _normalise_attack_id(off_tech_id) or _iri_to_attack_id(
            _binding_value(row, "off_tech")
        )
        entry = entries.setdefault(
            d3fend_id,
            {
                "d3fend_id": d3fend_id,
                "name": name,
                "counters_attack_set": set(),
            },
        )
        # Keep the first non-empty name we see; later rows are duplicates.
        if not entry["name"] and name:
            entry["name"] = name
        if attack_id:
            entry["counters_attack_set"].add(attack_id)

    # --- JSON-LD @graph shape (plan-documented future-proof path) --------
    for node in data.get("@graph", []) if isinstance(data, dict) else []:
        if not isinstance(node, dict):
            continue
        ntype = node.get("@type")
        type_list = ntype if isinstance(ntype, list) else [ntype]
        if "d3fend:Technique" not in type_list:
            continue
        iri = node.get("@id", "")
        d3fend_id = _iri_to_d3fend_id(iri, node=node)
        if not d3fend_id:
            continue
        name = _label(node)
        entry = entries.setdefault(
            d3fend_id,
            {
                "d3fend_id": d3fend_id,
                "name": name,
                "counters_attack_set": set(),
            },
        )
        if not entry["name"] and name:
            entry["name"] = name
        for relation in node.get("d3fend:d3f-counters", []) or []:
            attack_iri = (
                relation.get("@id") if isinstance(relation, dict) else relation
            )
            attack_id = _iri_to_attack_id(attack_iri)
            if attack_id:
                entry["counters_attack_set"].add(attack_id)

    # Finalise: sort the counter set into a list, drop the working set field,
    # and sort entries by d3fend_id for deterministic diffs across refreshes.
    final_entries: list[dict[str, Any]] = []
    for entry in entries.values():
        counters = sorted(entry.pop("counters_attack_set"))
        entry["counters_attack"] = counters
        final_entries.append(entry)
    final_entries.sort(key=lambda e: e["d3fend_id"])

    return {
        "source_url": D3FEND_JSON_URL,
        "source_sha256": hashlib.sha256(json_bytes).hexdigest(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "entries": final_entries,
    }


# --------------------------------------------------------------------------
# IRI parsers
# --------------------------------------------------------------------------


def _binding_value(row: dict[str, Any], var: str) -> str | None:
    """Read ``row[var].value`` from a SPARQL-JSON-results binding row, defensively."""
    cell = row.get(var)
    if isinstance(cell, dict):
        value = cell.get("value")
        if isinstance(value, str):
            return value
    return None


def _iri_strip_to_last_segment(iri: str) -> str:
    """Trim an IRI to its final identifying segment.

    Handles ``http://.../d3fend.owl#TokenBinding`` (fragment),
    ``http://.../techniques/D3-NTF`` (path), and ``d3f:TokenBinding`` (CURIE)
    uniformly: the returned string is whatever follows the last ``#``, ``/``,
    or ``:`` separator, in that priority order.
    """
    if "#" in iri:
        iri = iri.rsplit("#", 1)[-1]
    if "/" in iri:
        iri = iri.rsplit("/", 1)[-1]
    if ":" in iri:
        iri = iri.rsplit(":", 1)[-1]
    return iri


def _iri_to_d3fend_id(iri: str, node: dict[str, Any] | None = None) -> str | None:
    """Extract a ``D3-XX`` short code from a D3FEND IRI or node.

    Strategy (in order):

    1. If a node carries an explicit ``d3fend:d3f-id`` (or ``d3f:d3f-id``)
       property starting with ``D3-``, use it. This path future-proofs the
       parser against D3FEND adopting a JSON-LD endpoint that exposes the
       short code directly.
    2. If the IRI's final segment already matches ``D3-XX``, use it.
    3. Look up the IRI's final segment in :data:`_LONG_NAME_TO_SHORT_CODE`
       (e.g. ``NetworkTrafficFiltering`` → ``D3-NTF``).

    Returns ``None`` for unknown long names rather than fabricating a code —
    the v1.2 validator treats absence as legitimate uncertainty.
    """
    if node is not None:
        explicit = node.get("d3fend:d3f-id") or node.get("d3f:d3f-id")
        if isinstance(explicit, str) and explicit.startswith("D3-"):
            return explicit
    if not iri:
        return None
    last = _iri_strip_to_last_segment(iri)
    if last.startswith("D3-"):
        return last
    return _LONG_NAME_TO_SHORT_CODE.get(last)


def _normalise_attack_id(value: str | None) -> str | None:
    """Normalise an ATT&CK technique id string (``T####`` or ``T####.###``).

    The SPARQL endpoint puts the ATT&CK ID in ``off_tech_id`` as a plain
    string literal, so this is just a shape check: starts with ``T``,
    followed by 4 digits, optionally followed by ``.``+digits for
    sub-techniques.
    """
    if not value:
        return None
    if (
        len(value) >= 5
        and value[0] == "T"
        and value[1:5].isdigit()
        and (len(value) == 5 or value[5] == "." or value[5:6] == "")
    ):
        return value
    return None


def _iri_to_attack_id(iri: str | None) -> str | None:
    """Extract a ``T####`` or ``T####.###`` ID from an ATT&CK IRI fragment."""
    if not iri:
        return None
    last = _iri_strip_to_last_segment(iri)
    return _normalise_attack_id(last)


def _label(node: dict[str, Any]) -> str:
    """Best-effort extraction of an RDF/JSON-LD label from a node."""
    label = node.get("rdfs:label") or node.get("label") or ""
    if isinstance(label, dict):
        return str(label.get("@value", ""))
    if isinstance(label, list):
        for item in label:
            if isinstance(item, str):
                return item
            if isinstance(item, dict) and "@value" in item:
                return str(item["@value"])
        return ""
    return label if isinstance(label, str) else ""


def refresh_d3fend(output_path: Path | None = None) -> Path:
    """Fetch, project, and write D3FEND reference data. Returns the output path."""
    if output_path is None:
        output_path = Path(__file__).parent / "data" / "d3fend.json"
    json_bytes = fetch_d3fend_json()
    projected = project_d3fend_json(json_bytes)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(projected, indent=2, sort_keys=True))
    return output_path


# --------------------------------------------------------------------------
# Seeded long-name -> short-code map
# --------------------------------------------------------------------------
# Harvested from the live D3FEND API (``/api/offensive-technique/attack/<id>.json``
# returns ``def_tech_id`` alongside ``def_tech``) on 2026-05-25, covering all
# 149 defensive techniques in the current D3FEND release. The refresh script
# uses this to project the live SPARQL-JSON-results document — whose
# ``def_tech`` IRIs use long class names rather than short codes — into the
# stable ``D3-XX`` codes the APD validator expects in ``counters_attack``.
#
# When a future D3FEND release adds new techniques, supplement this map
# (don't replace it). Unknown long names project to ``None`` and the
# corresponding rows are skipped, so a partial update degrades cleanly.
_LONG_NAME_TO_SHORT_CODE: dict[str, str] = {
    "AccessModeling": "D3-AM",
    "AccountLocking": "D3-AL",
    "AdministrativeNetworkActivityAnalysis": "D3-ANAA",
    "AgentAuthentication": "D3-AA",
    "Application-basedProcessIsolation": "D3-ABPI",
    "ApplicationConfigurationHardening": "D3-ACH",
    "ApplicationExceptionMonitoring": "D3-AEM",
    "ApplicationProtocolCommandAnalysis": "D3-APCA",
    "AssetVulnerabilityEnumeration": "D3-AVE",
    "AuthenticationCacheInvalidation": "D3-ANCI",
    "BootloaderAuthentication": "D3-BA",
    "Certificate-basedAuthentication": "D3-CBAN",
    "CertificateAnalysis": "D3-CA",
    "CertificatePinning": "D3-CP",
    "CertificateRotation": "D3-CERO",
    "ChangeDefaultPassword": "D3-CDP",
    "Client-serverPayloadProfiling": "D3-CSPP",
    "ConfigurationInventory": "D3-CI",
    "ConnectionAttemptAnalysis": "D3-CAA",
    "ContainerImageAnalysis": "D3-CIA",
    "ContentFiltering": "D3-CF",
    "ContentModification": "D3-CM",
    "ContentQuarantine": "D3-CQ",
    "CredentialCompromiseScopeAnalysis": "D3-CCSA",
    "CredentialHardening": "D3-CH",
    "CredentialRevocation": "D3-CR",
    "CredentialRotation": "D3-CRO",
    "CredentialScrubbing": "D3-CS",
    "CredentialTransmissionScoping": "D3-CTS",
    "DNSAllowlisting": "D3-DNSAL",
    "DNSDenylisting": "D3-DNSDL",
    "DNSTrafficAnalysis": "D3-DNSTA",
    "DataInventory": "D3-DI",
    "DatabaseQueryStringAnalysis": "D3-DQSA",
    "DecoyEnvironment": "D3-DE",
    "DecoyFile": "D3-DF",
    "DecoyNetworkResource": "D3-DNR",
    "DecoyUserCredential": "D3-DUC",
    "DisableRemoteAccess": "D3-DRA",
    "DiskEncryption": "D3-DENCR",
    "DiskErasure": "D3-DKE",
    "DiskFormatting": "D3-DKF",
    "DiskPartitioning": "D3-DKP",
    "DomainAccountMonitoring": "D3-DAM",
    "DomainLogicValidation": "D3-DLV",
    "DomainTrustPolicy": "D3-DTP",
    "DynamicAnalysis": "D3-DA",
    "EmailFiltering": "D3-EF",
    "EmailRemoval": "D3-ER",
    "EmulatedFileAnalysis": "D3-EFA",
    "EndpointHealthBeacon": "D3-EHB",
    "ExecutableAllowlisting": "D3-EAL",
    "ExecutableDenylisting": "D3-EDL",
    "FileAnalysis": "D3-FA",
    "FileCarving": "D3-FC",
    "FileCreationAnalysis": "D3-FCA",
    "FileEncryption": "D3-FE",
    "FileEviction": "D3-FEV",
    "FileFormatVerification": "D3-FFV",
    "FileIntegrityMonitoring": "D3-FIM",
    "FirmwareBehaviorAnalysis": "D3-FBA",
    "FirmwareEmbeddedMonitoringCode": "D3-FEMC",
    "FirmwareVerification": "D3-FV",
    "ForwardResolutionDomainDenylisting": "D3-FRDDL",
    "Hardware-basedProcessIsolation": "D3-HBPI",
    "Hardware-basedWriteProtection": "D3-HBWP",
    "HardwareComponentInventory": "D3-HCI",
    "HomoglyphDetection": "D3-HD",
    "HostReboot": "D3-HR",
    "HostShutdown": "D3-HS",
    "IOPortRestriction": "D3-IOPR",
    "IPCTrafficAnalysis": "D3-IPCTA",
    "IdentifierActivityAnalysis": "D3-IAA",
    "InboundSessionVolumeAnalysis": "D3-ISVA",
    "InboundTrafficFiltering": "D3-ITF",
    "InputDeviceAnalysis": "D3-IDA",
    "Kernel-basedProcessIsolation": "D3-KBPI",
    "LocalAccountMonitoring": "D3-LAM",
    "LocalFilePermissions": "D3-LFP",
    "LogicalLinkMapping": "D3-LLM",
    "MemoryBoundaryTracking": "D3-MBT",
    "Multi-factorAuthentication": "D3-MFA",
    "NetworkNodeInventory": "D3-NNI",
    "NetworkResourceAccessMediation": "D3-NRAM",
    "NetworkTrafficCommunityDeviation": "D3-NTCD",
    "NetworkTrafficFiltering": "D3-NTF",
    "NetworkTrafficPolicyMapping": "D3-NTPM",
    "NetworkTrafficSignatureAnalysis": "D3-NTSA",
    "One-timePassword": "D3-OTP",
    "OperationalProcessMonitoring": "D3-OPM",
    "OutboundTrafficFiltering": "D3-OTF",
    "PasswordAuthentication": "D3-PWA",
    "PasswordRotation": "D3-PR",
    "PerHostDownload-UploadRatioAnalysis": "D3-PHDURA",
    "PhysicalLinkMapping": "D3-PLM",
    "ProcessCodeSegmentVerification": "D3-PCSV",
    "ProcessLineageAnalysis": "D3-PLA",
    "ProcessSegmentExecutionPrevention": "D3-PSEP",
    "ProcessSelf-ModificationDetection": "D3-PSMD",
    "ProcessSpawnAnalysis": "D3-PSA",
    "ProcessSuspension": "D3-PS",
    "ProcessTermination": "D3-PT",
    "ProtocolMetadataAnomalyDetection": "D3-PMAD",
    "RPCTrafficAnalysis": "D3-RTA",
    "RadiationHardening": "D3-RH",
    "RegistryKeyDeletion": "D3-RKD",
    "ReissueCredential": "D3-RIC",
    "RelayPatternAnalysis": "D3-RPA",
    "RemoteFileAccessMediation": "D3-RFAM",
    "RemoteTerminalSessionDetection": "D3-RTSD",
    "RestoreConfiguration": "D3-RC",
    "RestoreDatabase": "D3-RD",
    "RestoreEmail": "D3-RE",
    "RestoreFile": "D3-RF",
    "RestoreNetworkAccess": "D3-RNA",
    "RestoreSoftware": "D3-RS",
    "RestoreUserAccountAccess": "D3-RUAA",
    "ReverseResolutionIPDenylisting": "D3-RRID",
    "ScheduledJobAnalysis": "D3-SJA",
    "SegmentAddressOffsetRandomization": "D3-SAOR",
    "SenderMTAReputationAnalysis": "D3-SMRA",
    "SenderReputationAnalysis": "D3-SRA",
    "ServiceBinaryVerification": "D3-SBV",
    "SessionTermination": "D3-ST",
    "ShadowStackComparisons": "D3-SSC",
    "SoftwareInventory": "D3-SWI",
    "SoftwareUpdate": "D3-SU",
    "StackFrameCanaryValidation": "D3-SFCV",
    "StrongPasswordPolicy": "D3-SPP",
    "SystemCallAnalysis": "D3-SCA",
    "SystemCallFiltering": "D3-SCF",
    "SystemConfigurationPermissions": "D3-SCP",
    "SystemDaemonMonitoring": "D3-SDM",
    "SystemFileAnalysis": "D3-SFA",
    "SystemFirmwareVerification": "D3-SFV",
    "SystemInitConfigAnalysis": "D3-SICA",
    "SystemVulnerabilityAssessment": "D3-SYSVA",
    "Token-basedAuthentication": "D3-TBA",
    "TokenBinding": "D3-TB",
    "TrustedLibrary": "D3-TL",
    "URLAnalysis": "D3-UA",
    "URLReputationAnalysis": "D3-URA",
    "UnlockAccount": "D3-ULA",
    "UserAccountPermissions": "D3-UAP",
    "UserGeolocationLogonPatternAnalysis": "D3-UGLPA",
    "UserSessionInitConfigAnalysis": "D3-USICA",
    "VariableInitialization": "D3-VI",
    "VideoSurveillance": "D3-VS",
    "WebSessionAccessMediation": "D3-WSAM",
}


if __name__ == "__main__":
    print(f"Wrote {refresh_d3fend()}")
