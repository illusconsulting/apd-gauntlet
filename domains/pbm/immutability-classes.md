# PBM required-immutable data classes

For a PBM, the following data classes must not change once written:

- Audit log entries (HIPAA 6-year retention, SOC 2 audit trail)
- Claim adjudication outcomes (regulatory and contractual reconcilability)
- Submitted CMS PDE records (CMS submission integrity)
- Backups (ransomware resilience)
- Configuration history (change traceability, RCA evidence)
- Signed agreements and consent records
- Member communications and notifications (proof of delivery)
- Prior authorization decisions
- Drug formulary historical state at point of adjudication

Specialists raise Immutability findings against any class on this list that has mutable storage or absent retention controls.
