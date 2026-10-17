"""APD Gauntlet — Python validator and CLI for the APD security architecture review framework."""
import re

__version__ = "1.7.1"


def release_of(version: str) -> str:
    """Return the X.Y.Z release of a PEP 440 version, without pre/post/dev/local parts.

    2.0.0a1 -> 2.0.0, 2.0.0.dev0 -> 2.0.0, 1.7.0.post1 -> 1.7.0, 1.7.0 -> 1.7.0.
    """
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if m is None:
        raise ValueError(f"not an X.Y.Z-based version: {version!r}")
    return m.group(0)


# The framework version stamped into run configs (run-config.schema.json requires
# X.Y.Z) and checked against each domain pack's framework_compat range. A
# pre-release engine (2.0.0a1) runs as the release it previews (2.0.0).
FRAMEWORK_VERSION = release_of(__version__)
