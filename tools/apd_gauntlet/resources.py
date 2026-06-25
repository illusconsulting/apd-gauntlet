"""Wheel-safe access to packaged framework resources (JSON Schemas, domain packs).

Every read of a framework resource MUST go through this module so it resolves
package-relative via importlib.resources and survives a pip-wheel install — where
the repo root and its former sibling schemas/ and domains/ trees do not exist
(repo checkouts keep working via the committed repo-root symlinks, but the wheel
relies on these accessors). Mirrors report/build.py: the Traversable is coerced to
a real pathlib.Path, valid because pip/uv install wheels unzipped."""
from __future__ import annotations

import json
import pathlib
from functools import lru_cache
from importlib import resources
from typing import Any, cast


@lru_cache(maxsize=1)
def data_dir() -> pathlib.Path:
    """Absolute path to the packaged ``tools/apd_gauntlet/data`` root."""
    return pathlib.Path(str(resources.files("apd_gauntlet") / "data"))


def schemas_dir() -> pathlib.Path:
    """Directory of packaged ``*.schema.json`` files."""
    return data_dir() / "schemas"


def domains_dir() -> pathlib.Path:
    """Directory of packaged built-in domain packs."""
    return data_dir() / "domains"


def read_schema(filename: str) -> dict[str, Any]:
    """Parse one packaged schema, e.g. ``read_schema("domain.schema.json")``."""
    text = (schemas_dir() / filename).read_text(encoding="utf-8")
    return cast("dict[str, Any]", json.loads(text))
