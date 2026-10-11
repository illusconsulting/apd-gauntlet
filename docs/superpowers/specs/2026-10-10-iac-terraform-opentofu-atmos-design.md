# IaC evaluation for Terraform, OpenTofu and Atmos — design

**Date:** 2026-10-10
**Status:** Proposed
**Release line:** `next` (2.0)
**Related:** ADR-0007 (code recon), ADR-0017 (local-only accuracy benchmark),
ADR-0019 (multi-repo recon), ADR-0023 (two-channel distribution), the 2.0
local-apps spec (`2026-10-10-local-apps-and-decision-models-design.md`, PR #29),
and GRAML (Li, Tian, Qu, Jiang, arXiv 2610.09605, 7 Oct 2026).

## 1. Problem

The gauntlet reads infrastructure-as-code by handing raw `*.tf` files to the
intake agent (`infrastructure.static.terraform` globs) and labelling Atmos
manifests `iac`. That produces wrong answers in four ways:

1. **Atmos values are not the values that deploy.** Stacks are built from
   imports, catalogs, `metadata.inherits`, mixins, overrides and Go templates.
   A reader of `stacks/catalog/vpc.yaml` sees the default, not what prod
   deploys.
2. **OpenTofu has different file rules.** When `main.tofu` and `main.tf` sit
   in the same directory, OpenTofu loads only `main.tofu`.
3. **Terraform override files change blocks.** `*_override.tf` merges into
   existing blocks; read separately, the original block looks insecure.
4. **No variable values.** Raw HCL has `var.x` where a scanner needs a value.

There is also no deterministic evidence: every IaC claim is an LLM reading of a
file, which costs tokens and varies between runs.

## 2. Goals and non-goals

**Goals**

- Evaluate Terraform, OpenTofu and Atmos (driving either engine).
- Scan every real component instance with the values it deploys with.
- Cite stack, component, resource address, file, line and value provenance.
- Run nothing from the client repository during analysis.
- Turn every unresolved value into an evidence gap, never a silent pass.
- Accept a client-supplied plan JSON as stronger evidence.
- Give specialists compact, typed evidence packets instead of raw files or
  graphs.
- Measure accuracy on held-out repositories, and prove findings survive
  changes that keep the infrastructure the same.

**Non-goals (version 1)**

- Running `plan`, `apply`, `validate` or `init` with providers. The gauntlet
  never holds cloud credentials.
- Live cloud inventory and drift detection.
- Terraform Stacks (`*.tfstack.hcl`, `*.tfdeploy.hcl`) and query files
  (`*.tfquery.hcl`). They are listed as not analysed.
- Atmos `helmfile` and `packer` components.
- Merging Terraform override files into their target blocks.
- Fetching Atmos-vendored components that are not committed.
- Rich graph semantics for providers other than AWS.
- Scanning script contents beyond ShellCheck (left to the code-flow work).

## 3. Decisions

| Question | Decision |
|---|---|
| Deployed-reality evidence | Static analysis, plus an optional client plan JSON. The gauntlet never runs plans. |
| Remote modules | Fetched with a module-only `tofu get`, behind the existing egress consent. |
| Architecture | Fixed pipeline in the Python engine (`apd-gauntlet iac`), no tokens. Agents read its outputs. |
| Atmos functions | Always `--process-functions=false`. Unresolved functions become `unknown` entries. |
| Scanners | Trivy (baseline) and Checkov (relationship checks), both on a normalised workspace. Either may be absent. |
| Terraform binary | Never required. OpenTofu (MPL) fetches modules for both engines. |
| Evidence to lenses | Compact per-goal packets selected by a GRAML-style relevance algorithm (§10). |
| Release line | `next`, as part of 2.0. |

## 4. Probe results that shape the design

Verified on 2026-10-10 against Atmos 1.231.0, Checkov 3.3.26 and Trivy 0.70.0:

| Probe | Result | Consequence |
|---|---|---|
| `!exec` in a stack, plain `atmos describe stacks` | The command ran | Functions are always off (§7.3) |
| `--process-functions=false` | Nothing ran; functions stayed literal strings | Literals become `unknown` entries and dependency edges |
| `!include /etc/hostname`, functions off | The host file's content appeared in the output | Sanitising pass on a scratch copy (§7.3) |
| `!include https://…`, functions off | Atmos tried to download it; the whole describe failed | Sanitising pass; egress blocked (§12) |
| Catalog default `false`, prod override `true` | Resolved correctly; provenance pointed at `orgs/prod.yaml:8` | Provenance feeds evidence and the override check |
| Checkov on a directory with only `main.tofu` | Zero findings | `.tofu` files are renamed `.tf` in the workspace (§7.4) |
| Trivy with `main.tf` and `main.tofu` | Reported `main.tf`, which OpenTofu never loads | Workspace applies OpenTofu precedence (§7.4) |
| Both scanners with `main_override.tf` fixing a block | Both reported the original block as insecure | Overridden blocks are marked uncertain (§7.4) |

`--use-mocks` resolves `!terraform.output` and `!terraform.state` from mocks
only when functions run. Atmos's `--skip` is a deny-list, so a function added in
a future Atmos version would execute. Version 1 therefore keeps functions off
and does not use mocks.

## 5. Architecture

A new `iac` phase runs after `setup` and before `intake`, in both the Claude
Code workflow (`.claude/workflows/apd-gauntlet.js`) and the 2.0 runner
(`runner/flow.py`). It is one CLI step, `apd-gauntlet iac run <run-dir>`, that
runs only when `infrastructure.mode: static`.

```text
inputs/ ──discover──► roots ──engine──► per-root engine
   │                     │
   │            Atmos roots: sanitize ─► describe (per stack) ─► instances
   │            plain roots: var files ────────────────────────► instances
   │                                                              │
   └──────────────────────────► workspace (normalised copy per instance)
                                         │
                                   fetch (consented, module-only)
                                         │
              ┌──────────────┬───────────┼──────────────┬──────────────┐
            scan          checks        plan          graph       inventory
              └──────────────┴───────────┼──────────────┴──────────────┘
                                         ▼
                      iac-evidence-index.yaml + iac-graph.yaml
                                         │
                                      context
                                         ▼
                      iac-summary.md + iac-packets/<goal>.md
```

All work happens under `<run>/.apd-state/iac/`. `inputs/` is never modified.

## 6. Run-config changes (additive)

```yaml
infrastructure:
  mode: static
  static:
    terraform:
      - "infra/live/**"                  # glob form, unchanged
      - root: "infra/live/prod"          # object form (new)
        var_files: ["infra/live/prod/prod.tfvars"]
        engine: opentofu                 # optional: opentofu | terraform
    atmos:                               # new
      - root: "platform"                 # directory holding atmos.yaml
        stacks: ["prod-*"]               # optional stack-name globs; default all
    k8s: []                              # existing keys unchanged
  modules:
    fetch: false                         # new; true needs recorded consent (§7.5)
  plans:                                 # new
    - path: "plans/prod-vpc.json"
      stack: "prod"                      # optional Atmos binding
      component: "vpc"                   # optional Atmos binding
      root: "infra/live/prod"            # optional plain-root binding
  require_tools: false                   # new; true fails the phase if a tool is missing
```

Every path is relative to `inputs/` and uses the existing traversal guard (no
leading `/`, no `..`). `terraform` entries accept a string or an object
(`oneOf`).

## 7. Units

Each unit lives in `tools/apd_gauntlet/iac/` with one job and a typed
interface. Only `tools.py` starts processes.

### 7.1 `tools.py` — the only process gateway

`run_tool(tool, args, *, cwd, network=False, timeout)` is the single place a
subprocess starts. It enforces:

- **Argument allowlist.** Accepted invocations:
  - `atmos describe stacks|component` (the gateway adds
    `--process-functions=false` and rejects any call without it);
  - `tofu get`;
  - `trivy config`;
  - `checkov -d|-f`;
  - `shellcheck -f json`.

  Anything else raises. A test asserts no other command can run.
- **Scrubbed environment.** It starts from an empty environment and sets:
  - `PATH` to the resolved tool directory;
  - `HOME` and `TMPDIR` to a fresh temp directory;
  - `LANG`;
  - `GIT_TERMINAL_PROMPT=0`;
  - `GIT_SSH_COMMAND=false`.

  No cloud, Terraform, OpenTofu, Atmos, GitHub or SSH variables pass through.
- **Egress.** With `network=False`, `HTTP_PROXY`, `HTTPS_PROXY` and
  `ALL_PROXY` point at a closed local port. Only the consented fetch gets the
  operator's real proxy settings.
- **Isolation.** Each call gets its own working directory, a timeout and an
  output-size cap. The directory is removed afterwards. Stderr from a failure
  is kept for the resulting `unknown` entry, following GRAML Appendix A on
  isolating batch Joern runs.

### 7.2 `discover.py` and `engine.py`

`discover` finds roots under the declared globs:

- An **Atmos root** is a directory holding `atmos.yaml`.
- A **plain root module** is a directory of `.tf`/`.tofu` (or `.tf.json`/
  `.tofu.json`) files that no other directory uses as a local module source.

`engine` picks the engine for each root, first match wins:

1. The run-config `engine` value.
2. Atmos `components.terraform.command`: its basename `tofu` means OpenTofu,
   `terraform` means Terraform. Any other value (a wrapper script) is recorded
   as an execution point, and the engine falls through to the next rule.
3. Any `.tofu` or `.tofu.json` file in the root or its local modules: OpenTofu.
4. Otherwise: Terraform.

The engine decides:

- file precedence;
- which engine-only constructs are recognised: OpenTofu `encryption`,
  provider `for_each`, and early-evaluated variables in `backend` and module
  `source`;
- which files are listed as not analysed.

### 7.3 `atmos.py` — sanitise, then resolve

**Sanitise.** Copy the Atmos root to `.apd-state/iac/atmos/<root-id>/`,
refusing symlinks that resolve outside the root. In the copy:

- Rewrite every `!include` (and `!include.raw`) that names a URL, a go-getter
  source or a path outside the root to a quoted literal
  (`"!include <target>"`). Record each as `unknown`.
- Remove remote `import:` entries and record each as `unknown`.
- Strip `templates.settings.gomplate.datasources` from the copied `atmos.yaml`
  and record it as `unknown`.
- Refuse a root whose configured `base_path` values escape it.

Rewrites are single-line substitutions, so line numbers in provenance still
match the original files. When a rewrite cannot be done on one line, that file
is excluded and its stacks are recorded as unresolved.

**Resolve.** For each stack, through `run_tool`:

```text
atmos describe stacks -s <stack> --format json --process-functions=false
```

If templates fail (for example a `{{ .vars.X }}` self-reference), retry with
`--process-templates=false`. Values that still contain template syntax become
`unknown`. If both attempts fail, record the stack as unresolved, citing
Atmos's error, and continue with the others.

For each concrete component (not `metadata.type: abstract`), record:

- stack, component, `metadata.component`;
- `vars`, `settings`, `env`, `backend`, `providers`, `settings.depends_on`,
  `hooks`;
- every remaining function literal: `!terraform.output`, `!terraform.state`,
  `!store`, `!env`, `!exec`, `!secret` and the rest.

Function literals become `unknown` entries. `!terraform.output` and
`!terraform.state` also become component-dependency edges, and `!exec` is
also an execution point.

**Provenance.** `describe component <c> -s <stack> --format yaml` (provenance
is on by default in 1.231.0) gives `file:line` for every value as YAML
comments; the unit parses those comments. The 1.231.0 probe showed provenance
in YAML output but not in JSON. Calls run with bounded concurrency.

### 7.4 `workspace.py` — one normalised copy per instance

For each instance, build `.apd-state/iac/ws/<instance-id>/`:

1. **Copy** the root module and its local modules (`./`, `../` sources inside
   `inputs/` only; escaping sources become `unknown`).
2. **OpenTofu precedence.** For each stem `X`, `X.tofu` excludes `X.tf`, and
   `X.tofu.json` excludes `X.tf.json`. Kept `.tofu` files are written as `.tf`
   (and `.tofu.json` as `.tf.json`) so every scanner reads them. Copies are
   byte-identical, so lines map straight back to the original paths.
3. **Override files** (`override.tf`, `*_override.tf` and the `.tofu`
   equivalents) are kept. Every block they touch is recorded as an `override`
   entry. Scanner results on those addresses get confidence
   `uncertain: override_unmerged`.
4. **Variables.**
   - Atmos instances: resolved `vars` minus unknowns, written to
     `apd.auto.tfvars.json`.
   - Plain roots: the declared `var_files` plus any `terraform.tfvars` and
     `*.auto.tfvars(.json)` already in the root.

   Unknown variables are omitted and listed on the instance. A scanner result
   on a block that references an unknown variable gets confidence
   `uncertain: unknown_var`.
5. **Not-analysed files.** `*.tfstack.hcl`, `*.tfdeploy.hcl` and
   `*.tfquery.hcl` are listed as not analysed. Test files (`*.tftest.hcl`,
   `*.tofutest.hcl`) are ignored.
6. **Deduplication.** Instances with the same module content hash, variables
   hash and engine share one workspace; results fan out to every instance.

### 7.5 `fetch.py` — consented, module-only

1. **List sources.** Parse every workspace's `module` blocks with python-hcl2
   and list the unique remote sources and versions. Early-evaluated sources
   that use `var.` are resolved from known variables, or recorded as
   `unknown`.
2. **Consent.** Fetching requires `infrastructure.modules.fetch: true` and a
   recorded consent in `.apd-state/consent.json`, the 2.0 egress-notice
   mechanism (local-apps spec §8.7).
   - **Where consent is given:** `apd-gauntlet iac consent <run-dir>` shows the
     exact source list and records consent with `--yes` or a typed
     confirmation. The TUI and web show the same list in a dialog.
   - **In the plugin workflow,** which cannot prompt, a missing consent stops
     the fetch with an instruction to run `iac consent` first. The rest of the
     phase continues, with remote modules recorded as unknown.
3. **Fetch.** Run `tofu get` in the workspace (`network=True`). Provider
   plugins are never downloaded or executed. The plan verifies that
   `tofu get` reads `apd.auto.tfvars.json` for early-evaluated sources; if it
   doesn't, those sources are recorded as `unknown`.
4. **Sources that need credentials** (private registries, SSH git, cloud
   buckets) fail fast and become `unknown` entries naming the source.

The implementation plan verifies that each scanner resolves the fetched
modules in `.terraform/modules`. When a scanner can't, module internals are
recorded as unknown for that scanner.

### 7.6 `scan.py`

Runs offline on each workspace through `run_tool`:

- **Trivy:** `trivy config` with bundled checks (`--skip-check-update`), JSON
  output and `--tf-vars` pointing at the generated variable file.
- **Checkov:** the Terraform framework, JSON output, `--var-file`, and no
  downloads (external modules or platform metadata).

Results are normalised to one shape: scanner, check id, title, scanner
severity, resource address, file, line range and category. A data table
(`data/iac/check-goal-map.yaml`) maps check categories to APD goals. Unmapped
checks go to the intake summary only.

Failed checks become `check` entries. Passed checks become `control` entries
only when their category is on `data/iac/control-allowlist.yaml`: encryption
at rest and in transit, logging, versioning, object lock, deletion protection,
IMDSv2 and similar. Capabilities then have evidence without the index
recording every passing check.

### 7.7 `checks.py` — APD checks the scanners lack

Deterministic Python checks, each producing `check` or `control` entries:

| Check | Fires when | Goals |
|---|---|---|
| `atmos.secure_default_override` | A stack changes an inherited security-relevant variable: a flag like `enable_*`, `*_enabled` or `encrypt*` turned off, a flag like `public*` or `allow_*` turned on, or any other change to a name on the security-variable list. Cites both provenance locations. | Varies by variable |
| `atmos.stage_drift` | The same component's security-relevant variables differ between prod and non-prod stacks (informational). Prod stacks match `prod_stack_patterns`, default `["prod*", "*-prod*"]`. | Varies |
| `source.unpinned` | Git module source without a commit or tag `ref`, registry module without `version`, or a `vendor.yaml` entry without a pinned version | Integrity |
| `state.protection` | S3 backend without `encrypt = true` or without locking (`use_lockfile` or `dynamodb_table`); an OpenTofu root without `encryption` is a gap signal for the Confidentiality lens to judge | Confidentiality, Integrity |
| `iam.github_oidc_trust_scope` | An IAM role trusts `token.actions.githubusercontent.com` with a missing `sub` condition, or one wildcarded beyond a single repository | Authenticity |

The security-variable name patterns and `prod_stack_patterns` live in
`data/iac/security-vars.yaml`.

### 7.8 `plan.py` — client plan JSON

- **Accepted format:** JSON from `terraform show -json` or `tofu show -json`
  (`format_version` 1.x). Binary planfiles are refused, because rendering them
  needs providers.
- **Binding** to an instance: the run-config binding first, then the Atmos
  stack name, then a unique match on resource addresses. An unbound plan is
  recorded and not used.
- **Scanning:** the same scanners run on the plan JSON. Results are reconciled
  with static results by (instance, address, check id):
  - found by both: `plan_confirmed`;
  - static only, but the plan shows the resource with different values:
    `plan_refuted`. Kept with the reason, but excluded from packets.
  - plan only: added with confidence `plan`.
- **Filling unknowns:** values from `planned_values`, except attributes marked
  sensitive (`after_sensitive`, `sensitive_values`).
- **Secret handling:** the plan stays in `inputs/` and is never copied into
  outputs. `prior_state` values are never read into outputs. Excerpts carry
  attribute paths and non-sensitive values only; sensitive ones render as
  `(sensitive)`.
- **Known gap:** plan JSON can lose cross-resource references under
  `for_each`/`count` (documented by Trivy), so the static scan always runs too.

### 7.9 `graph.py`

Parses each workspace (HCL and JSON syntax) with python-hcl2:

- **Nodes:**
  - resources, data sources and modules (expanded where the source is
    available);
  - Atmos components;
  - synthetic nodes `internet`, external accounts and federated identity
    providers.
- **Classes:** network, identity, data_store, compute, key, secret, logging,
  unknown.
- **Edges:**
  - references between blocks;
  - component `depends_on` and output references;
  - typed AWS edges from a mapping table: `ingress_from` (CIDR or security
    group, with ports), `exposed_to` (public IP or `publicly_accessible`),
    `routes_to` (route tables to IGW or NAT, listeners to targets), `in_subnet`,
    `trusts` (assume-role principals), `grants` (attached policies, at service
    and action granularity), `encrypts` (KMS key use), `logs_to`.
- **Multiplicity:** `count`/`for_each` are expanded when literal or resolvable
  from known variables. Otherwise one node is marked `multiplicity: unknown`.
- **Citations:** every node and edge carries a file, line range and verbatim
  excerpt.

Other providers get typed nodes with reference edges only.

### 7.10 `inventory.py` — execution points

Records an `execution_point` entry for every place the deploy runs code:

- **Atmos:**
  - `!exec`;
  - custom `commands` in `atmos.yaml`;
  - workflow steps of type shell;
  - `hooks`;
  - a non-standard `components.terraform.command`.
- **HCL:**
  - `provisioner "local-exec"` and `"remote-exec"`;
  - `data "external"`;
  - `null_resource` or `terraform_data` with provisioners.
- **CI:** steps in `.github/workflows/*.yml` that invoke `atmos`, `tofu` or
  `terraform`, or assume an AWS role, linked to `iam.github_oidc_trust_scope`
  by role name when possible.

Scripts these reference that exist in `inputs/` are run through ShellCheck
when it is installed.

### 7.11 `index.py` — evidence index writer

Writes `00-context/iac-evidence-index.yaml` and `00-context/iac-graph.yaml`
(§8). Ids are minted by the engine as `iev-` plus the first 8 hex characters of
a SHA-256 over the instance, address, kind and check id. No agent mints ids.
Output ordering is stable.

### 7.12 `context.py` — evidence packets (§10)

Writes `00-context/iac-summary.md` for intake and
`00-context/iac-packets/<goal>.md` for each APD goal.

## 8. Outputs

### 8.1 `iac-evidence-index.yaml`

Schema `iac-evidence-index.schema.json`, modelled on `code-evidence-index`:

```yaml
iac_evidence_index:
  generated_at: 2026-10-10T12:00:00Z
  tools: {atmos: 1.231.0, tofu: 1.10.6, trivy: 0.70.0, checkov: 3.3.26}
  context_params_version: 1
  roots:
    - {id: atmos:platform, kind: atmos, path: platform, engine: opentofu}
  instances:
    - id: prod/vpc
      root: atmos:platform
      stack: prod
      component: vpc
      module_path: platform/components/terraform/vpc
      engine: opentofu
      unknown_vars: [vpc_peer_id]
      fetch: fetched        # fetched | local | not_fetched | partial
  not_analysed: [platform/stacks/deploy.tfstack.hcl]
  entries:
    - id: iev-3f9a0c12
      kind: check           # check | control | execution_point | override | unknown
      instance: prod/vpc
      address: aws_security_group.ssh
      source: trivy         # trivy | checkov | apd | plan | shellcheck
      check: {id: AWS-0107, title: "…", scanner_severity: HIGH}
      file_path: platform/components/terraform/vpc/main.tf
      line_range: "L4-L9"
      excerpt: 'cidr_blocks = ["0.0.0.0/0"]'
      provenance:
        - {key: vars.allow_ssh_from, file: platform/stacks/orgs/prod.yaml, line: 12}
      apd_relevance: [confidentiality, integrity]
      confidence: static    # plan_confirmed | static | uncertain | plan | plan_refuted
      uncertain_reason: null
```

### 8.2 `iac-graph.yaml`

Schema `iac-graph.schema.json`. Nodes carry `{id, kind, class, type, instance,
address, file_path, line_range, excerpt, multiplicity}`. Edges carry `{id,
from, to, kind, attributes, file_path, line_range, excerpt, confidence}`.

### 8.3 Citation formats

```yaml
- artifact: iac-evidence-index.yaml
  locator: "iac:<instance>:<address>@<file_path>:<line_range>#<iev-id>"
  excerpt: "<verbatim from the entry>"
- artifact: iac-graph.yaml
  locator: "iacg:<node-or-edge-id>"
  excerpt: "<verbatim from the node or edge>"
```

The validator recognises both files as known artifact sources and
schema-validates them.

## 9. Specialist integration

- **Intake.** Stops reading raw `.tf` files for every root the `iac` phase
  resolved. It lists IaC files in the artifact inventory, reads
  `iac-summary.md`, and builds trust boundaries from graph exposure, routing
  and cross-account trust edges.
- **Fallback for unresolved roots.** A root the phase could not resolve (a
  missing tool, a sanitise refusal, or every stack failing) is listed in
  `iac-summary.md` as `unresolved-raw`. For that root only, intake keeps 1.7's
  raw reading of the declared files, so coverage never drops below 1.7.
  Findings resting only on raw-read evidence carry `confidence: low`.
- **Lenses.** Each lens dispatch names its goal's packet file. Lenses cite
  index or graph entries, never re-derive them, and never read `iac-graph.yaml`
  whole.
- **`apd-evidence-discipline` skill.** Gains an "IaC-evidence pointers"
  section mirroring the code-evidence section:
  - IaC evidence is declared intent, and counts like code evidence for
    capability maturity up to `implemented`;
  - `plan_confirmed` raises confidence, but not maturity: a plan shows what
    would deploy, not that the control was tested;
  - `unknown` entries become evidence gaps, and the resulting blocked findings
    name the plan, state or module that would resolve them.
- **Findings from IaC evidence must answer four things** (a GRAML insight,
  §11.3):
  - whether there is a problem;
  - where (address, file and lines, value provenance);
  - how severe (the APD rubric);
  - why: cause → relation path from the packet → consequence.
- **Competing explanations.** A finding that cites IaC evidence at high or
  critical severity records at least two `alternatives_considered` (new
  optional finding field):

  ```yaml
  alternatives_considered:
    - hypothesis: "SSH reachable from the internet"
      verdict: retained          # retained | pruned
      basis: "subnet routes to igw-1; no NACL deny"
      evidence_refs: ["iac:prod/vpc:aws_security_group.ssh@…#iev-3f9a0c12"]
    - hypothesis: "Exposure blocked upstream"
      verdict: pruned
      basis: "no load balancer or WAF in front; instance has a public IP"
      evidence_refs: ["iacg:e-0192"]
  ```

- **Validator gates** for findings that cite IaC evidence:
  1. every cited `iev`/`iacg` id exists and the excerpt matches it verbatim;
  2. **factual consistency:** every Terraform address in the title, summary or
     detail whose type prefix appears in the index must exist in the index or
     graph, so no invented resources;
  3. high or critical findings carry at least two `alternatives_considered`.

  Failures use the existing per-lens retry loop.
- **Attack-path analyzer.**
  - The asset graph gains provenance value `iac_evidence`.
  - IaC edges map to existing kinds where they fit: `exposed_to`/`ingress_from`
    from `internet` become `network_reachable`; `trusts` stays `trusts`;
    `grants` becomes `authz_grants`.
  - IaC edges with no matching kind stay in `iac-graph.yaml`.
  - Nodes cite `iacg:` ids, so the never-invent rule holds.
- **Report header.** Engines, tool versions, roots and instances analysed,
  fetch status, unknown counts and the not-analysed list.

## 10. Evidence packets (adapted from GRAML §II-B)

GRAML found that curated graph evidence beats both raw graph serialisations
(about 0.9–2.0 F1 points lower) and no graph evidence (up to about 13.7 points
lower). Packets apply its selection method to the infrastructure graph.

**Seeds.** Each `check` entry that failed and is not `plan_refuted`. The seed
nodes are its resources. Reliability weights: `plan_confirmed` and `plan` 1.0,
`static` 0.8, `uncertain` 0.5. Seed vector:
`z0_i = α_i / Σα` over seed nodes, 0 elsewhere.

**Weighted relations.** `A_ij = Σ_type w_type · R^type_ij`, summed when
several edge types join the same pair. Starting weights: exposure and routing
0.30, trust and grants 0.25, references and dependencies 0.20, containment
(`in_subnet`) 0.15, encrypts and logging 0.10.

**Hub damping.** `B = A + Aᵀ`, `Ã = Δ^-1/2 B Δ^-1/2`, with
`Δ_ii = Σ_j B_ij`. This stops VPC, account and provider nodes dominating.

**Scoring.** `z1 = Ã z0`, `z2 = Ã z1`, and
`Score(i) = 0.45·ẑ1_i + 0.25·ẑ2_i + 0.20·d_i − 0.10·ρ_i`, where:

- `ẑ` are min-max normalised;
- `d_i` is the number of distinct edge types joining `i` to already-selected
  nodes, divided by the number of types;
- `ρ_i` is the largest Jaccard overlap between `i`'s neighbourhood and an
  already-selected node's.

Selection is greedy up to K = 20 nodes, seeds included. Only edges between
selected nodes are kept.

**Counter-evidence.** Computed for each seed:

- route to `internet` present or absent;
- upstream controls (load balancer or CloudFront in front, WAF association,
  security groups that reference only other groups, NACL denies);
- overrides on the seed block;
- unknown values on attributes the check evaluated;
- the plan verdict.

**Rendering.** Templated sentences with citations, never YAML dumps. Example:
"`aws_security_group.ssh` allows 0.0.0.0/0 on port 22
[iev-3f9a0c12] → attached to `aws_instance.relay` [iacg:n-0041] → in
`subnet.public_a`, which routes to `igw-1` [iacg:e-0192]."

Each goal file lists packets in descending order of the seed's scanner
severity, then score. Past a size cap (default about 6,000 tokens, estimated
as characters ÷ 4, set in the context parameters), it summarises the overflow
as counts with index pointers, since long noisy context hurt GRAML's
baselines.

**Frozen parameters.** The starting values are GRAML's C/C++ values. They are
tuned on the development corpus only (§13.2), then frozen in
`data/iac/context-params.yaml` with a version recorded in each run.

## 11. What GRAML changed, and what it didn't

1. **Packets, not graphs** (§10). Source: GRAML Table X.
2. **Competing explanations** (§9). GRAML's multi-branch reasoning beat a
   single chain of thought in all 24 model-and-dataset comparisons (+3.14 F1
   on average, Table XI), and it keeps branches for traceability. Version 1
   asks for one structured turn rather than five sequential calls. The analogue
   of GRAML's verification against CVE text is the scanner rule's documented
   rationale and CWE, plus the plan when present.
3. **Complete findings.** GRAML's description and localization tasks gave the
   largest ablation gains (Table IX). The four-part requirement and the
   factual-consistency gate carry that over without fine-tuning.
4. **Frozen tunables and held-out evaluation** (§13.2), following GRAML's
   validation-then-freeze threshold protocol and its six held-out datasets.
5. **Behaviour-preserving changes as tests** (§13.3), adapting GRAML's
   transformations tf1–tf7.
6. **Tool isolation** (§7.1), from GRAML Appendix A.
7. **Decision models (optional).** When a decision model is configured, an
   advisory `decide iac-triage` task asks a `noul` question per high or
   critical IaC finding: "Given this packet, is the flagged condition
   reachable and effective?" Thresholds are calibrated on the development
   corpus and frozen, as GRAML selects τ* on validation data.

**Not adopted:**

- fine-tuning (APD has no training pipeline);
- checking against CVE text (misconfigurations have none);
- five sequential calls for every item (cost);
- GRAML's numeric weights as final values (tuned for C/C++).

GRAML's best detector reaches about 69% average F1. That supports keeping
deterministic scanners as the detectors and using models to adjudicate and
explain.

## 12. Safety model

- **Untrusted input.** Client repositories are untrusted. Nothing from them
  runs: Atmos functions stay off, no plan, apply, validate or provider init
  runs, and `run_tool` enforces the allowlist.
- **No secrets reach a tool.** The environment is scrubbed and `HOME` is
  empty. Plan JSON is treated as sensitive (§7.8).
- **Egress.** Blocked on a best-effort basis by pointing proxies at a closed
  port. That doesn't stop raw sockets or DNS, so the docs recommend running the
  gauntlet in a container with no network for hostile repositories. Only the
  consented module fetch gets network access.
- **Filesystem.** Escaping symlinks and paths are refused; outside includes
  are neutralised before Atmos sees them.
- **Content trust.** HCL comments and YAML values are artifact data under the
  existing input-trust rule. Text in them that looks like instructions is a
  finding for Integrity, not an instruction.

## 13. Failure handling and evaluation

### 13.1 Failure handling

Each unit degrades on its own, and the run never crashes on IaC input:

- **Missing tool:** that stage is skipped and recorded as an evidence gap.
  With `require_tools: true` the phase fails instead.
- **Failed stack, HCL parse error, scanner crash or timeout, unreachable
  source:** an `unknown` entry scoped to what it affects.
- **Schema validation:** both outputs are validated in the phase's own gate,
  the same as other phase outputs.

### 13.2 Accuracy evaluation (local benchmark, ADR-0017)

- **Corpus manifest.** `eval/iac/corpus.yaml` pins repositories by commit SHA
  in two disjoint sets:
  - **development:** synthetic fixtures plus intentionally vulnerable
    Terraform such as TerraGoat;
  - **held-out:** realistic Atmos and OpenTofu repositories by other authors.
    The plan confirms candidates and licences.
- **Labels.** Each repository has a hand-labelled file of expected results:
  check category, address and verdict.
- **Metrics.**
  - precision, recall and F1 per check category for the deterministic index;
  - the same metrics end to end for final findings;
  - unknown rate;
  - packet tokens per goal.
- **Tuning protocol.** Tunables are tuned on development only and frozen
  before held-out runs: edge weights, score coefficients, K, reliability
  weights, and decision thresholds. A tunable changed after a held-out run
  means a new held-out set.
- **Baseline.** Every metric is also computed for 1.7's raw-read path on the
  same corpus and labels, so the evaluation reports a before-and-after delta,
  not only an absolute score. A release that lowers recall of labelled issues
  against that baseline does not ship.

### 13.3 Behaviour-preserving transformation suite (CI, deterministic)

Each transformation is applied to the fixtures, and the normalised result set
`{(check id, address modulo rename map, verdict)}` must not change:

| Id | Transformation |
|---|---|
| T1 | Rename resource labels, rewriting references |
| T2 | Rename variables and locals |
| T3 | Move a resource into a local module (addresses compared modulo the module prefix) |
| T4 | Split one file into several, or merge several into one |
| T5 | Rename `.tf` to `.tofu` (OpenTofu engine) |
| T6 | Move a stack value into an Atmos catalog and inherit it |
| T7 | Add comments, unused variables and dead locals |
| T8 | Convert HCL to `.tf.json` |

Known non-invariances, such as a scanner lacking JSON support, must be listed
explicitly in the suite's allowlist with a reason. This suite would have
caught all three scanner and engine gaps in §4.

### 13.4 Other tests

- **Unit tests** per unit, with a fake `run_tool`, so no binaries are needed.
- **Integration tests** at pinned tool versions, marked `iac_tools` and
  skipped when absent. A CI job installs the pinned tools.
- **Security tests:**
  - an `!exec` canary file is never created;
  - outside-root include content never appears in any output;
  - a remote include never produces a network attempt beyond the closed proxy;
  - only allowlisted argument vectors reach `subprocess`;
  - plan-marked sensitive values never appear in outputs.
- **Parity:** `runner.flow.PHASES` and the workflow's `meta.phases` both
  include `iac`.
- **Manual acceptance:** one private Atmos repository run (not in CI).

## 14. Packaging, tools and versions

- **`[iac]` extra:** `python-hcl2`.
- **External tools,** found on `PATH` with minimum versions recorded in
  `data/iac/tools.yaml`:

  | Tool | Minimum | Required for |
  |---|---|---|
  | Atmos | 1.231.0 | Atmos roots |
  | OpenTofu | 1.8.0 (`.tofu` support) | Module fetch only |
  | Trivy | 0.70.0 | Baseline scanning |
  | Checkov | 3.3.26 | Relationship checks |
  | ShellCheck | 0.9 | Script checks (optional) |

  Checkov stays outside the package's dependencies because its dependency
  tree is heavy; `pipx install checkov` is the documented path.
- **The Terraform binary is never invoked.**
- **`doctor`** reports each tool's presence and version against its minimum.
  **`setup`** prints install commands per platform.
- **Records:**
  - ADR-0027 records the decisions in §3;
  - `docs/schema-evolution.md` gets a 2.0.0 entry: run-config
    `infrastructure` additions, `alternatives_considered` on findings,
    asset-graph provenance `iac_evidence`, and two new schemas;
  - all changes are additive and `framework_compat` is unaffected.

## 15. Delivery

Four implementation plans, each shippable alone:

1. **Resolution and workspaces:**
   - `run_tool`, `discover`, `engine`;
   - Atmos sanitise and resolve, with provenance;
   - `workspace` and `fetch` with consent;
   - the run-config schema;
   - an index containing instances, unknowns, overrides and Atmos/HCL
     execution points;
   - `iac run` and the `iac` phase in the workflow and runner.
2. **Scanning, checks and plan JSON:**
   - `scan`, `checks`, the check-to-goal map, `plan`;
   - the full index schema;
   - validator citation and factual-consistency gates;
   - the evidence-discipline skill and intake changes.
3. **Graph, packets and integration:**
   - `graph` with the AWS mapping, `context`, counter-evidence;
   - packet dispatch to lenses;
   - `alternatives_considered` with its validator rule;
   - the attack-path merge and the report header;
   - `doctor` and `setup` checks, docs and ADR-0027.
4. **Evaluation:**
   - the corpus manifest and labels;
   - the transformation suite;
   - the local benchmark runner;
   - tuning and freezing parameters;
   - optional `decide iac-triage`.

## 16. Risks and open questions

- **python-hcl2 fidelity** on complex expressions limits graph edges. Missed
  references become unknowns; the evaluation measures how often.
- **Checkov module resolution** from `.terraform/modules` is unverified (plan
  1 checks it).
- **Provenance cost** on large Atmos repositories, from one `describe
  component` per instance. Concurrency is bounded; if it proves too slow,
  provenance is fetched only for instances with findings or overrides.
- **Scanner rule churn** across versions. Versions are pinned and recorded,
  and the evaluation reruns on every upgrade.
- **Egress blocking is best-effort** (§12).
- **Graph semantics are AWS-only** in version 1.
- **Token cost of `alternatives_considered`** on high and critical IaC
  findings. The evaluation measures it.
- **Mocks.** If Atmos adds an allow-list mode for functions, a later version
  could resolve `!terraform.output` from mocks without running other
  functions.
- **Infrastructure-to-code join.** This spec builds the infrastructure graph
  but does not link a compute resource (ECS task, EC2 instance, Kubernetes
  workload, Lambda function) to the service code it runs. Until the code-flow
  layer defines that join (`2026-10-10-code-flow-layer-design.md`, §9),
  attack paths stop at the compute node.
