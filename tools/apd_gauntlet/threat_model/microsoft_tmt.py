"""Parser for Microsoft Threat Modeling Tool .tm7 XML files.

Microsoft TMT (Threat Modeling Tool 2016/2022) is one of the most widely-used
commercial threat modeling tools in enterprise environments.  Its native export
format is a UTF-8 XML file with the ``.tm7`` extension.

Security notes
--------------
* XXE-hardened: ``resolve_entities=False``, ``no_network=True``,
  ``load_dtd=False``.  External entity payloads are silently ignored.
* Best-effort recovery: ``recover=True`` lets lxml return whatever could be
  parsed from a truncated or malformed file rather than raising an exception.
"""

from __future__ import annotations

import hashlib
from typing import Any

from lxml import etree

from .mappings import stride_letter_to_apd_goals

# Microsoft TMT namespace — constant across TMT 2016+ versions.
_TMT_NS = "{http://schemas.datacontract.org/2004/07/ThreatModeling.Model}"

_TMT_CATEGORY_TO_STRIDE: dict[str, str] = {
    "Spoofing":               "S",
    "Tampering":              "T",
    "Repudiation":            "R",
    "Information Disclosure": "I",
    "Denial of Service":      "D",
    "Elevation of Privilege": "E",
}

# First-word prefixes for TMT custom-template category strings
# e.g. "Spoofing the External Entity" → first word "Spoofing" → "S"
_STRIDE_PREFIXES: dict[str, str] = {
    "Spoofing":    "S",
    "Tampering":   "T",
    "Repudiation": "R",
    "Information": "I",
    "Denial":      "D",
    "Elevation":   "E",
}


def _category_to_stride_letter(category: str) -> str | None:
    """Map a TMT Category string to a single-letter STRIDE code.

    Tries exact match first, then falls back to first-word prefix matching
    (handles TMT custom-template strings such as "Spoofing the External Entity"
    or "Tampering with Data Flow").  Returns ``None`` for unrecognized
    categories or empty strings.
    """
    if not category:
        return None
    if category in _TMT_CATEGORY_TO_STRIDE:
        return _TMT_CATEGORY_TO_STRIDE[category]
    words = category.split()
    first_word = words[0] if words else ""
    return _STRIDE_PREFIXES.get(first_word)


def _get_property(value_elem: etree._Element, key: str) -> str | None:
    """Return the property value matching *key* from a TMT Value element.

    Searches ``<Properties><KeyValueOfstringstring>`` children for a
    ``<Key>`` text matching *key* and returns the corresponding ``<Value>``
    text, or ``None`` if not found.
    """
    props_container = value_elem.find(f"{_TMT_NS}Properties")
    if props_container is None:
        return None
    for kv in props_container.iter(f"{_TMT_NS}KeyValueOfstringstring"):
        k_elem = kv.find(f"{_TMT_NS}Key")
        v_elem = kv.find(f"{_TMT_NS}Value")
        if k_elem is not None and k_elem.text == key and v_elem is not None:
            return v_elem.text
    return None


def _build_element_index(root: etree._Element) -> dict[str, str]:
    """Build a GUID → element-name mapping from the ``Borders`` section.

    Each ``<KeyValueOfguidanyType>`` inside ``<Borders>`` represents a diagram
    element (Process, DataStore, DataFlow, ExternalInteractor, etc.).  We index
    them by their ``<Key>`` GUID (braces stripped) so that threat
    ``SourceGuid``/``TargetGuid`` lookups can resolve human-readable names.
    """
    index: dict[str, str] = {}
    for kv in root.iter(f"{_TMT_NS}KeyValueOfguidanyType"):
        key_elem = kv.find(f"{_TMT_NS}Key")
        value_elem = kv.find(f"{_TMT_NS}Value")
        if key_elem is None or value_elem is None or not key_elem.text:
            continue
        guid = key_elem.text.strip("{}")
        name = _get_property(value_elem, "Name")
        if name:
            index[guid] = name
    return index


def _stable_entry_id(*, asset: str, threat: str, source_locator: str) -> str:
    """Deterministic 8-hex-char ID, stable across runs for the same inputs."""
    raw = f"{asset}|{threat}|{source_locator}".encode()
    return f"tm-{hashlib.sha256(raw).hexdigest()[:8]}"


def _text_of(elem: etree._Element | None) -> str | None:
    return elem.text if elem is not None else None


def parse_microsoft_tmt(xml_bytes: bytes) -> list[dict[str, Any]]:
    """Parse a ``.tm7`` XML file into normalized threat-model entries.

    Uses lxml in ``recover`` mode (best-effort on malformed or truncated files)
    with full XXE hardening (``resolve_entities=False``, ``no_network=True``,
    ``load_dtd=False``).

    Returns an empty list when:
    * ``xml_bytes`` is empty or ``None``.
    * The document cannot be parsed at all (``root`` is ``None`` even after
      recovery).
    * The document contains no ``ThreatInstances``.

    Each returned dict conforms to the ``threat-model-normalized.schema.json``
    entries-array contract.
    """
    if not xml_bytes:
        return []

    parser = etree.XMLParser(
        recover=True,
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
    )
    try:
        root = etree.fromstring(xml_bytes, parser=parser)
    except etree.XMLSyntaxError:
        # recover=True normally suppresses this, but defend in depth.
        return []

    if root is None:
        return []

    element_index = _build_element_index(root)
    entries: list[dict[str, Any]] = []

    # ThreatInstances → each threat is wrapped in a KeyValue element whose
    # localname starts with "KeyValueOfstringThreat".  The suffix varies across
    # TMT versions (e.g. "KeyValueOfstringThreatpc_P0_PhOB") so we match by
    # prefix rather than exact name.
    #
    # Note: lxml's iter() yields comment and PI nodes whose .tag is a callable,
    # not a string.  Guard with isinstance before constructing QName.
    for threat_kv in root.iter():
        tag = threat_kv.tag
        if not isinstance(tag, str):
            continue  # skip _Comment, _ProcessingInstruction, etc.
        local = etree.QName(tag).localname
        if not local.startswith("KeyValueOfstringThreat"):
            continue

        key_elem = threat_kv.find(f"{_TMT_NS}Key")
        value_elem = threat_kv.find(f"{_TMT_NS}Value")
        if key_elem is None or value_elem is None or not key_elem.text:
            continue

        threat_guid = key_elem.text.strip("{}")

        # Title: prefer explicit Title property; fall back to <Title> element.
        title_via_property = _get_property(value_elem, "Title")
        title_elem = value_elem.find(f"{_TMT_NS}Title")
        title = title_via_property or _text_of(title_elem) or ""

        description = _get_property(value_elem, "Description") or ""

        # Category: prefer Category property; fall back to UserThreatCategory.
        category = (
            _get_property(value_elem, "Category")
            or _get_property(value_elem, "UserThreatCategory")
            or ""
        )

        # Mitigation prose lives in UserThreatDescription.  Empty string → None.
        mitigation = _get_property(value_elem, "UserThreatDescription") or None

        # Resolve asset name via SourceGuid first, then TargetGuid.
        source_guid = (_get_property(value_elem, "SourceGuid") or "").strip("{}")
        target_guid = (_get_property(value_elem, "TargetGuid") or "").strip("{}")
        asset = (
            element_index.get(source_guid)
            or element_index.get(target_guid)
            or "(unknown element)"
        )

        stride_letter = _category_to_stride_letter(category)
        apd_goals = stride_letter_to_apd_goals(stride_letter) if stride_letter else []
        confidence = "high" if stride_letter else "medium"
        source_locator = f"ThreatInstances/[Key={{guid={threat_guid}}}]"

        entries.append({
            "entry_id": _stable_entry_id(
                asset=asset,
                threat=title,
                source_locator=source_locator,
            ),
            "asset": asset,
            "threat": title or description or "(unnamed threat)",
            "mitigation": mitigation,
            "methodology": "stride",
            "source_locator": source_locator,
            "extraction_confidence": confidence,
            "framework_refs": {
                "stride_letter": stride_letter,
                "linddun_letter": None,
                "attack_tree_position": None,
                "mitre_attack": [],
            },
            "inferred_apd_goals": apd_goals,
        })

    return entries
