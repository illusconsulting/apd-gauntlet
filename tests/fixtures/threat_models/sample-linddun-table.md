# PBM Member Portal LINDDUN Privacy Threat Model

| Data Flow | L | I | N | D | D | U | N |
|-----------|---|---|---|---|---|---|---|
| Member login flow | Cross-session user tracking via fingerprint | SSN visible in profile API response | Login timestamp stored and attributable to member | Login event observable to third-party CDN | Browser autofill leaks plan-member ID | No consent gate on analytics SDK init | HIPAA breach notification not triggered on this surface |
| Claim history download | — | Member ID embedded in CSV filename | — | Download event logged in CDN metrics | — | — | — |
| Pharmacy lookup search | Search terms tied to authenticated session | — | — | — | — | — | — |
