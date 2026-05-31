"""rejected-records schema: failed-validation + stale-downgrade categories."""
from __future__ import annotations

import json
import pathlib

from jsonschema import Draft202012Validator

REPO = pathlib.Path(__file__).parent.parent
SCHEMA = REPO / "schemas" / "rejected-records.schema.json"


def _validator():
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


def test_minimal_rejected_doc():
    doc = {"schema_version": 1, "generated_by": "synthesizer",
           "rejected": [{"id": "conf-7aa376c5", "reason": "failed schema validation",
                         "category": "failed_validation"}]}
    assert list(_validator().iter_errors(doc)) == []


def test_stale_downgrade_record():
    doc = {"schema_version": 1, "generated_by": "synthesizer",
           "rejected": [{"id": "conf-cap-89e19793", "reason": "evidence supports designed only",
                         "category": "stale_capability_downgrade",
                         "from_maturity": "tested", "to_maturity": "designed"}]}
    assert list(_validator().iter_errors(doc)) == []


def test_rejects_short_reason():
    doc = {"schema_version": 1, "generated_by": "synthesizer",
           "rejected": [{"id": "x", "reason": "no", "category": "failed_validation"}]}
    assert list(_validator().iter_errors(doc))  # reason minLength 10
