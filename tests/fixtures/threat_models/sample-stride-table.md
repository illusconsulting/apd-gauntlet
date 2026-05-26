# PBM Claim Event Bus STRIDE Threat Model

| Element | S | T | R | I | D | E |
|---------|---|---|---|---|---|---|
| claim-ingress-API | Pharmacy credential theft via phishing | Replay of submitted claim with altered NDC | — | Token logged in CloudFront access logs | High-volume duplicate submission DoS | Compromised pharmacy account elevated via missing tenant check |
| adjudication-service | mTLS cert pinning bypass via service mesh misconfig | Drug pricing data swap in transit | — | PHI included in error response body | Slow-query saturation of adjudication pool | — |
| audit-log-writer | — | — | Audit entry deletion via direct DynamoDB access | — | — | — |
