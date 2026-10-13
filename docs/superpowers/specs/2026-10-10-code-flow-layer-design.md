# Code-flow layer: control and data flow across functions and services — design

**Date:** 2026-10-10
**Status:** Draft, awaiting review
**Release line:** proposed for 2.1 on `next` (see §13)
**Related:** ADR-0007 (code recon), ADR-0019 (multi-repo recon), the IaC spec
(`2026-10-10-iac-terraform-opentofu-atmos-design.md`), and GRAML (arXiv
2610.09605).

## 1. Problem

Code evidence comes only from codebase-memory-mcp (CBM). CBM is a structural
knowledge graph:

- tree-sitter parsing with partial type resolution;
- calls, imports and routes;
- cross-service HTTP and async edges.

It has no control-flow graph. Its data flow is shallow (`DATA_FLOWS`: argument
to parameter, field-access chains). So it can show that a call path exists, but
not the questions ADR-0007 cites as the reason for code recon:

- Does every path from an entry point pass the identity check?
- Does every consequential write reach the audit emitter?
- Does request or PHI data reach a log, outbound call or store unsanitised?

The answers cross functions, frameworks and services. Languages in scope: Java,
Go, Python, TypeScript, plus GraphQL as an API contract.

## 2. Goals and non-goals

**Goals**

- For each pair of entry point and sink, give a verdict: `guarded`,
  `unguarded` (with a witness path) or `unknown` (with the unresolved edge that
  blocks the proof).
- Data flows from tagged sources to tagged sinks within a service.
- Cross-service edges anchored on contracts (OpenAPI, protobuf, AsyncAPI,
  GraphQL) and deployment config, with optional runtime confirmation from
  traces.
- Framework-enforced guards (middleware, decorators, annotations, directives)
  recognised as guards.
- Data flow diagrams (system level, per service and per handler) rendered
  from evidence.
- The join between infrastructure compute resources and the services they run
  (§9), so attack paths cross from network exposure into code.
- Compact, cited evidence packets for lenses, using the same selector as the
  IaC spec (§10 there).

**Non-goals**

- A single literal interprocedural control-flow graph. Interprocedural
  guarantees come from per-function summaries plus the call graph (§5.4).
- Dynamic analysis beyond ingesting traces the client exports.
- Languages beyond the five above.
- Running CodeQL on client code. Its licence forbids non-open-source code
  without a paid GitHub Advanced Security licence. Clients that already run it
  can supply SARIF (§5.9).

## 3. Proposed decisions (need approval)

| Question | Proposal |
|---|---|
| Engines | CBM (skeleton), OpenGrep (labelling), Joern (control and data flow within a service), graphql-core (GraphQL contracts) |
| Joern integration | Joern's CLI with bundled, fixed scripts through the `run_tool` gateway. No third-party Joern MCP server: codebadger is GPL-3.0, and its taint tools match variable names heuristically and never call `reachableByFlows`. |
| Interprocedural method | Per-function guard summaries plus a graph cut over the call graph (§5.4) |
| Cross-service edges | Contracts first, deployment config second, traces as confirmation |
| Agent role | Agents read packets and the index; they never run engines |
| Release | 2.1, after 2.0 GA (§13) |

## 4. Architecture

A new `code-flow` phase runs after `code-recon` and after `iac`, before
`threat-model-author`. It is one CLI step, `apd-gauntlet code-flow run
<run-dir>`, gated by `code_flow.mode`. All engines run through the IaC spec's
`run_tool` gateway, extended with the invocations listed in §11.

```text
CBM index ─┐
           ├─► call graph (+ unresolved markers)
Joern CPG ─┘          │
OpenGrep rules ─► entry / guard / sink / sanitiser / resolver tags
framework models ─► synthetic dispatch and middleware edges
           │
           ▼
   per-function guard summaries ─► graph cut ─► guarded / unguarded / unknown
           │
contracts + deploy config + IaC graph + traces ─► cross-service edges (labelled)
           │
           ▼
code-flow-index.yaml, code-flow-graph.yaml, dfd/*.md, code-flow-packets/<goal>.md
```

## 5. Units (`tools/apd_gauntlet/codeflow/`)

### 5.1 `services.py`

Defines service boundaries:

- from ADR-0019 `repos[]` (one service per repo, or per `role`);
- otherwise, from CBM projects.

Each service records its languages, detected from file extensions and build
files.

### 5.2 `labels.py` — OpenGrep rule packs

Bundled rules in `data/codeflow/rules/<language>/` tag:

- **entry points:** route registration, GraphQL resolvers, gRPC handlers,
  queue consumers, scheduled jobs;
- **guards:** authentication and authorisation checks, middleware
  registration;
- **sinks:** database writes, logging, outbound HTTP, file writes,
  PHI-classified fields;
- **sanitisers.**

OpenGrep runs offline with bundled rules only (no registry, metrics off).
Cross-function taint within a file is used as corroboration, never as the
verdict.

### 5.3 `frameworks.py` — dispatch and middleware models

Data-driven models in `data/codeflow/frameworks/*.yaml` turn framework
configuration into explicit edges: entry → middleware chain → handler, and
annotation or decorator guards → handler. Version 1 models:

- **Java:** Spring MVC and Spring Security (filter chain, `@PreAuthorize`,
  `@Secured`), Spring for GraphQL (`@QueryMapping`, `@SchemaMapping`), Netflix
  DGS (`@DgsQuery`, `@DgsMutation`).
- **Go:** `net/http`, chi, gin, echo middleware; gqlgen generated resolvers
  (`schema.resolvers.go`).
- **Python:** FastAPI (`Depends`, router dependencies), Django (middleware,
  decorators), Flask (decorators), Strawberry and Graphene resolvers.
- **TypeScript:** Express (`app.use`, router-level middleware), NestJS (guards,
  interceptors, decorators), Apollo Server resolver maps, graphql-shield rules.

A framework a service uses but no model covers produces an `unknown` on every
entry point it dispatches.

### 5.4 `joern.py` and `summaries.sc` — per-function guard summaries

For each service and language, build a code property graph with the matching
frontend (`javasrc2cpg`, `gosrc2cpg`, `pysrc2cpg`, `jssrc2cpg`, which also
parses TypeScript). Then run the bundled script, which emits JSON per method:

- **call sites,** with line numbers and resolved targets;
- **guarded call sites:** call sites whose execution is controlled by a
  guard's outcome. The site must be control-dependent on the guard's result,
  or post-dominated by an early exit or throw on guard failure. Merely calling
  the guard and ignoring its result does not count.
- **source-to-sink data flows** for the tagged pairs (`reachableByFlows`),
  with the statement path.

**The graph cut.** `cut.py` decides each verdict over the merged call graph:

1. Delete every call edge whose call site is guarded, plus every
   framework-model edge that passes a guard.
2. If the sink is still reachable from the entry point, the verdict is
   `unguarded`, with the remaining path as the witness.
3. If it is reachable only through an unresolved edge (CBM `USAGE`, a Joern
   unresolved call, or an unmodelled framework), the verdict is `unknown`,
   naming that edge.
4. Otherwise, `guarded`.

### 5.5 `callgraph.py`

Merges CBM `CALLS`, Joern call edges and framework edges. Each edge records
where it came from (`cbm`, `joern`, `framework`, or several), and unresolved
call sites stay in the graph as explicit unresolved nodes. A per-language
resolver for higher precision, such as Go's `go/ssa` with VTA call graphs, is a
later addition, made only where the evaluation shows the call graph is the
bottleneck.

### 5.6 `graphql.py`

- **Schema and resolvers:** parse the SDL with graphql-core and map each field
  to its resolver through the framework models.
- **Client operations:** parse operations in client code (`gql` template
  literals, `.graphql` files) into operation → field edges.
- **Guards:** schema directives (`@auth`, federation's `@authenticated` and
  `@requiresScopes`) and graphql-shield rules are field-level guards.
- **Federation:** the supergraph or router configuration maps fields to
  subgraphs.
- **Entry points:** every field is one, so authentication on the `/graphql`
  route alone never marks a field guarded.

### 5.7 `contracts.py` and `deploy.py` — edges between services

- **Contracts:** OpenAPI, protobuf, AsyncAPI and GraphQL schemas match client
  call sites to server handlers. They raise or confirm CBM's `HTTP_CALLS`
  confidence. Queue edges match on topic names at both ends.
- **Deployment config** resolves hostnames and URLs to services, and adds
  guards on edges (mTLS, JWT authorizers, mesh authorization policies):
  - Kubernetes Services and Ingress;
  - Istio `AuthorizationPolicy` and `PeerAuthentication`;
  - API gateway routes;
  - the IaC graph.

### 5.8 `traces.py` — optional confirmation

Ingests OpenTelemetry trace exports (OTLP JSON files declared in run-config)
into observed service-to-service and route edges. Each cross-service edge is
labelled:

- `confirmed`: found statically and observed;
- `static_only`;
- `runtime_only`: the static model missed it, which flags a model gap.

### 5.9 `sarif.py`

Ingests client-supplied SARIF (CodeQL, Semgrep Pro and others) as `flow`
entries with the tool recorded. SARIF results are corroborating evidence, not
verdicts.

### 5.10 `dfd.py` and `context.py`

- **`dfd.py`** renders Mermaid data flow diagrams:
  - L0, the system and external entities;
  - L1, services and data stores;
  - L2, handlers to stores within a service.

  Flows are labelled with data classes such as PHI, and trust boundaries come
  from the IaC graph and intake. Diagrams are capped in size, and anything
  beyond the cap is listed, not drawn.
- **Packets** reuse the IaC spec's selector (`iac/context.py`, generalised into
  `apd_gauntlet/context/`). For code, GRAML's own relation weights are the
  natural starting point: data dependence 0.50, control dependence 0.30,
  control flow and calls 0.20. They are then tuned and frozen on the
  development corpus.

## 6. Outputs

- `00-context/code-flow-index.yaml` (schema `code-flow-index.schema.json`).
  - **Entry ids:** `cfx-` plus the first 8 hex characters of a SHA-256 over
    the service, kind and location, minted by the engine.
  - **Kinds:** `verdict` (with `outcome: guarded|unguarded|unknown`), `flow`,
    `entry_point`, `guard`, `sink`, `unknown`.
  - **Every entry carries:** file, line range, verbatim excerpt, service, edge
    provenance, confidence and APD relevance.
- `00-context/code-flow-graph.yaml`: nodes and edges with provenance and
  labels.
- `00-context/dfd/{l0,l1-<service>,l2-<service>-<handler>}.md`.
- `00-context/code-flow-packets/<goal>.md`.

The citation locator is `cf:<service>:<file>:<lines>#<cfx-id>`. The validator
gates from the IaC spec apply here too:

- cited ids exist and excerpts match verbatim;
- factual consistency on named functions and routes;
- at least two `alternatives_considered` on high and critical findings.

## 7. Run-config (additive)

```yaml
code_flow:
  mode: auto            # auto | enabled | disabled
  traces: ["traces/staging-otlp.json"]
  sarif: ["scans/codeql.sarif"]
  contracts: ["api/openapi.yaml", "proto/**/*.proto", "schema/*.graphql"]
repos:                  # ADR-0019, extended
  - cbm_project: claims-api
    role: primary
    deploys_as: ["aws_ecs_service.claims_api"]   # optional join override (§9)
```

`auto` runs when Joern or OpenGrep is present and records a gap otherwise.
`enabled` fails without them.

## 8. Specialist integration

- **Lenses** receive `code-flow-packets/<goal>.md` alongside the IaC packets.
  - **Authenticity and Integrity** get `guarded`/`unguarded`/`unknown`
    verdicts.
  - **Confidentiality** gets PHI flows.
  - **Non-Repudiation** gets the verdicts for consequential write → audit
    emitter.
- **Unknown verdicts** become evidence gaps, and the resulting blocked
  findings name the unresolved edge or the unmodelled framework.
- **The attack-path analyzer** gains provenance `code_flow` and maps:
  - an unguarded entry exposed through the join (§9) → `network_reachable`
    plus `compromisable_via_finding`;
  - a guarded entry → `authn_required`.

## 9. Infrastructure-to-code join

Links compute resources in the IaC graph to services:

1. **Container images.** Image references in ECS task definitions, Kubernetes
   workloads and Helm values are matched against image names built in each
   repo (Dockerfiles and CI build-and-push steps).
2. **Functions.** Lambda `handler` plus `filename` or `s3_key` matched to repo
   paths.
3. **Operator override.** `repos[].deploys_as` lists IaC addresses or
   workload names explicitly.

Each join edge records its method and confidence. A compute node with no join
ends the attack path there and is recorded as `unknown`.

## 10. Evaluation

- **Corpora (development and held-out, ADR-0017 local benchmark):**
  - **Seeded fixtures per language.** Each has an entry point and these guard
    variants: inline guard, guard with ignored result, guard on one branch,
    middleware-only guard, decorator or annotation guard, unresolved dispatch.
  - **OWASP Benchmark (Java)** for flows.
  - **A polyglot microservice demo run with tracing,** for edge precision and
    recall. Candidates: Google Online Boutique, TrainTicket; the plan confirms
    licences.
- **Baseline.** The 1.7 CBM-only path, scored on the same labels.
- **Metrics:**
  - verdict precision and recall per language and framework;
  - edge precision and recall against traces;
  - unknown rate per language;
  - packet tokens.
- **Behaviour-preserving transformations** (GRAML tf1–tf7, adapted). These
  must not change verdicts:
  - renaming;
  - comment removal;
  - dead-code insertion;
  - function extraction;
  - void-call insertion;
  - moving an inline guard into middleware.

## 11. Safety and packaging

- **Tools through the IaC spec's `run_tool` gateway:**
  - Joern's frontends (`*2cpg`) and `joern --script` with bundled scripts
    only, under a JVM memory cap and a timeout, with Joern's residual files
    (such as `replay_pid*.log`) cleaned up after each run;
  - `opengrep scan` with bundled rules only and metrics off.

  No network.
- **Extra `[codeflow]`:** graphql-core.
- **External tools:** Joern and OpenGrep found on `PATH` with recorded minimum
  versions. `doctor` checks them.
- **Licences:** Joern is Apache-2.0. OpenGrep is LGPL-2.1, invoked as a
  separate binary.

## 12. Delivery

1. **CF1:** services, labels, frameworks (Java and Go first), Joern summaries,
   call-graph merge, graph cut, index and graph outputs, phase wiring.
2. **CF2:** Python and TypeScript frameworks, GraphQL, contracts, deployment
   config, traces, SARIF.
3. **CF3:** DFD rendering, packets, specialist integration, the
   infrastructure-to-code join, attack-path merge.
4. **CF4:** evaluation corpora, labels, transformation suite, baseline,
   tuning and freezing.

## 13. Open questions

- **Release target.** 2.1 keeps 2.0 bounded; pulling it into 2.0 delays GA by
  roughly the size of CF1–CF4.
- **Joern frontend maturity** for Go and TypeScript, and the resulting unknown
  rates. CF4 measures them before any verdict is used for severity.
- **Framework coverage** beyond the version 1 list.
- **JVM resource needs** on large monorepos.
