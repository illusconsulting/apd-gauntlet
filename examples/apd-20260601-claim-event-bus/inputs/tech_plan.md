# Claim Event Bus — Tech Plan

## §1 Overview

The claim event bus is a Kafka-based topic that emits claim adjudication events to downstream consumers (reporting, fraud detection, member portal updates).

## §2 Goals

- Decouple adjudication from downstream consumers.
- Provide near-real-time visibility into claim status changes.
- Enable horizontal scale of consumers without changing the adjudication path.

## §3 KMS Hierarchy

The KMS hierarchy uses AWS KMS as the root. A DEK-issuer service mints data encryption keys on demand. Application-level decryption is performed at query time with a 5-minute in-memory DEK cache.

[NOTE: rotation cadence, automation, and revocation procedure are NOT specified in this tech plan.]

## §4 Event Bus Architecture

### §4.1 Topic configuration

The `claim-events` topic has 12 partitions, replication factor 3, retention 7 days.

### §4.2 Encryption posture

All Kafka topics use AES-256 at-rest encryption via broker-managed keys. TLS 1.2+ in transit between producers, brokers, and consumers.

## §5 Data at Rest

### §5.1 Database

Adjudication outcomes are persisted to a PostgreSQL RDS cluster with field-level envelope encryption applied to PHI columns in the `member_demographics` and `claims` tables.

### §5.2 Audit log

Audit entries (PHI access, configuration changes, authentication events) are written to a `audit_log` table in the same RDS cluster. The table is a normal append-only table with application-level discipline — no WORM enforcement at the database level.

## §6 Availability

The system targets 99.95% uptime over a rolling 30-day window. RTO is 4 hours; RPO is 15 minutes. DR failover has not been tested in the last 12 months.

## §7 Multi-Region

The system is deployed in a single AWS region (us-east-1) with multi-AZ active-passive within that region. Cross-region failover is not yet implemented.

## §8 Authentication

Member portal: OAuth + MFA via Okta. MFA factors accepted: TOTP, push, SMS (fallback).
Internal admin tools: SAML SSO with Okta, MFA required.
Service-to-service: shared bearer tokens stored in HashiCorp Vault.
