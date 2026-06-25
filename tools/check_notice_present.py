"""CI gate: NOTICE must attribute every redistribution-restricted bundled KB."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REQUIRED = [
    "mitre-attack-techniques.json", "capec.json", "cwe.json", "d3fend.json",
    "atlas-techniques.json", "masvs.json", "maswe.json",
    "owasp_top10.json", "owasp_api_top10.json", "owasp_llm_top10.json",
]
notice = (REPO / "NOTICE").read_text(encoding="utf-8")
missing = [f for f in REQUIRED if f not in notice]
if missing:
    print("NOTICE is missing attribution for:", missing)
    sys.exit(1)
print("NOTICE present for all attribution-required KBs.")
