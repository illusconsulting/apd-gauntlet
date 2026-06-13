# Manual audit prompts

Each blocked finding below needs a runtime signal a static review cannot provide. Run the paired command(s) against the live system and attach the output as the prerequisite evidence.

## dist-11111111 — NetworkPolicy enforcement state unknown for claim-events namespace

**Prerequisite evidence:**

- Live confirmation that the cluster CNI enforces NetworkPolicy objects.

**Suggested audit commands:**

```bash
kubectl get networkpolicies -A
```

## auth-22222222 — istio PeerAuthentication runtime mTLS mode unverified

**Prerequisite evidence:**

- Effective runtime mTLS mode after workload-level PeerAuthentication overrides.

**Suggested audit commands:**

```bash
kubectl get peerauthentications.security.istio.io -A
istioctl proxy-config secret -n production
```

## ephem-33333333 — istio workload secret rotation lifetime not observable from manifests

**Prerequisite evidence:**

- Actual issued workload certificate TTL on the production namespace.

**Suggested audit commands:**

```bash
istioctl proxy-config secret -n production
```

## conf-44444444 — KMS DEK rotation cadence not specified in artifacts

**Prerequisite evidence:**

- DEK rotation policy document with cadence and revocation runbook.

No infrastructure command template matched; review manually against the prerequisite evidence above.
