# IaC Plan 3 — Graph, Packets and Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cited infrastructure graph from the resolved workspaces, give each lens a compact per-goal evidence packet selected by a GRAML-style relevance algorithm, require competing explanations on serious IaC findings, merge IaC edges into the attack-path graph without inventing nodes, and surface the IaC run in the report header, `setup`, the TUI and the web UI.

**Architecture:** `iac/graph.py` parses each workspace with python-hcl2 and a data-driven AWS mapping into `00-context/iac-graph.yaml`. A domain-neutral selector, `apd_gauntlet.context.select.select_packet` (R2, reused by the code-flow layer), scores nodes around each failed check with hub damping, diversity and redundancy terms, and `iac/context.py` renders the selections, plus counter-evidence, as templated sentences into `00-context/iac-packets/<goal>.md`. The validator learns graph citations and the `alternatives_considered` rule; the attack-path builder maps IaC edges onto existing asset-graph kinds only where the intake inventory already names both ends.

**Tech Stack:** Python 3.10–3.12, python-hcl2 7.x, PyYAML, jsonschema; the existing esbuild report-template pipeline; LA3's Textual TUI and Starlette web UI; pytest.

**Spec:** `docs/superpowers/specs/2026-10-10-iac-terraform-opentofu-atmos-design.md` §7.9, §7.12, §8.2, §8.3, §9 (lens packets, competing explanations, validator gate 3, attack-path analyzer, report header), §10, §11, §14 (`setup`, records), §15 item 3, §16. Master plan R2 (`select_packet`, `EVIDENCE_INDEXES`), R7 (`iac-graph`, `finding.alternatives_considered`, asset-graph `iac_evidence`), R8. This is Plan 3 of 4; it consumes Plans 1 and 2, and Plan 4 consumes the Interfaces below.

**Amended 2026-10-17** per the amendments register (A13.12, A13.16, A13.18, A13.19, A13.25, A13.26, A13.28, A15.12, A15.21, A15.28).

## Global Constraints

- Graph nodes carry `{id, kind, class, type, instance, address, file_path, line_range, excerpt, multiplicity}`; edges carry `{id, from, to, kind, attributes, file_path, line_range, excerpt, confidence}` (spec §8.2).
- Classes: network, identity, data_store, compute, key, secret, logging, unknown. Typed AWS edges: `ingress_from`, `exposed_to`, `routes_to`, `in_subnet`, `trusts`, `grants`, `encrypts`, `logs_to`; plus references between blocks and component `depends_on`. Other providers get typed nodes with reference edges only (spec §7.9).
- `count`/`for_each` are expanded when literal or resolvable from known variables; otherwise one node is marked `multiplicity: unknown` (spec §7.9).
- Graph citation format: `artifact: iac-graph.yaml`, `locator: "iacg:<node-or-edge-id>"`, `excerpt: "<verbatim from the node or edge>"` (spec §8.3).
- `select_packet(graph: TypedGraph, seeds: dict[str, float], params: ContextParams) -> Packet`, with `ContextParams` loaded from `data/<domain>/context-params.yaml` (R2).
- Seeds: each `check` entry that failed and is not `plan_refuted`; reliability weights `plan_confirmed` and `plan` 1.0, `static` 0.8, `uncertain` 0.5; `z0_i = α_i / Σα` over seed nodes, 0 elsewhere (spec §10).
- Starting weights: exposure and routing 0.30, trust and grants 0.25, references and dependencies 0.20, containment (`in_subnet`) 0.15, encrypts and logging 0.10 (spec §10).
- `B = A + Aᵀ`, `Ã = Δ^-1/2 B Δ^-1/2`, `z1 = Ã z0`, `z2 = Ã z1`, `Score(i) = 0.45·ẑ1_i + 0.25·ẑ2_i + 0.20·d_i − 0.10·ρ_i`; greedy up to K = 20 nodes, seeds included; only edges between selected nodes are kept (spec §10).
- Each goal file lists packets in descending order of the seed's scanner severity, then score; past a size cap (default about 6,000 tokens, estimated as characters ÷ 4) it summarises the overflow as counts with index pointers (spec §10).
- Parameters start at GRAML's C/C++ values and live in `data/iac/context-params.yaml` with a version recorded in each run; Plan 4 tunes them, and WS2's `eval freeze` freezes them (its `TUNABLE_GLOBS` covers `data/*/context-params.yaml`) (spec §10, §13.2).
- Lenses cite index or graph entries, never re-derive them, and never read `iac-graph.yaml` whole (spec §9).
- A finding that cites IaC evidence at high or critical severity records at least two `alternatives_considered` (`hypothesis`, `verdict: retained | pruned`, `basis`, `evidence_refs`) (spec §9).
- IaC edges map to existing asset-graph kinds where they fit: `exposed_to`/`ingress_from` from `internet` become `network_reachable`; `trusts` stays `trusts`; `grants` becomes `authz_grants`; edges with no matching kind stay in `iac-graph.yaml`; nodes cite `iacg:` ids (spec §9).
- The synthetic `internet` node maps to an attacker position only through `data/iac/internet-aliases.yaml` (coordinator decision, 2026-10-11): `internet`, `public_internet`, `external_internet`, `unauthenticated_internet` and the bundled packs' surface-specific internet positions. Any other position gets no IaC internet edge, and `iac-summary.md` lists it.
- Suppressed entries (Plan 2 `suppressed_in_repo`) stay seeds like any other result; packets show the suppression as counter-evidence, never as a control.
- Attack paths stop at the compute node until the code-flow layer defines the infrastructure-to-code join (spec §16).
- A run without IaC produces byte-identical report data (`tests/integration/report/test_example_golden.py`).
- Tasks that change what agents read or what the validator accepts gate against the previous accepted state: the master plan Task 1 set run on the last accepted commit is the baseline, and `apd-gauntlet compare-runs <previous-accepted> <candidate> --gates eval/gates.yaml` must exit 0. Because `Workflow({name: "apd-gauntlet"})` runs the copy of the script registered when the Claude Code session started, every run that exercises a changed runner runs it by path, `Workflow({scriptPath: "<checkout>/.claude/workflows/apd-gauntlet.js", args: <the run's parsed .apd-run.yaml>})`, as `/apd-gauntlet:run` does, or starts a new session (register A15.12).
- M5 merge order (register A13.28): merge one at a time and rebuild the bundle after each: IAC3 Task 5 with CAT3 Task 6; WS6 Task 4, IAC3 Task 8 and CAT3 Task 14; IAC3 Task 6 with CAT3 Tasks 2–4; IAC3 Task 7, WS6 Task 7 and CAT3 Task 9.

## Review Focus

- **Hub nodes dominating a packet:** a VPC, account or provider joined to dozens of resources must not crowd out the exposure path. Pinned by Task 3 `test_hub_damping_selects_one_leaf`.
- **A goal with many seeds or a huge packet:** the goal file stays under the cap, keeps whole packets, and summarises the rest as counts with `iev` pointers. Pinned by Task 4 `test_size_cap_summarises_overflow`.
- **A serious IaC finding with a single story:** a high or critical lens finding citing IaC evidence with fewer than two `alternatives_considered`, or with an `evidence_refs` item that resolves to nothing, fails the tier gate; merged findings keep their sources' alternatives; deterministic attack-path findings are exempt. Pinned by Task 6 `test_high_iac_finding_needs_two_alternatives`, `test_alternative_refs_must_resolve`, `test_merged_finding_keeps_alternatives`, `test_apath_findings_exempt`.
- **The attack-path graph inventing infrastructure:** an IaC edge whose endpoints the intake inventory does not name by `iacg:` locator, or an internet edge in a run with no internet attacker position, must not reach `asset-graph.yaml`. Pinned by Task 7 `test_unmapped_iac_edge_not_merged`, `test_internet_edge_needs_internet_position`.
- **Runs without IaC:** report data, lens behaviour and the asset graph stay exactly as in 1.7. Pinned by Task 8 `test_meta_iac_absent_without_index` with `tests/integration/report/test_example_golden.py`, and Task 5 `test_lens_instruction_names_iac_packet`.

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `tools/apd_gauntlet/iac/graph.py` + `data/iac/aws-graph-map.yaml` + `data/iac/internet-aliases.yaml` | Node and edge extraction, AWS mapping, internet attacker-position aliases | Create |
| `tools/apd_gauntlet/data/schemas/iac-graph.schema.json` | Graph schema | Create |
| `tools/apd_gauntlet/context/__init__.py`, `context/select.py` | Domain-neutral packet selector | Create |
| `tools/apd_gauntlet/data/iac/context-params.yaml` | Versioned selector parameters | Create |
| `tools/apd_gauntlet/iac/context.py` | Seeds, counter-evidence, rendering, packet files | Create |
| `tools/apd_gauntlet/iac/pipeline.py`, `iac/summary.py`, `iac/index.py` | `graph` and `context` stages; summary exposure section; `context_params_version` | Modify |
| `tools/apd_gauntlet/validate.py`, `tools/apd_gauntlet/linters.py` | `iac-graph.yaml` in `EVIDENCE_INDEXES`; graph addresses; alternatives rule | Modify |
| `tools/apd_gauntlet/data/schemas/finding.schema.json:143-161` | `alternatives_considered` | Modify |
| `tools/apd_gauntlet/synthesis/apply.py:309-335` | Merged findings union alternatives | Modify |
| `tools/apd_gauntlet/attack_path/build.py:105-163`, `:235-307`, `:798-840` | IaC edge merge; public `resolved_attacker_positions` | Modify |
| `tools/apd_gauntlet/data/schemas/asset-graph.schema.json:31`, `:79` | Provenance `iac_evidence`; source `iac_graph` | Modify |
| `tools/apd_gauntlet/report/transform.py:156-219`, `report-template/screens/Overview.jsx:156-168`, `tools/apd_gauntlet/data/report-template/` | Report header | Modify |
| `.claude/workflows/apd-gauntlet.js` (`async function runTier(`, `async function repairTierGate(`), `tools/apd_gauntlet/runner/instructions.py` | Lens dispatch names the packet | Modify |
| `.claude/agents/apd-intake.md`, `.claude/skills/apd-evidence-discipline/SKILL.md`, `.claude/skills/apd-finding-schema/SKILL.md`, `.claude/skills/apd-attack-path-discipline/SKILL.md` | Agent and skill text | Modify |
| `tools/apd_gauntlet/app/setup.py`, `app/services.py`, `app/web/server.py`, `app/web/templates/fetch_consent.html`, `app/tui/{__init__,app,screens}.py` | Setup hints and fetch-consent dialogs | Modify/Create |
| `docs/iac-evaluation.md`, `docs/attack-path-analysis.md`, `docs/schema-evolution.md`, `CHANGELOG.md` | Docs | Modify |
| `tests/iac/…`, `tests/context/test_select.py`, `tests/test_validator_iac_graph.py`, `tests/test_finding_alternatives.py`, `tests/test_attack_path_iac.py`, `tests/unit/report/test_transform_meta.py`, `tests/app/…` | Tests | Create/Modify |

---

### Task 1: Infrastructure graph

**Files:**

- Create: `tools/apd_gauntlet/iac/graph.py`, `tools/apd_gauntlet/data/iac/aws-graph-map.yaml`, `tools/apd_gauntlet/data/iac/internet-aliases.yaml`, `tools/apd_gauntlet/data/schemas/iac-graph.schema.json`, `tests/fixtures/iac/aws-graph/main.tf`
- Modify: `tools/apd_gauntlet/iac/pipeline.py` (insert stage `graph` after `ci`)
- Test: `tests/iac/test_graph.py`, `tests/iac/test_graph_stage.py`

**Interfaces:**

- Consumes: Plan 1 `Workspace`, `Instance`, `Block`, `parse_file`, `attribute_line`, `excerpt_at`, `PipelineState`, `insert_stage`; Plan 2 `Instance.plan_variables`, entries' `confidence`
- Produces:
  - `NodeClass = Literal["network", "identity", "data_store", "compute", "key", "secret", "logging", "unknown"]`
  - `EdgeKind = Literal["references", "depends_on", "ingress_from", "exposed_to", "routes_to", "in_subnet", "trusts", "grants", "encrypts", "logs_to"]`
  - `@dataclass(frozen=True) class GraphNode: id: str; kind: Literal["resource", "data", "module", "component", "synthetic"]; cls: NodeClass; type: str; instance: str | None; address: str; file_path: str | None; line_range: str | None; excerpt: str; multiplicity: Literal["one", "expanded", "unknown"]` (serialised with key `class`)
  - `@dataclass(frozen=True) class GraphEdge: id: str; src: str; dst: str; kind: EdgeKind; attributes: dict[str, Any]; file_path: str | None; line_range: str | None; excerpt: str; confidence: Literal["static", "uncertain", "plan"]` (serialised with keys `from` and `to`)
  - `def node_id(instance: str | None, address: str) -> str` → `"n-" + sha256(f"{instance or ''}|{address}".encode()).hexdigest()[:8]`; `def edge_id(src: str, dst: str, kind: str, key: str) -> str` → `"e-" + sha256(f"{src}|{dst}|{kind}|{key}".encode()).hexdigest()[:8]`
  - `INTERNET = node_id(None, "internet")`; synthetic addresses `internet`, `account:<12-digit id>`, `idp:<host>`
  - `@dataclass class IacGraph: nodes: dict[str, GraphNode]; edges: dict[str, GraphEdge]; def add_node(self, n: GraphNode) -> None; def add_edge(self, e: GraphEdge) -> None; def by_address(self, instance: str | None, address: str) -> list[GraphNode]; def to_document(self) -> dict[str, Any]`
  - `@dataclass(frozen=True) class AwsMap: classes: dict[str, NodeClass]; rules: tuple[dict[str, Any], ...]`; `def load_aws_map() -> AwsMap`
  - `def load_internet_aliases() -> tuple[str, ...]` (the `aliases[].position` values of `data/iac/internet-aliases.yaml`, in file order); `def internet_position(positions: Sequence[str]) -> str | None` — the first alias, in file order, that appears in `positions`, else `None`
  - `def build_graph(instances: Sequence[Instance], workspaces: Mapping[str, Workspace], entries: Sequence[Mapping[str, Any]], aws: AwsMap) -> IacGraph`
  - `GRAPH_FILENAME = "iac-graph.yaml"`; `def write_graph(run_dir: Path, graph: IacGraph) -> Path` (schema-validated; root key `iac_graph` with `generated_at`, `nodes`, `edges`, sorted by id)
  - `def graph_stage(state: PipelineState, runner: ToolRunner) -> None`

Graph rules:

- Nodes: every `resource`, `data` and `module` block of each instance's root module; a `module` block whose source is a local directory or a fetched directory (`.terraform/modules/modules.json` `Dir`) is expanded by parsing that directory with `parse_file` and prefixing addresses with `module.<name>.`; one `component` node (address `component.<component>`) per Atmos instance.
- Multiplicity: `count` as an integer literal, or `for_each` as a literal list or map, or either as `${var.x}` with `x` in the instance's `vars` or `plan_variables` → nodes `addr[0]…` or `addr["key"]…` (`expanded`); anything else → one node with `multiplicity: unknown`. A `provider` block with `for_each` (an OpenTofu-only construct, spec §7.2) yields one synthetic `provider.<name>[key]` node per key under the same rule when the engine is opentofu, and none under terraform.
- Edges: a `references` edge for every `Block.refs` entry that resolves to a node in the same instance; `depends_on` edges from `Instance.dependencies` and `settings.depends_on`; typed edges from the rule table below. Edge `file_path`/`line_range`/`excerpt` come from `attribute_line` on the attribute that produced the edge (the block's first line when not found).
- Edge confidence: `uncertain` when the source block's address is overridden or its `var_refs` meet the instance's `unknown_vars`; `plan` when a value came from `plan_variables`; else `static`.

`aws-graph-map.yaml` rule table (edge direction is `from → to`):

| Kind | Resource types | From → to |
|---|---|---|
| `ingress_from` | `aws_security_group` `ingress` blocks; `aws_security_group_rule` with `type = "ingress"`; `aws_vpc_security_group_ingress_rule` | `internet` (a `0.0.0.0/0` or `::/0` CIDR) or the referenced source group → the target group; `attributes: {ports: "<from>-<to>", protocol, cidr}` |
| `exposed_to` | `aws_instance.associate_public_ip_address = true`; `aws_db_instance.publicly_accessible = true`; `aws_subnet.map_public_ip_on_launch = true`; every `aws_internet_gateway` | `internet` → the resource |
| `routes_to` | `aws_route` (`route_table_id` → `gateway_id`/`nat_gateway_id`); `aws_route_table` `route` blocks; `aws_route_table_association` (`subnet_id` → `route_table_id`); `aws_lb_listener` (`load_balancer_arn` → `default_action.target_group_arn`); `aws_lb_target_group_attachment` (`target_group_arn` → `target_id`); `aws_cloudfront_distribution` origins referencing an LB | first → second |
| `in_subnet` | any resource with `subnet_id`, `subnet_ids` or `subnets` references | resource → subnet |
| `trusts` | `aws_iam_role.assume_role_policy` (JSON literal or `aws_iam_policy_document` data block) principals | principal (`account:<id>`, `idp:<host>`, a role in the graph, or `service:<name>`) → role; `attributes: {condition_keys}` |
| `grants` | `aws_iam_role_policy_attachment` (`role` → `policy_arn`); `aws_iam_role_policy` and attached policy documents | role → policy or referenced resource; `attributes: {actions: ["s3:GetObject", …]}` at service and action granularity |
| `encrypts` | any resource with `kms_key_id`, `kms_master_key_id` or `kms_key_arn` (at any nesting depth of the block body) referencing a key | key → resource |
| `logs_to` | `aws_flow_log` (`vpc_id`/`subnet_id` → `log_destination`/`log_group_name`); `aws_s3_bucket_logging` (`bucket` → `target_bucket`); `aws_cloudtrail` (the trail → `s3_bucket_name`/`cloud_watch_logs_group_arn`) | first → second (the logged resource → its destination) |

`classes` maps each AWS resource type in the table, plus `aws_lambda_function`, `aws_ecs_service`, `aws_ecs_task_definition`, `aws_eks_cluster`, `aws_autoscaling_group`, `aws_launch_template` (compute), `aws_iam_user`, `aws_iam_policy`, `aws_iam_openid_connect_provider` (identity), `aws_s3_bucket`, `aws_rds_cluster`, `aws_dynamodb_table`, `aws_efs_file_system` (data_store), `aws_kms_key` (key), `aws_secretsmanager_secret`, `aws_ssm_parameter` (secret), `aws_cloudwatch_log_group` (logging); every other type is `unknown`.

`data/iac/internet-aliases.yaml` (`version: 1`) lists the attacker-position names that mean "an untrusted client on the public internet", most general first, because the `internet` node maps to the first one present in a run (pack paths are under `tools/apd_gauntlet/data/`):

| Position | Declared by |
|---|---|
| `internet` | generic |
| `public_internet` | generic |
| `external_internet` | `domains/pbm/domain.yaml` ("Untrusted external internet client") |
| `unauthenticated_internet` | `domains/api-security/domain.yaml` ("Untrusted external client with no credentials") |
| `unauthenticated_internet_against_member_portal` | `domains/pbm/domain.yaml` (the member-portal surface) |
| `unauthenticated_attacker_at_login_endpoint` | `domains/identity-security/domain.yaml` (the login surface) |

The last two name one surface of the internet, so they rank after the general names: in a pbm run that resolves both `external_internet` and the portal position, IaC internet edges start at `external_internet`. The minimal attack-path fixture's `external` is not an alias, because no bundled pack declares it and it could mean a partner network.

`tests/fixtures/iac/aws-graph/main.tf` declares, with known line numbers: `aws_vpc.main`; `aws_subnet.public_a` (`map_public_ip_on_launch = true`); `aws_internet_gateway.igw`; `aws_route_table.public` with a `route` to the gateway; `aws_route_table_association.a`; `aws_security_group.ssh` (port 22 from `0.0.0.0/0`); `aws_instance.relay` (`subnet_id`, `vpc_security_group_ids`, `associate_public_ip_address = true`); `aws_kms_key.data` and an `aws_s3_bucket_server_side_encryption_configuration` using it; `aws_iam_role.deploy` trusting `token.actions.githubusercontent.com` and account `111122223333`; `aws_iam_role_policy_attachment.deploy`; `aws_flow_log.vpc` to `aws_cloudwatch_log_group.flow`; `aws_instance.workers` with `count = 2`; `aws_instance.dyn` with `for_each = var.unknown_map`.

- [ ] **Step 1: Write the failing tests**

```python
def edges_by_kind(g, kind):
    return {(g.nodes[e.src].address, g.nodes[e.dst].address) for e in g.edges.values() if e.kind == kind}

def test_typed_edges(tmp_path):
    g = graph_for(tmp_path, "aws-graph")
    assert ("internet", "aws_security_group.ssh") in edges_by_kind(g, "ingress_from")
    assert {("internet", "aws_instance.relay"), ("internet", "aws_subnet.public_a"),
            ("internet", "aws_internet_gateway.igw")} <= edges_by_kind(g, "exposed_to")
    assert {("aws_subnet.public_a", "aws_route_table.public"),
            ("aws_route_table.public", "aws_internet_gateway.igw")} <= edges_by_kind(g, "routes_to")
    assert ("aws_instance.relay", "aws_subnet.public_a") in edges_by_kind(g, "in_subnet")
    assert {("idp:token.actions.githubusercontent.com", "aws_iam_role.deploy"),
            ("account:111122223333", "aws_iam_role.deploy")} <= edges_by_kind(g, "trusts")
    assert ("aws_kms_key.data", "aws_s3_bucket_server_side_encryption_configuration.data") in edges_by_kind(g, "encrypts")
    assert ("aws_vpc.main", "aws_cloudwatch_log_group.flow") in edges_by_kind(g, "logs_to")
    assert ("aws_instance.relay", "aws_security_group.ssh") in edges_by_kind(g, "references")

def test_ingress_attributes_and_citation(tmp_path):
    g = graph_for(tmp_path, "aws-graph")
    e = next(e for e in g.edges.values() if e.kind == "ingress_from")
    assert e.attributes == {"ports": "22-22", "protocol": "tcp", "cidr": "0.0.0.0/0"}
    assert e.file_path == "aws-graph/main.tf" and e.excerpt == 'cidr_blocks = ["0.0.0.0/0"]'

def test_multiplicity(tmp_path):
    g = graph_for(tmp_path, "aws-graph")
    workers = [n for n in g.nodes.values() if n.address.startswith("aws_instance.workers")]
    assert sorted(n.address for n in workers) == ["aws_instance.workers[0]", "aws_instance.workers[1]"]
    assert {n.multiplicity for n in workers} == {"expanded"}
    (dyn,) = [n for n in g.nodes.values() if n.address.startswith("aws_instance.dyn")]
    assert dyn.multiplicity == "unknown"

def test_classes(tmp_path):
    g = graph_for(tmp_path, "aws-graph")
    cls = {n.address: n.cls for n in g.nodes.values()}   # addresses are unique within one instance
    assert cls["aws_kms_key.data"] == "key" and cls["aws_iam_role.deploy"] == "identity" and cls["internet"] == "unknown"

def test_internet_aliases_cover_bundled_packs():
    aliases = set(load_internet_aliases())
    for pack in sorted((REPO / "tools/apd_gauntlet/data/domains").glob("*/domain.yaml")):
        for p in yaml.safe_load(pack.read_text())["attacker_positions"]:
            if p["description"].startswith("Untrusted external"):
                assert p["position"] in aliases, f"{pack.parent.name}: {p['position']}"

def test_internet_position_prefers_general_names():
    assert internet_position(["unauthenticated_internet_against_member_portal", "external_internet"]) == "external_internet"
    assert internet_position(["unauthenticated_attacker_at_login_endpoint"]) == "unauthenticated_attacker_at_login_endpoint"
    assert internet_position(["insider_with_member_service_role", "external"]) is None

def test_other_provider_reference_edges_only(tmp_path): ...   # google_compute_instance referencing google_compute_network → one references edge, class unknown
def test_local_module_expanded(tmp_path): ...                  # plain fixture → nodes module.sg and module.sg.aws_security_group.ssh
def test_override_makes_edge_uncertain(tmp_path): ...          # override fixture → ingress_from edge confidence "uncertain"
def test_ids_stable_across_runs(tmp_path): ...                 # build twice → identical to_document()

def test_graph_stage_writes_valid_file(tmp_path, fake_runner, tools_ok):
    run = run_with_fixture(tmp_path, "aws-graph", {"terraform": [{"root": "aws-graph"}]})
    run_iac(run, runner=fake_runner)
    doc = yaml.safe_load((run / "00-context/iac-graph.yaml").read_text())
    assert validate_against("iac-graph.schema.json", doc) == [] and doc["iac_graph"]["nodes"]
```

`graph_for(tmp_path, fixture)` builds the plain-root instance and workspace for a fixture and returns `build_graph(...)` with no index entries; `REPO = Path(__file__).resolve().parents[2]`; the pack guard passes today with exactly the four pack positions in the table, and fails when a new pack declares an "Untrusted external…" position the table lacks; `validate_against(schema_name, doc)` returns the error messages from validating `doc` with `build_registry()`.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/iac/test_graph.py tests/iac/test_graph_stage.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `graph.py`, the map, the schema and the stage**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/iac tests/test_meta_schemas.py tests/test_schema_vocab_centralized.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/iac tools/apd_gauntlet/data/iac/aws-graph-map.yaml tools/apd_gauntlet/data/iac/internet-aliases.yaml tools/apd_gauntlet/data/schemas/iac-graph.schema.json tests/fixtures/iac/aws-graph tests/iac
git commit -m "feat(iac): build a cited infrastructure graph with typed AWS edges"
```

### Task 2: Graph citations in the validator

**Files:**

- Modify: `tools/apd_gauntlet/validate.py` (`EVIDENCE_INDEXES` entry; known addresses), `tools/apd_gauntlet/linters.py` (none beyond inputs)
- Test: `tests/test_validator_iac_graph.py`

**Interfaces:**

- Consumes: Plan 2 `EVIDENCE_INDEXES`, `run_evidence_pass`, `check_iac_addresses`; Task 1 graph file
- Produces: `EVIDENCE_INDEXES["iac-graph.yaml"] = EvidenceIndexSpec("iac-graph.schema.json", r"^iacg:(?P<id>[ne]-[0-9a-f]{8})$", "id")`; `run_evidence_pass` adds every graph node `address` (with `[…]` suffixes stripped) to the known-address set used by `check_iac_addresses`.

- [ ] **Step 1: Write the failing tests**

```python
# run_with_graph(tmp_path) writes a minimal run with a context brief and Task 1's aws-graph graph file; returns (run, the relay node mapping)
def test_graph_citation_resolves(tmp_path):
    run, node = run_with_graph(tmp_path)
    add_finding(run, evidence=[{"artifact": "iac-graph.yaml", "locator": f"iacg:{node['id']}", "excerpt": node["excerpt"]}])
    assert run_evidence_pass(run, run).errors == []

def test_unknown_graph_id_rejected(tmp_path): ...       # iacg:n-00000000 → "cites unknown id n-00000000 in iac-graph.yaml"
def test_graph_excerpt_must_match(tmp_path): ...        # excerpt "x" → "verbatim"
def test_address_known_only_from_graph(tmp_path): ...   # detail names aws_instance.relay present only in the graph → no error
def test_graph_schema_validated_by_validate(tmp_path): ...  # malformed iac-graph.yaml → schema error on that file
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_validator_iac_graph.py -v`
Expected: FAIL

- [ ] **Step 3: Register the graph and extend the known-address set**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_validator_iac_graph.py tests/test_validator_iac_evidence.py tests/test_validator_evidence_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/validate.py tests/test_validator_iac_graph.py
git commit -m "feat(validate): resolve iac-graph citations"
```

### Task 3: Domain-neutral packet selector

**Files:**

- Create: `tools/apd_gauntlet/context/__init__.py`, `tools/apd_gauntlet/context/select.py`, `tools/apd_gauntlet/data/iac/context-params.yaml`
- Test: `tests/context/__init__.py`, `tests/context/test_select.py`

**Interfaces:**

- Produces (`apd_gauntlet.context.select`, R2):
  - `@dataclass(frozen=True) class TypedEdge: id: str; src: str; dst: str; type: str`
  - `@dataclass(frozen=True) class TypedGraph: nodes: tuple[str, ...]; edges: tuple[TypedEdge, ...]`
  - `@dataclass(frozen=True) class ContextParams: version: int; weights: dict[str, float]; type_groups: dict[str, str]; coef_z1: float; coef_z2: float; coef_diversity: float; coef_redundancy: float; k: int; reliability: dict[str, float]; token_cap: int; tuned_on: dict[str, str]`
  - `@dataclass(frozen=True) class Packet: nodes: tuple[str, ...]; edges: tuple[str, ...]; scores: dict[str, float]` — `nodes` in selection order, `edges` sorted ids with both ends selected
  - `def load_context_params(domain: str) -> ContextParams` — reads `data/<domain>/context-params.yaml` through `resources.data_dir()`
  - `def select_packet(graph: TypedGraph, seeds: dict[str, float], params: ContextParams) -> Packet` — raises `ValueError` when `seeds` is empty or names a node not in the graph

`data/iac/context-params.yaml`:

```yaml
version: 1
tuned_on: {}
weights: {exposure: 0.30, routing: 0.30, trust: 0.25, grants: 0.25, reference: 0.20, dependency: 0.20, containment: 0.15, encrypts: 0.10, logging: 0.10}
type_groups: {exposed_to: exposure, ingress_from: exposure, routes_to: routing, trusts: trust, grants: grants, references: reference, depends_on: dependency, in_subnet: containment, encrypts: encrypts, logs_to: logging}
score: {z1: 0.45, z2: 0.25, diversity: 0.20, redundancy: 0.10}
k: 20
reliability: {plan_confirmed: 1.0, plan: 1.0, static: 0.8, uncertain: 0.5}
token_cap: 6000
```

Selection algorithm (spec §10; the stop rule, candidate set and tie-break are this plan's choices and are what the tests pin):

```text
A[i,j]  = Σ over edges (i→j) of weights[type_groups[type]]
B       = A + Aᵀ ;  Δ[i] = Σ_j B[i,j] ;  Ã[i,j] = B[i,j] / sqrt(Δ[i]·Δ[j])   (0 when Δ is 0)
z0      = seeds normalised to sum 1 ;  z1 = Ã z0 ;  z2 = Ã z1 ;  ẑ = min-max over all nodes (0 when flat)
N(i)    = undirected neighbour set ;  T = distinct edge types in the graph
selected = seeds sorted by (-weight, id), first k
candidates = nodes not selected with z1 > 0 or z2 > 0
while len(selected) < k and candidates:
    for i in candidates (ascending id):
        d   = |edge types between i and any selected node| / |T|
        rho = max Jaccard(N(i), N(s)) over selected s
        score = coef_z1·ẑ1[i] + coef_z2·ẑ2[i] + coef_diversity·d − coef_redundancy·rho
    best = highest score, first in id order on ties
    stop when best score <= 0 ; else append best, remove it from candidates
```

- [ ] **Step 1: Write the failing tests**

```python
HUB_EDGES = [("internet", "sg", "ingress_from"), ("inst", "sg", "references"), ("sg", "vpc", "references"),
             ("inst", "subnet", "in_subnet"), ("subnet", "vpc", "in_subnet"), ("subnet", "rt", "routes_to"),
             ("rt", "igw", "routes_to"), ("internet", "igw", "exposed_to")] + \
            [(f"leaf{i:02d}", "vpc", "in_subnet") for i in range(30)]

def hub_graph(edges=HUB_EDGES):
    nodes = sorted({n for s, d, _ in edges for n in (s, d)})
    return TypedGraph(tuple(nodes), tuple(TypedEdge(f"e{k}", s, d, t) for k, (s, d, t) in enumerate(edges)))

def test_hub_damping_selects_one_leaf():
    p = select_packet(hub_graph(), {"sg": 0.8}, load_context_params("iac"))
    assert p.nodes == ("sg", "internet", "inst", "igw", "vpc", "subnet", "leaf00")

def test_k_caps_selection():
    params = dataclasses.replace(load_context_params("iac"), k=6)
    assert select_packet(hub_graph(), {"sg": 0.8}, params).nodes == ("sg", "internet", "inst", "igw", "vpc", "subnet")

def test_edges_only_between_selected():
    p = select_packet(hub_graph(), {"sg": 0.8}, dataclasses.replace(load_context_params("iac"), k=3))
    assert set(p.nodes) == {"sg", "internet", "inst"} and p.edges == ("e0", "e1")

def test_order_independent():
    shuffled = list(reversed(HUB_EDGES))
    assert select_packet(hub_graph(shuffled), {"sg": 0.8}, load_context_params("iac")).nodes == \
           select_packet(hub_graph(), {"sg": 0.8}, load_context_params("iac")).nodes

def test_seeds_first_by_weight(): ...      # seeds {"inst": 0.5, "sg": 1.0} → nodes start ("sg", "inst")
def test_isolated_seed(): ...              # graph with node "x" only → Packet(("x",), (), {})
def test_bad_seeds():
    with pytest.raises(ValueError):
        select_packet(hub_graph(), {}, load_context_params("iac"))

def test_params_values():
    p = load_context_params("iac")
    assert (p.version, p.k, p.token_cap, p.tuned_on) == (1, 20, 6000, {})
    assert p.weights["exposure"] == 0.30 and p.reliability["uncertain"] == 0.5
```

The expected tuples were computed with a reference implementation of the algorithm above on 2026-10-11; the hub `vpc` is selected once, and every further leaf scores `-0.048` because its neighbourhood equals `leaf00`'s.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/context/test_select.py -v`
Expected: FAIL (`ModuleNotFoundError: apd_gauntlet.context`)

- [ ] **Step 3: Implement `select.py` and the parameter file (pure Python, no NumPy)**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/context -v && mypy tools/`
Expected: PASS, mypy clean

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/context tools/apd_gauntlet/data/iac/context-params.yaml tests/context
git commit -m "feat(context): add the domain-neutral evidence packet selector"
```

### Task 4: IaC packets and counter-evidence

**Files:**

- Create: `tools/apd_gauntlet/iac/context.py`
- Modify: `tools/apd_gauntlet/iac/pipeline.py` (insert stage `context` after `graph`; record `context_params_version`), `tools/apd_gauntlet/iac/summary.py` ("Exposure and trust" section with its attacker-position lines), `tools/apd_gauntlet/attack_path/build.py:235-307` (public `resolved_attacker_positions`), `tests/iac/conftest.py` (`run_with_fixture` gains `checks=[(check_id, address)]`, registering a fake `trivy config` report with those failed checks, and `positions=None`, written as run-config `attacker_positions` when given)
- Test: `tests/iac/test_context.py`

**Interfaces:**

- Consumes: Task 1 `IacGraph`, `GraphNode`, `GraphEdge`, `INTERNET`, `internet_position`; Plan 2 entry fields `suppressed_in_repo`, `suppression`; Task 3 `select_packet`, `TypedGraph`, `TypedEdge`, `ContextParams`, `load_context_params`; Plan 2 `GoalMap`, `effective_severity`, `SEVERITY_ORDER`; Plan 1 `Workspace`; WS6 Task 12's reading contract (`packet_for(goal_text, ids)` splits a goal file at level-2 headings and returns the sections that cite a finding's ids)
- Produces:
  - `PACKETS_DIR = "iac-packets"`; `GOALS: tuple[str, ...]` (the nine `apd_goal` values)
  - `@dataclass(frozen=True) class Seed: entry_id: str; instance: str; address: str; check_id: str; title: str; severity: str; confidence: str; goals: tuple[str, ...]; nodes: tuple[str, ...]; var_refs: frozenset[str]`
  - `def seeds_from_index(entries: Sequence[Mapping[str, Any]], graph: IacGraph, workspaces: Mapping[str, Workspace], instances: Mapping[str, Instance], gm: GoalMap) -> tuple[list[Seed], list[str]]` — returns seeds and the ids of failed checks with no graph node
  - `def to_typed_graph(graph: IacGraph) -> TypedGraph`
  - `@dataclass(frozen=True) class CounterEvidence: internet_route: bool | None; upstream_controls: tuple[str, ...]; overrides: tuple[str, ...]; unknowns: tuple[str, ...]; plan_verdict: str; suppressed_in_repo: str | None` — the suppression excerpt when the seed entry carries `suppressed_in_repo: true`, else `None`
  - `def counter_evidence(seed: Seed, graph: IacGraph, entries: Sequence[Mapping[str, Any]]) -> CounterEvidence`
  - `def render_packet(seed: Seed, packet: Packet, graph: IacGraph, ce: CounterEvidence) -> str`
  - `def render_goal_file(goal: str, packets: Sequence[tuple[Seed, float, str]], params: ContextParams) -> tuple[str, str]` — the goal file text and the overflow file text (empty when nothing overflowed)
  - `def write_packets(run_dir: Path, graph: IacGraph, entries: Sequence[Mapping[str, Any]], seeds: Sequence[Seed], params: ContextParams) -> list[Path]` — always writes all nine goal files, plus `<goal>.overflow.md` beside any goal file that overflowed
  - `def context_stage(state: PipelineState, runner: ToolRunner) -> None`
  - `apd_gauntlet.attack_path.build.resolved_attacker_positions(run_dir: Path) -> list[str]` — the position names the attack-path graph will use, from `_load_yaml(run_dir / ".apd-run.yaml")`, `_load_domain` (`build.py:235`) and `_resolve_attacker_positions` (`build.py:284`), in their order, so the summary and the graph agree

Counter-evidence (spec §10):

- `internet_route`: a breadth-first walk from the seed's nodes over `exposed_to`, `ingress_from`, `routes_to`, `in_subnet` and `references` edges, ignoring direction, up to 4 hops, reaches `INTERNET` → `True`; the walk finishes without it → `False`; the instance has no network-class node → `None`.
- `upstream_controls`: ids of `aws_lb` or `aws_cloudfront_distribution` nodes with a `routes_to` path to a seed node; `aws_wafv2_web_acl_association` nodes referencing those; security groups on the seed whose every `ingress_from` source is another group; `aws_network_acl_rule` nodes with `rule_action = "deny"` on the seed's subnet.
- `overrides`: `override` entry ids for the seed's (instance, address).
- `unknowns`: `unknown` entry ids for the seed's instance whose key names a variable in `seed.var_refs`.
- `plan_verdict`: the seed entry's `confidence`.
- `suppressed_in_repo`: the seed entry's `suppression.excerpt` when `suppressed_in_repo` is true. It is the client's own risk acceptance, shown so a lens can say the client knew; it never counts as an upstream control.

Rendering (templated sentences, never YAML dumps):

```text
## <SEVERITY> · <check id> · `<address>` (<instance>) [<iev id>]
<check title>. Confidence: <confidence>.
Path: <sentence>; <sentence>; …
Counter-evidence: route to internet <present|absent|unknown>; upstream controls <ids or none>; overrides <ids or none>; unknown values <ids or none>; plan <verdict>; suppressed in repo <"excerpt" or no>.
```

One sentence per kept packet edge, in breadth-first order from the seed: ``` `<from address>` <verb> `<to address>` [iacg:<edge id>] ```, with verbs `ingress_from` "accepts traffic from" (the sentence reads to → from, with `attributes.ports` appended as "on port <ports>"), `exposed_to` "exposes", `routes_to` "routes to", `in_subnet` "is in", `references` "references", `depends_on` "depends on", `trusts` "is trusted by" (to → from), `grants` "grants", `encrypts` "encrypts", `logs_to` "logs to". A goal file starts with `# IaC evidence packets: <goal>` and lists packets as level-2 sections (WS6's `decide iac-triage` splits the file at `##` headings and selects the section citing a finding's `iev` id), by `SEVERITY_ORDER` of the seed, then score; packets are added whole while the file's `len(text) / 4` stays within `params.token_cap`; the rest goes under a closing `## More packets` section as one count line per severity, `"<n> more <SEVERITY> packets; ids in iac-packets/<goal>.overflow.md"`, and the overflow file lists one `<iev id> · <check id> · <address> (<instance>)` line per overflowed seed. Keeping the ids out of the goal file means WS6's section match never returns the overflow section as a seed's packet; an overflowed seed has no packet, which WS6 records as an `error` item. A goal with no seeds gets the single body line `No IaC check seeds this goal; see iac-summary.md for unknowns and execution points.`

Summary "Exposure and trust" section: one line per `exposed_to`/`ingress_from` edge from `INTERNET` and per `trusts` edge from an `account:` or `idp:` node, each with its `iacg:` id, so intake can build trust boundaries from them. It then lists the run's attacker positions (`resolved_attacker_positions`): `IaC internet edges start at: <position>` for `internet_position(...)`, or `IaC internet edges start at: none (no attacker position is an internet alias; see data/iac/internet-aliases.yaml)`, followed by `Attacker positions without an IaC internet edge: <names or none>`.

- [ ] **Step 1: Write the failing tests**

```python
# context_for(tmp_path, fixture, check=(id, address)) builds graph, index entries with that failed check and seeds; fake_seed(entry_id, severity) builds a Seed
def test_packet_sentence_matches_spec_shape(tmp_path):
    g, entries, seeds = context_for(tmp_path, "aws-graph", check=("AWS-0107", "aws_security_group.ssh"))
    text = render_packet(seeds[0], select_packet(to_typed_graph(g), {n: 0.8 for n in seeds[0].nodes},
                         load_context_params("iac")), g, counter_evidence(seeds[0], g, entries))
    assert "`aws_security_group.ssh` accepts traffic from `internet` on port 22-22 [iacg:e-" in text
    assert "route to internet present" in text and f"[{seeds[0].entry_id}]" in text

def test_refuted_and_passed_checks_are_not_seeds(tmp_path): ...  # plan_refuted check and a control entry → not in seeds
def test_seed_weight_from_reliability(tmp_path): ...             # uncertain seed → select_packet called with 0.5
def test_counter_evidence_upstream_lb(tmp_path): ...            # fixture with aws_lb routes_to the instance → its node id listed
def test_counter_evidence_overrides_and_unknowns(tmp_path): ... # override entry and unknown var on the seed → both ids listed

def test_counter_evidence_suppressed_in_repo(tmp_path):
    g, entries, seeds = context_for(tmp_path, "aws-graph", check=("AWS-0107", "aws_security_group.ssh"))
    seed_entry = next(e for e in entries if e["id"] == seeds[0].entry_id)
    seed_entry |= {"suppressed_in_repo": True, "suppression": {"tool": "trivy", "form": "inline", "origin": "repo",
                   "file_path": "aws-graph/main.tf", "line_range": "L20-L20", "excerpt": "#trivy:ignore:AWS-0107", "reason": None}}
    ce = counter_evidence(seeds[0], g, entries)
    assert ce.suppressed_in_repo == "#trivy:ignore:AWS-0107" and ce.upstream_controls == ()
    text = render_packet(seeds[0], select_packet(to_typed_graph(g), {n: 0.8 for n in seeds[0].nodes},
                         load_context_params("iac")), g, ce)
    assert 'suppressed in repo "#trivy:ignore:AWS-0107"' in text

def test_size_cap_summarises_overflow():
    params = dataclasses.replace(load_context_params("iac"), token_cap=200)
    packets = [(fake_seed(f"iev-{i:08x}", "HIGH"), 1.0 - i / 100, "x" * 1000) for i in range(5)]
    text, overflow = render_goal_file("confidentiality", packets, params)
    assert len(text) / 4 <= 200 and "5 more HIGH packets; ids in iac-packets/confidentiality.overflow.md" in text
    assert "iev-" not in text and overflow.splitlines()[0].startswith("iev-00000000 · ")

def test_packets_are_level2_sections(tmp_path, fake_runner, tools_ok):
    run = run_with_fixture(tmp_path, "aws-graph", {"terraform": [{"root": "aws-graph"}]}, checks=[("AWS-0107", "aws_security_group.ssh")])
    run_iac(run, runner=fake_runner)
    text = (run / "00-context/iac-packets/confidentiality.md").read_text()
    heads = [l for l in text.splitlines() if l.startswith("## ")]
    assert heads and all(re.search(r"\[iev-[0-9a-f]{8}\]$", h) for h in heads if h != "## More packets")

def test_order_by_severity_then_score(): ...   # CRITICAL low score precedes HIGH high score
def test_all_nine_goal_files_written(tmp_path, fake_runner, tools_ok): ...   # run_iac → nine files under 00-context/iac-packets/
def test_context_params_version_recorded(tmp_path, fake_runner, tools_ok): ...  # load_index(run)["context_params_version"] == 1
def test_summary_lists_exposure_and_trust(tmp_path, fake_runner, tools_ok): ... # "Exposure and trust" lists internet → aws_security_group.ssh with iacg id

def test_summary_lists_positions_without_internet_edge(tmp_path, fake_runner, tools_ok):
    run = run_with_fixture(tmp_path, "aws-graph", {"terraform": [{"root": "aws-graph"}]},
                           positions=["external_internet", "insider_with_member_service_role"])
    run_iac(run, runner=fake_runner)
    text = (run / "00-context/iac-summary.md").read_text()
    assert "IaC internet edges start at: external_internet" in text
    assert "Attacker positions without an IaC internet edge: insider_with_member_service_role" in text

def test_summary_names_no_internet_alias(tmp_path, fake_runner, tools_ok): ...   # positions ["external"] → "start at: none (…)"; "external" listed
```

Each test packet (1,000 characters) alone exceeds the 200-token cap, so the goal file holds only its title and the `## More packets` count line, and the overflow file lists the ids in order. `run_with_fixture(..., checks=[(check_id, address)])` makes the fake Trivy report those failed checks.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/iac/test_context.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `context.py`, the stage and the summary section**

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/iac tests/context -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/iac tools/apd_gauntlet/attack_path/build.py tests/iac/test_context.py tests/iac/conftest.py
git commit -m "feat(iac): render per-goal evidence packets with counter-evidence"
```

### Task 5: Packets to lenses, graph trust boundaries to intake

**Files:**

- Modify: `.claude/workflows/apd-gauntlet.js` (`runTier` lens instructions, first dispatch and retries: locate by `async function runTier(` and its lens-retry `for (let i = 0; i < lenses.length; i++)` loop, and the `-rerun` dispatch in `async function repairTierGate(`; register A15.28), `tools/apd_gauntlet/runner/instructions.py` (the `apd-<lens>` and `apd-<lens>:retry` instructions), `.claude/agents/apd-intake.md` (Step 4b), `.claude/skills/apd-evidence-discipline/SKILL.md` (IaC section), `tools/apd_gauntlet/data/claude/` (packaged copies, register A13.16)
- Test: `tests/test_workflow_apd_gauntlet.py`, `tests/runner/test_flow_parity.py`, `tests/test_intake_contract.py`, `tests/test_skill_apd_evidence_discipline_iac.py` (extend each)

Workflow edits follow register A15.21. Only the instruction strings change: the first dispatch and the `-rerun` dispatch stay `return llmStep('apd-' + lens, …)` inside their `parallel` thunks, and the retry stays `r = await llmStep('apd-' + lens, …)`. No `await`, helper or dispatch label changes, so `tests/test_workflow_runner_awaits.py` is untouched, and the substring `llmStep('apd-' + lens` that `test_lens_instruction_names_iac_packet` counts matches every awaited form.

**Interfaces:**

- Consumes: Task 4 packet files; LA2 `INSTRUCTIONS`, `instruction(key, **values)`
- Produces: `IAC_PACKET_SENTENCE = "If <run_dir>/00-context/iac-packets/<goal>.md exists, read it and cite its iac-evidence-index.yaml and iac-graph.yaml entries verbatim; never read iac-graph.yaml whole."` — appended to every lens dispatch in both channels (first dispatch, retries and WS1's re-run after a tier-gate repair), where `<goal>` is the lens name with `-` replaced by `_` (`non-repudiation` → `non_repudiation`). In the workflow it is built as `' If ' + runDir + '/00-context/iac-packets/' + lens.replace('-', '_') + '.md exists, read it and cite its iac-evidence-index.yaml and iac-graph.yaml entries verbatim; never read iac-graph.yaml whole.'`.

Intake Step 4b gains: build trust boundaries from the summary's "Exposure and trust" lines; an asset or identity taken from the graph records `provenance: {source: artifact, artifact: iac-graph.yaml, locator: "iacg:<node id>"}` so the attack-path builder (Task 7) can join it. The skill's IaC section gains the `iacg:` citation format and "read your goal's packet file; never read `iac-graph.yaml` whole".

- [ ] **Step 1: Write the failing tests**

```python
def test_lens_instruction_names_iac_packet() -> None:
    text = _text()
    dispatches = text.count("llmStep('apd-' + lens")          # first dispatch, retries, WS1's post-repair re-run
    assert dispatches >= 2
    assert text.count("/00-context/iac-packets/' + lens.replace('-', '_') + '.md exists") == dispatches
    assert "never read iac-graph.yaml whole" in text

# tests/runner/test_flow_parity.py
def test_runner_lens_instruction_matches_workflow():
    assert "never read iac-graph.yaml whole" in instruction("apd-integrity", run_dir="runs/r", tier_dir="10-trustworthiness", lens="integrity")
    assert "00-context/iac-packets/non_repudiation.md" in instruction("apd-non-repudiation", run_dir="runs/r",
                                                                         tier_dir="30-auditability", lens="non-repudiation")

def test_intake_records_iacg_locators():
    t = INTAKE.read_text()
    assert 'locator: "iacg:<node id>"' in t and "Exposure and trust" in t

def test_skill_names_graph_citation():
    t = SKILL.read_text()
    assert 'locator: "iacg:<node-or-edge-id>"' in t and "never read `iac-graph.yaml` whole" in t
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_workflow_apd_gauntlet.py tests/runner/test_flow_parity.py tests/test_intake_contract.py tests/test_skill_apd_evidence_discipline_iac.py -v`
Expected: FAIL on the new tests

- [ ] **Step 3: Edit the workflow, the runner instructions, the intake agent and the skill**

Then run `python -I -m apd_gauntlet.bundle --sync` to refresh the packaged copies (register A13.16).

- [ ] **Step 4: Run to verify pass and lint**

Run: `pytest tests/test_workflow_apd_gauntlet.py tests/runner tests/test_intake_contract.py tests/test_skill_apd_evidence_discipline_iac.py tests/test_lint_agents.py tests/test_lint_skills.py tests/test_bundle.py -v && markdownlint-cli2 ".claude/**/*.md"`
Expected: PASS, 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add .claude/workflows/apd-gauntlet.js tools/apd_gauntlet/runner/instructions.py .claude/agents/apd-intake.md .claude/skills/apd-evidence-discipline/SKILL.md tools/apd_gauntlet/data/claude tests
git commit -m "feat(workflow): point each lens at its IaC packet and intake at graph trust edges"
```

- [ ] **Step 6: Operator comparison**

Run the master plan Task 1 set on this branch, then `apd-gauntlet compare-runs <previous-accepted> <candidate> --gates eval/gates.yaml` for each run, where `<previous-accepted>` is the same run from the last accepted commit. Expected: exit 0 (no packet file exists for those runs, so the added sentence is inert).

### Task 6: `alternatives_considered`

**Files:**

- Modify: `tools/apd_gauntlet/data/schemas/finding.schema.json:143-161` (new optional property), `tools/apd_gauntlet/validate.py` (`run_evidence_pass` rule), `tools/apd_gauntlet/synthesis/apply.py:309-335` (merged findings), `.claude/skills/apd-finding-schema/SKILL.md`, `.claude/skills/apd-evidence-discipline/SKILL.md`, `docs/schema-evolution.md`, `tools/apd_gauntlet/data/claude/` (packaged copies, register A13.16)
- Create: `tests/fixtures/valid/finding-with-alternatives.yaml`
- Test: `tests/test_finding_alternatives.py`

**Interfaces:**

- Consumes: Plan 2 `run_evidence_pass` resolution helpers; Task 2 graph registry entry
- Produces:
  - Schema (R7): `alternatives_considered: {type: array, items: {type: object, additionalProperties: false, required: [hypothesis, verdict, basis, evidence_refs], properties: {hypothesis: {type: string, minLength: 5}, verdict: {enum: [retained, pruned]}, basis: {type: string, minLength: 5}, evidence_refs: {type: array, minItems: 1, items: {type: string, minLength: 1}}}}}`
  - `IAC_ARTIFACTS = frozenset({"iac-evidence-index.yaml", "iac-graph.yaml"})`; `LENS_AGENTS` = the nine lens `agent` values (the keys of `linters._GOAL_TIER`)
  - Rule in `run_evidence_pass`: a finding whose `agent` is in `LENS_AGENTS`, whose `severity` is `high` or `critical` and whose evidence cites an `IAC_ARTIFACTS` file must carry at least two `alternatives_considered` (`high or critical IaC finding needs at least two alternatives_considered`); every `evidence_refs` item must match an `iac:` or `iacg:` locator pattern and resolve to an existing id (`alternatives_considered[<i>] cites unknown <ref>`)
  - `apply.py`: a merged finding carries the union of its sources' `alternatives_considered`, sorted by source id and de-duplicated by `(hypothesis, verdict)`, when any source has them

- [ ] **Step 1: Write the failing tests**

```python
def test_schema_accepts_alternatives():
    assert schema_errors("finding", FIX / "valid/finding-with-alternatives.yaml") == []

def test_high_iac_finding_needs_two_alternatives(tmp_path):
    run, e = run_with_index(tmp_path)
    add_finding(run, severity="high", evidence=[cite(e)], alternatives=[alt("SSH reachable from the internet", "retained", [cite(e)["locator"]])])
    assert any("at least two alternatives_considered" in v.message for v in run_evidence_pass(run, run).errors)

def test_two_alternatives_pass(tmp_path): ...          # retained + pruned, both refs resolve → no errors
def test_medium_finding_needs_none(tmp_path): ...       # severity medium, no alternatives → no errors

def test_alternative_refs_must_resolve(tmp_path):
    run, e = run_with_index(tmp_path)
    add_finding(run, severity="critical", evidence=[cite(e)],
                alternatives=[alt("a hypothesis", "retained", [cite(e)["locator"]]), alt("b hypothesis", "pruned", ["iacg:e-00000000"])])
    assert any("alternatives_considered[1] cites unknown iacg:e-00000000" in v.message for v in run_evidence_pass(run, run).errors)

def test_apath_findings_exempt(tmp_path): ...           # agent attack_path_analyzer, high, cites iac-graph.yaml, no alternatives → no errors

def test_merged_finding_keeps_alternatives(tmp_path):
    result = apply_two_member_cluster(tmp_path, alternatives_a=[ALT_1], alternatives_b=[ALT_1, ALT_2])
    assert result.findings[0]["alternatives_considered"] == [ALT_1, ALT_2]
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_finding_alternatives.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the schema property, the rule, the merge and the skill text**

The finding-schema skill documents the field with the spec §9 example; the evidence-discipline skill says high and critical IaC findings record at least two competing explanations (one turn, not sequential calls) and that a pruned hypothesis still cites the evidence that pruned it. `docs/schema-evolution.md` gains a dated entry: `finding` gains optional `alternatives_considered`. Then run `python -I -m apd_gauntlet.bundle --sync` to refresh the packaged copies (register A13.16).

- [ ] **Step 4: Run to verify pass, including synthesis and examples**

Run: `pytest tests/test_finding_alternatives.py tests/test_finding_schema.py tests/unit/synthesis tests/test_synthesis_equivalence.py tests/test_validate_example_run.py tests/test_bundle.py -v && markdownlint-cli2 ".claude/**/*.md" docs/schema-evolution.md`
Expected: PASS, 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/data/schemas/finding.schema.json tools/apd_gauntlet/validate.py tools/apd_gauntlet/synthesis/apply.py .claude/skills tools/apd_gauntlet/data/claude docs/schema-evolution.md tests
git commit -m "feat(findings): require competing explanations on serious IaC findings"
```

- [ ] **Step 6: Operator comparison**

Run the master plan Task 1 set on this branch, then `apd-gauntlet compare-runs <previous-accepted> <candidate> --gates eval/gates.yaml` for each run, where `<previous-accepted>` is the same run from the last accepted commit. Expected: exit 0.

### Task 7: IaC edges in the attack-path graph

**Files:**

- Modify: `tools/apd_gauntlet/attack_path/build.py:105-163` (load and merge), new `_add_iac_edges` beside `_add_code_evidence_edges` (`:798-840`), `tools/apd_gauntlet/data/schemas/asset-graph.schema.json:31` (provenance source enum gains `iac_evidence`), `:79` (`sources_used` enum gains `iac_graph`), `.claude/skills/apd-attack-path-discipline/SKILL.md`, `docs/attack-path-analysis.md`, `tools/apd_gauntlet/data/claude/` (packaged copies, register A13.16)
- Test: `tests/test_attack_path_iac.py`

**Interfaces:**

- Consumes: Task 1 graph document and `internet_position`; the attack-path `Graph`, `Edge`, `stable_id`, and the `attacker_position` nodes `_add_attacker_positions` (`build.py:340-361`) emits
- Produces:
  - `IAC_EDGE_MAP = {"exposed_to": "network_reachable", "ingress_from": "network_reachable", "trusts": "trusts", "grants": "authz_grants"}`
  - `IAC_CONFIDENCE = {"plan": "high", "static": "medium", "uncertain": "low"}`
  - `IAC_TRAVERSAL_COST = {"network_reachable": 2, "trusts": 3, "authz_grants": 3}`
  - `def _iac_node_map(g: Graph, inventory: dict[str, Any], graph_doc: dict[str, Any]) -> dict[str, str]` — iac node id → asset-graph node id, from inventory assets and identities whose `provenance.artifact` is `iac-graph.yaml` or `00-context/iac-graph.yaml` and whose `locator` is `iacg:<id>`; the `internet` node maps to the `attacker_position` node named `internet_position([n.name for n in g.nodes_by_type("attacker_position")])`, and to nothing when that is `None`
  - `def _add_iac_edges(g: Graph, graph_doc: dict[str, Any], node_map: Mapping[str, str]) -> int` — for each iac edge whose kind is in `IAC_EDGE_MAP` (`exposed_to`/`ingress_from` only when `from` is `internet`) and whose both ends are mapped, adds an edge with `provenance {source: iac_evidence, artifact: 00-context/iac-graph.yaml, locator: iacg:<edge id>}`, id `stable_id("edge", from, to, kind, "iacg:<edge id>")`, skipping an id already present; returns the count
  - `build_graph` appends `"iac_graph"` to `sources_used` when at least one edge merged

- [ ] **Step 1: Write the failing tests**

```python
def test_internet_ingress_becomes_network_reachable(tmp_path):
    run = apath_run_with_iac(tmp_path, positions=["external_internet"], inventory_locators={"relay": "iacg:" + RELAY_NODE})
    res = build_graph(run)
    e = [e for e in res.graph._edges.values() if e.provenance.get("source") == "iac_evidence"]
    assert [(x.edge_type, x.traversal_cost, x.confidence) for x in e] == [("network_reachable", 2, "medium")]
    assert e[0].provenance["locator"].startswith("iacg:e-") and "iac_graph" in res.sources_used

def test_unmapped_iac_edge_not_merged(tmp_path):
    run = apath_run_with_iac(tmp_path, positions=["external_internet"], inventory_locators={})
    res = build_graph(run)
    assert not any(e.provenance.get("source") == "iac_evidence" for e in res.graph._edges.values())
    assert "iac_graph" not in res.sources_used

def test_internet_edge_needs_internet_position(tmp_path):
    run = apath_run_with_iac(tmp_path, positions=["insider_with_member_service_role", "external"],
                             inventory_locators={"relay": "iacg:" + RELAY_NODE})
    res = build_graph(run)
    assert not any(e.provenance.get("source") == "iac_evidence" for e in res.graph._edges.values())

@pytest.mark.parametrize("position", ["internet", "public_internet", "external_internet", "unauthenticated_internet",
                                      "unauthenticated_internet_against_member_portal", "unauthenticated_attacker_at_login_endpoint"])
def test_every_alias_starts_internet_edges(tmp_path, position):
    run = apath_run_with_iac(tmp_path, positions=[position], inventory_locators={"relay": "iacg:" + RELAY_NODE})
    (e,) = [e for e in build_graph(run).graph._edges.values() if e.provenance.get("source") == "iac_evidence"]
    assert e.from_node == stable_id("atk", position, "run_config")

def test_general_alias_preferred(tmp_path): ...   # positions [portal position, "external_internet"] → the edge starts at external_internet
def test_trusts_and_grants_mapped(tmp_path): ...                # inventory names role and bucket by iacg → trusts and authz_grants edges
def test_routes_to_not_merged(tmp_path): ...                     # routes_to edge with both ends mapped → stays out
def test_asset_graph_schema_accepts_iac_provenance(tmp_path): ...  # analyze-attack-paths on the run → validate asset-graph.yaml clean
def test_runs_without_iac_unchanged(): ...                       # tests/fixtures/attack_path/minimal-run → identical edge set and sources_used to today
```

`apath_run_with_iac` copies `tests/fixtures/attack_path/minimal-run`, sets run-config `attacker_positions` to `positions`, writes an `00-context/iac-graph.yaml` with the `aws-graph` fixture's `internet → aws_security_group.ssh` and `internet → aws_instance.relay` edges, and adds inventory assets for the named graph nodes with the given locators.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_attack_path_iac.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the merge, the schema enums, the skill note and the doc section**

The attack-path discipline skill gains: IaC-derived edges carry `provenance.source: iac_evidence` with an `iacg:` locator; cite that id; an IaC node the inventory does not name is never added; paths stop at the compute node (spec §16). Then run `python -I -m apd_gauntlet.bundle --sync` to refresh the packaged copies (register A13.16).

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_attack_path_iac.py tests/test_attack_path_build.py tests/test_attack_path_graph.py tests/test_cli_analyze_attack_paths.py tests/test_skill_apd_attack_path_discipline.py tests/test_bundle.py -v && markdownlint-cli2 ".claude/**/*.md" docs/attack-path-analysis.md`
Expected: PASS, 0 lint errors

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/attack_path/build.py tools/apd_gauntlet/data/schemas/asset-graph.schema.json .claude/skills/apd-attack-path-discipline/SKILL.md tools/apd_gauntlet/data/claude docs/attack-path-analysis.md tests/test_attack_path_iac.py
git commit -m "feat(attack-path): merge IaC exposure, trust and grant edges into the asset graph"
```

- [ ] **Step 6: Operator comparison**

Run the master plan Task 1 set on this branch, then `apd-gauntlet compare-runs <previous-accepted> <candidate> --gates eval/gates.yaml` for each run, where `<previous-accepted>` is the same run from the last accepted commit. Expected: exit 0.

### Task 8: Report header

**Files:**

- Modify: `tools/apd_gauntlet/report/transform.py:156-219` (`meta_block`), `report-template/screens/Overview.jsx:156-168` (run rail card), `tools/apd_gauntlet/data/report-template/` (rebuilt bundle and `.source-hash`)
- Test: `tests/unit/report/test_transform_meta.py` (extend), `tests/test_workflow_apd_gauntlet.py` (template text pin)

**Interfaces:**

- Consumes: Plan 1 and 2 index fields (`tools`, `roots`, `instances`, `entries`, `not_analysed`, `scanners`)
- Produces: `def iac_header(run_dir: pathlib.Path | None) -> dict[str, Any] | None` in `report/transform.py` → `None` without `00-context/iac-evidence-index.yaml`; else `{"engines": sorted engines, "tools": {name: version or None}, "roots": n, "roots_unresolved": n, "instances": n, "fetch": {"fetched": n, "local": n, "not_fetched": n, "partial": n}, "unknowns": n, "not_analysed": first 20 paths, "not_analysed_count": n}`. `meta_block` sets `meta["iac"]` only when `iac_header` returns a mapping, so runs without IaC keep identical data. `Overview.jsx` adds a rail card `Infrastructure` (engines, tool versions, roots and instances analysed, unresolved roots, fetch status, unknown count, not-analysed list) rendered only when `data.meta.iac` is present.

- [ ] **Step 1: Write the failing tests**

```python
def test_meta_iac_absent_without_index(example_run):
    assert "iac" not in meta_block(load_run(example_run), run_dir=example_run)

def test_meta_iac_header(tmp_path):
    run = run_dir_with_index(tmp_path)   # index: 1 atmos root unresolved-raw, 1 plain root, 2 instances, 3 unknowns
    h = meta_block(_meta_artifacts(), run_dir=run)["iac"]
    assert (h["roots"], h["roots_unresolved"], h["instances"], h["unknowns"]) == (2, 1, 2, 3)
    assert h["tools"]["atmos"] == "1.231.0" and h["fetch"]["not_fetched"] == 1

def test_overview_renders_iac_card() -> None:
    src = (REPO / "report-template" / "screens" / "Overview.jsx").read_text(encoding="utf-8")
    assert "data.meta.iac &&" in src and "Infrastructure" in src
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/unit/report/test_transform_meta.py tests/test_workflow_apd_gauntlet.py -v`
Expected: FAIL on the new tests

- [ ] **Step 3: Implement `iac_header`, the card, and rebuild the bundle**

Run: `python tools/build_report_template.py`

- [ ] **Step 4: Run to verify pass, freshness and golden**

Run: `pytest tests/unit/report tests/integration/report tests/test_workflow_apd_gauntlet.py -v && python tools/check_report_template_freshness.py`
Expected: PASS; the golden `claim-event-bus-golden-data.js` comparison unchanged; freshness OK

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/report/transform.py report-template/screens/Overview.jsx tools/apd_gauntlet/data/report-template tests
git commit -m "feat(report): show the IaC run in the report header"
```

### Task 9: `setup` hints and fetch-consent dialogs

**Files:**

- Modify: `tools/apd_gauntlet/app/setup.py` (`apply_setup` warnings), `tools/apd_gauntlet/app/services.py` (`start_run`), `tools/apd_gauntlet/app/web/server.py` (start route), `tools/apd_gauntlet/app/tui/{__init__,app,screens}.py` (LA3's TUI package: start action)
- Create: `tools/apd_gauntlet/app/web/templates/fetch_consent.html`
- Test: `tests/app/test_setup.py`, `tests/app/test_services_lifecycle.py`, `tests/app/web/test_routes.py`, `tests/app/test_tui.py` (extend each, following LA3's fixtures)

**Interfaces:**

- Consumes: Plan 1 `tool_status`, `install_hint`, `load_tool_specs`, `collect_fetch_sources`, `has_fetch_consent`, `record_fetch_consent`, `read_consent`; LA3 `SetupResult`, `start_run` (`tools/apd_gauntlet/app/services.py`), `ApdApp`, the `cfg_ws` fixture and LA3's TUI test form `async with ApdApp(cfg_ws).run_test(size=(80, 24)) as pilot`, and LA3's web test-client fixture (written `web` below; use the name `tests/app/web/test_routes.py` defines when LA3 lands)
- Produces:
  - `apply_setup` appends, for each IaC tool not found or below minimum, `"IaC: <tool> not found (<required_for>); install with: <install_hint>"` to `SetupResult.warnings` (spec §14: `setup` prints install commands per platform)
  - `class FetchConsentNeeded(Exception): sources: list[str]` in `app/services.py`
  - `start_run(cfg, run_id, *, consent: bool, budget_usd: float | None = None, restart_from: str | None = None, fetch_consent: bool | None = None, consent_method: Literal["tui", "web"] = "web") -> int` — when the run sets `infrastructure.mode: static` and `modules.fetch: true`, remote sources exist and `has_fetch_consent` is false: `None` raises `FetchConsentNeeded(sources)`; `True` records consent with `consent_method`; `False` starts without fetching (the phase records remote modules as unknown). Granting decision-model `consent` never touches the fetch subject.
  - Web: a start request that raises `FetchConsentNeeded` renders `fetch_consent.html` (the source list, "Allow download" and "Skip fetch" buttons, CSRF field); the POST back calls `start_run(..., fetch_consent=<allow>, consent_method="web")`. TUI: a modal listing the sources with Allow and Skip, calling `start_run(..., consent_method="tui")`.

- [ ] **Step 1: Write the failing tests**

```python
def test_setup_warns_with_install_hint(tmp_path, monkeypatch, cfg_path):
    monkeypatch.setattr(setup_mod, "tool_status", lambda name, **k: ToolStatus(name, False, None, "1.231.0", False, "not found"))
    res = asyncio.run(apply_setup(SetupAnswers(tmp_path / "ws", "anthropic", None, "none", None, None, None, ["pbm"]), test_decision=False))
    assert any(w.startswith("IaC: atmos not found") and "install with:" in w for w in res.warnings)

def test_start_requires_fetch_decision(cfg_ws, run_with_remote_modules, monkeypatch):
    monkeypatch.setattr(services, "collect_fetch_sources", lambda run_dir, **k: ["terraform-aws-modules/vpc/aws@5.1.0"])
    with pytest.raises(FetchConsentNeeded) as e:
        start_run(cfg_ws, run_with_remote_modules.name, consent=False)
    assert e.value.sources == ["terraform-aws-modules/vpc/aws@5.1.0"]

def test_start_records_fetch_consent_only(cfg_ws, run_with_remote_modules, monkeypatch, popen_stub): ...  # fetch_consent=True → iac_module_fetch recorded with method "web"; no decision_model subject
def test_start_skip_fetch_starts(cfg_ws, run_with_remote_modules, monkeypatch, popen_stub): ...       # fetch_consent=False → PID returned, no consent written
def test_web_shows_fetch_dialog(web, run_with_remote_modules, monkeypatch): ...                      # POST start → 200 page listing the source and both buttons

def test_tui_fetch_modal(cfg_ws, run_with_remote_modules, monkeypatch, popen_stub):
    monkeypatch.setattr(services, "collect_fetch_sources", lambda run_dir, **k: ["terraform-aws-modules/vpc/aws@5.1.0"])

    async def scenario() -> None:
        async with ApdApp(cfg_ws).run_test(size=(80, 24)) as pilot:
            await start_from_tui(pilot, run_with_remote_modules.name)   # LA3's run-start interaction
            modal = pilot.app.screen
            assert isinstance(modal, FetchConsentModal) and "terraform-aws-modules/vpc/aws@5.1.0" in modal.sources_text
            await pilot.click("#fetch-allow")

    asyncio.run(scenario())
    assert read_consent(run_with_remote_modules)["iac_module_fetch"]["method"] == "tui"
```

`run_with_remote_modules` (new, `tests/app/conftest.py`) creates a run in `cfg_ws`'s workspace whose `inputs/` is Plan 1's `plain-remote` fixture and whose run-config sets `infrastructure: {mode: static, static: {terraform: ["infra/**"]}, modules: {fetch: true}}`. `popen_stub` (new) replaces the process start inside LA3's `start_run` with a stub returning PID 4242. `start_from_tui(pilot, run_id)` (new) drives LA3's start action for `run_id` with the keys LA3's own start test uses. `FetchConsentModal` (new, in the `app/tui/` package) shows the sources in a `Static` exposed as `sources_text`, with buttons `#fetch-allow` and `#fetch-skip`.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/app -v`
Expected: FAIL on the new tests

- [ ] **Step 3: Implement the setup warnings, `start_run`, the web route and template, and the TUI modal**

Imports from `apd_gauntlet.iac` stay inside the functions that use them, so `app.services` never imports the IaC package at module load.

`apd-gauntlet run --yes` never grants `iac_module_fetch`; Task 10's "Consent in the TUI and web" section documents it (register A13.25).

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/app tests/iac -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/apd_gauntlet/app tests/app
git commit -m "feat(app): IaC tool hints in setup and fetch-consent dialogs in the TUI and web"
```

### Task 10: Docs and manual acceptance

**Files:**

- Modify: `docs/iac-evaluation.md`, `docs/schema-evolution.md`, `CHANGELOG.md`, `docs/adrs/0027-iac-evaluation-pipeline.md` (Consequences: the packet selector is shared with the code-flow layer; the stop rule added in Task 3)

- [ ] **Step 1: Write the docs**

`docs/iac-evaluation.md` gains "Infrastructure graph" (classes, edge kinds, AWS-only semantics, multiplicity), "Evidence packets" (seeds, weights, the size cap, how to read a packet, counter-evidence including "suppressed in repo"), "Competing explanations", "Attack paths" (the edge mapping, the inventory join, and `data/iac/internet-aliases.yaml` with how to add a pack's internet position; the `agentic-ai`, `mobile-applications` and `security-tooling` packs declare no internet attacker position, so IaC internet edges never start in those runs, register A13.26), "Report header" and "Consent in the TUI and web" (`apd-gauntlet run --yes` never grants `iac_module_fetch`, register A13.25). `docs/schema-evolution.md` gains dated entries for the new `iac-graph` schema and the asset-graph provenance value `iac_evidence` and source `iac_graph` (the `alternatives_considered` entry landed in Task 6). `CHANGELOG.md` gains Added bullets for the graph, packets, alternatives, the attack-path merge and the report header.

- [ ] **Step 2: Lint and run the full suite**

Run: `markdownlint-cli2 docs/iac-evaluation.md docs/schema-evolution.md docs/adrs/0027-iac-evaluation-pipeline.md CHANGELOG.md && pytest -q && ruff check tools/ tests/ && mypy tools/`
Expected: 0 lint errors; PASS; ruff and mypy clean

- [ ] **Step 3: Commit**

```bash
git add docs CHANGELOG.md
git commit -m "docs(iac): document the graph, packets and integration"
```

- [ ] **Step 4: Manual acceptance (operator, not in CI)**

Run the gauntlet on one private Atmos repository with `infrastructure.mode: static`, an `atmos` root and the tools installed at their minimum versions. Expected: the run completes; `00-context/iac-evidence-index.yaml`, `iac-graph.yaml` and the nine packet files exist and validate; `apd-gauntlet validate <run-dir>` is clean; no file named in a `!exec` literal exists anywhere; the report header lists the roots, instances and tool versions (master plan Task 7 Step 1).
