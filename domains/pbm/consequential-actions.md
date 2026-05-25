# PBM consequential-action surface

For a PBM, the following actions are consequential and must be auditable. Non-Repudiation findings evaluate logging coverage against this list.

- Any PHI access (read, export, print)
- Any adjudication decision (approve, deny, soft-deny)
- Any administrative configuration change (formulary, plan rules, prior authorization criteria, user role)
- Any authentication event (successful, failed, MFA challenge result)
- Any authorization decision that grants access to PHI or admin functions
- Any data export or report generation containing PHI
- Any vendor or partner API call carrying PHI
- Any change to system configuration affecting security posture
- Any break-glass or emergency override

This list is not exhaustive. Specialists should treat actions outside this list as candidates for inclusion — flagging them as evidence gaps until the operator confirms.
