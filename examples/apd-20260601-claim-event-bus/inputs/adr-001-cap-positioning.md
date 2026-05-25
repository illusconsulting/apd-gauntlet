# ADR-001: CAP Positioning for Claim Event Bus

**Status:** Accepted
**Date:** 2026-04-15

## Context

We need to decide between strong consistency and availability under partition.

## Decision

In a partition, the system favors **consistency** for the adjudication engine and stops processing rather than risk diverging adjudication state. The downstream event-bus consumers may experience delay during a partition; this is acceptable because they are read-only.

## Consequences

- Adjudication latency may spike during cross-AZ partition.
- No "soft-deny" mode planned; system errors are surfaced to pharmacy POS.
