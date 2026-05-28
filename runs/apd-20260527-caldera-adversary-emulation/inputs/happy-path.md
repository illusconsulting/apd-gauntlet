# MITRE Caldera — Happy Path

The "happy path" is the workflow Caldera is designed to support
when used as intended by an authorised operator. This document
describes the legitimate engagement journey so reviewers can
distinguish expected behaviour from the
weapons-platform-misuse risks catalogued in `threat-model.md`.

## Prerequisites

- Caldera server is running on an operator-controlled host
  reachable on `:8888` (default). The deploy is on a
  network-segregated environment per the README's security
  recommendation.
- Operator has a credentials pair (`red/admin` for the
  `--insecure` lab case; otherwise the auto-generated
  credentials from `conf/local.yml`).
- Operator has explicit, documented authorisation (rules of
  engagement) for the target environment they intend to
  engage.
- For payload compilation: Go 1.24+ is installed on the
  server host; `builder` plugin is enabled.

## Conceptual model

Caldera supports:

- **Adversary emulation** — a red-team operator runs ATT&CK-
  aligned abilities against in-scope targets to model an
  adversary's tradecraft.
- **Detection-engineering validation** — a blue-team operator
  runs the same kinds of operations to fire sensors and
  confirm coverage.
- **Training** — the `training` plugin walks new operators
  through a self-paced CTF against the live server.

The happy path below covers the red-team automation flow,
which is the most common.

## Step-by-step

### 1. Operator log in

- **Endpoint:** `POST /enter` (legacy console) or via the Vue UI
  at `/`.
- **Request:** `username=red&password=admin` (or the
  operator's per-deploy credential).
- **Expected result:** session cookie set; redirected to the
  operator console. Session expires per
  `session_expiration_days` (default 7).
- **Alternative:** Pass `KEY: ADMIN123` (or the operator's
  per-deploy API key) on every API call to bypass the
  cookie flow entirely.

### 2. Configure an agent profile (sandcat)

- **Endpoint:** `GET /api/v2/agents/deploy_commands?platform=<linux|windows|darwin>`
- **Request:** bearer cookie or `KEY` header.
- **Expected result:** a one-liner shell command the operator
  copies and runs on the in-scope target host. The command
  downloads `sandcat` (compiled on demand by the `builder`
  plugin), runs it with operator-supplied callback URL and
  group.

### 3. Deploy the implant on the target

- **On the target:** operator pastes the deploy command into
  a shell on the target host (with whatever access the
  engagement scope grants them — pre-existing
  credentials, an exploit, or a phishing payload).
- **Expected result:** the implant runs, beacons home via
  `POST /beacon` (default HTTP contact), and registers
  itself in the Caldera server's agent registry. The
  operator UI's "agents" panel shows a new entry with the
  implant's `paw`, platform, hostname, and last-seen
  timestamp.

### 4. Select or author an adversary profile

- **Endpoint:** `GET /api/v2/adversaries` (list) or `POST
  /api/v2/adversaries` (create).
- **Request:** for a list, just auth. For create, an ordered
  list of ability IDs (each ATT&CK-mapped command sequence).
- **Expected result:** an adversary profile the operator can
  reference by ID in an operation. Stockpile ships a large
  collection (`plugins/stockpile/data/adversaries/`); emu
  ships CTID emulation plans; access ships initial-access
  profiles.

### 5. Choose a planner and a fact source

- **Planner:** `atomic` (sequential), `batch` (parallel),
  `look` (recon-first), or a plugin-contributed planner.
- **Fact source:** a starting fact set the planner uses to
  expand ability templates. May be empty (the planner
  harvests facts as the operation runs).

### 6. Launch an operation

- **Endpoint:** `POST /api/v2/operations`.
- **Request:**
  ```json
  {
    "name": "engagement-2026-q2-blueco",
    "adversary": {"adversary_id": "<adversary uuid>"},
    "planner": {"id": "atomic"},
    "source": {"id": "<source uuid>"},
    "auto_close": true,
    "group": "red"
  }
  ```
- **Expected result:** an Operation is created and starts
  running. The planner walks the adversary profile and queues
  Links (per-agent ability instances) for execution on each
  matching agent's next beacon.

### 7. Implant executes queued abilities

- **On the target:** the implant beacons (default sleep
  30-60s per `conf/agents.yml`), receives queued
  instructions in the beacon response, executes them in its
  local shell, and posts results in the next beacon.
- **On the server:** each Link is updated with the
  command's stdout / stderr / exit-code; the configured
  parsers run over the output and write Facts into the
  knowledge store; the planner uses the new Facts to expand
  the next round of ability templates (e.g. a Fact discovered
  as a domain name becomes the target of the next ability).

### 8. Review operation results

- **Endpoint:** `GET /api/v2/operations/{operation_id}`,
  `GET /api/v2/operations/{operation_id}/links`,
  `GET /api/v2/operations/{operation_id}/output`.
- **Expected result:** every executed Link with its result;
  every harvested Fact; the planner's decision trail. The
  `debrief` plugin can render this as a PDF report.

### 9. Close the operation

- **Endpoint:** `PATCH /api/v2/operations/{operation_id}`
  with `state: finished` (or rely on `auto_close`).
- **Expected result:** the operation transitions to
  `finished`; the implants remain deployed (unless the
  operator explicitly killed them via `DELETE
  /api/v2/agents/{paw}`).

### 10. Tear down the implants

- **Endpoint:** `DELETE /api/v2/agents/{paw}` (per-implant
  kill) or operator returns to the target host out-of-band
  to remove the implant binary.
- **Expected result:** the implant exits on receipt of the
  kill instruction at its next beacon.

### 11. Archive engagement evidence

- **Endpoint:** the `debrief` plugin's report-generation
  flow; manual `data/results/` archival.
- **Expected result:** an operator-controlled archive of the
  engagement's harvested data, Link records, and report
  artifacts. Retention is operator-driven (the platform has
  no built-in deletion policy).

## Normal operator usage past the happy path

Past step 11, the operator continues to:

- Run additional operations against the same or different
  adversary profiles.
- Pair red operations with blue-side detection-validation
  operations via the `gameboard` plugin.
- Iterate on adversary profiles based on observed defender
  coverage.
- Schedule recurring operations via the `croniter`-backed
  Schedule object.

At each step, the operator is expected to:

- Verify the target list against the documented ROE before
  launching an operation.
- Confirm that the implant is responding before queueing
  abilities (the untrusted-agent sniffer marks silent
  implants untrusted after `untrusted_timer` seconds).
- Avoid running operations against environments outside the
  engagement scope (the platform offers no enforcement here;
  see threat-model WP-2).

## Next steps for reviewers

Once the happy path is understood, reviewers proceed to:

- `threat-model.md` — STRIDE-organised view of where
  Caldera's design admits weapons-platform misuse.
- `invariants.md` — the architect's belief about what the
  platform holds true, against which reviewers can check
  enforcement.
- `prior-audit.md` — the carried-forward security posture
  observations.
