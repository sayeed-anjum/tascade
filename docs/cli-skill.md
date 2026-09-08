# Tascade CLI Skill

Print this file at any time with `tascade --skill`.

Tascade is the control plane for a fleet of coding agents: it holds the unit of
work, its intent, its dependencies, who is holding it, and its verifiable
completion. The `tascade` command is a thin client over the Tascade REST API —
it stores nothing locally and it is the same on every machine and every harness.
Everything you assert through it is visible to the human operator and to every
other agent.

## Configuration

Endpoint and API key resolve in this order, first match wins:

1. `--url` / `--api-key` flags
2. `TASCADE_URL` / `TASCADE_API_KEY` environment variables
3. `~/.config/tascade/config.toml`
4. Built-in default `http://127.0.0.1:8010`

```toml
# ~/.config/tascade/config.toml
url = "http://100.93.227.86:8010"
api_key = "tsk_..."
```

A `[default]` table with the same keys is also accepted.

## Output and exit codes

Every subcommand accepts `--json`. With it, the raw API response goes to stdout
and nothing else does, so it is safe to pipe into `jq`. Without it you get a
short human summary.

| Exit code | Meaning |
|---|---|
| `0` | Success. |
| `1` | The API returned an error, or it could not be reached. `error: <CODE>: <message>` on stderr. |
| `2` | Usage error: a missing argument or a malformed `--json`-typed value. |

## The worker loop

This is the sequence a worker agent actually follows. Ids below are placeholders.

```bash
# 1. Find work you are capable of.
tascade tasks ready --project-id "$PROJECT" --agent-id "$AGENT" \
  --capability python --json

# 2. Claim it. Keep the lease token: heartbeat needs it.
tascade tasks claim "$TASK" --project-id "$PROJECT" --agent-id "$AGENT" --json

# 3. Read the full spec and its dependency neighbourhood before writing code.
tascade tasks context "$TASK" --project-id "$PROJECT" --json

# 4. Start work. NOTE: this transition releases the lease, so heartbeat only
#    while the task is still in 'claimed'.
tascade tasks state "$TASK" --project-id "$PROJECT" \
  --new-state in_progress --actor-id "$AGENT" --reason "starting"

# 5. While still 'claimed', renew the lease before it expires (5 minutes).
tascade tasks heartbeat "$TASK" --project-id "$PROJECT" \
  --agent-id "$AGENT" --lease-token "$LEASE_TOKEN"

# 6. Commit your work, then record what you produced.
tascade tasks artifacts-create "$TASK" --project-id "$PROJECT" --agent-id "$AGENT" \
  --branch "$BRANCH" --commit-sha "$SHA" --check-status passed \
  --touched-file app/cli/main.py --touched-file tests/test_cli_e2e.py

# 7. Hand off. The reason is your handoff summary: what you built, what you
#    verified, what you left out and why.
tascade tasks state "$TASK" --project-id "$PROJECT" \
  --new-state implemented --actor-id "$AGENT" --reason "$HANDOFF_SUMMARY"
```

A worker may transition `claimed -> in_progress` and `in_progress -> implemented`
only. `integrated` belongs to a reviewer or the orchestrator, and self-review is
structurally blocked.

## Planning a project

```bash
PROJECT=$(tascade projects create --name "SpecTower" --json | jq -r .id)
PHASE=$(tascade phases create --project-id "$PROJECT" --name "Slice 1" --sequence 0 --json | jq -r .id)
MILESTONE=$(tascade milestones create --project-id "$PROJECT" --phase-id "$PHASE" \
  --name "Legible session" --sequence 0 --json | jq -r .id)

tascade tasks create --project-id "$PROJECT" --milestone-id "$MILESTONE" \
  --title "Tascade CLI over the REST API" --task-class backend \
  --work-spec '{"objective": "Thin client", "acceptance_criteria": ["parity test"]}' \
  --capability-tag python --json
```

Tasks need a milestone, and a milestone needs a phase, because that chain is
what generates the short id `P1.M1.T1`. Order work with dependency edges:

```bash
tascade deps create --project-id "$PROJECT" \
  --from-task-id "$UPSTREAM" --to-task-id "$DOWNSTREAM" --unlock-on implemented
```

`--unlock-on implemented` unblocks the downstream task as soon as the upstream
one is implemented; `integrated` waits for it to be merged.

## Error codes worth handling

| Code | What it means | What to do |
|---|---|---|
| `TASK_NOT_CLAIMABLE` | Someone else got there, or the task is not in `ready`. | Ask for ready tasks again. |
| `LEASE_EXISTS` | The task already has an active lease. | Do not force it; pick another task. |
| `LEASE_INVALID` | Your lease was released or expired. | Re-read the task state before doing anything else. |
| `PLAN_STALE` | The plan moved under you. | Re-read the task; your spec may have changed. |
| `INVALID_STATE_TRANSITION` | Not a legal edge in the state machine. | Check the current state with `tascade tasks get`. |
| `CYCLE_DETECTED` | The dependency edge would create a cycle. | Re-check the direction of the edge. |
| `SELF_REVIEW_NOT_ALLOWED` | You tried to review your own work. | Hand off to a reviewer. |
| `PROJECT_SCOPE_VIOLATION` | Your API key is not scoped to that project. | Use the right key. |

Read the server's own protocol guide at any time with `tascade instructions`.

## Command reference

Every command below also accepts `--json`, `--url`, and `--api-key`.

### `projects`

`tascade projects create` — Create a project.

- `--name` **(required)** — Project name.

Mirrors MCP `create_project`.

`tascade projects get <project_id>` — Get a project by id.


Mirrors MCP `get_project`.

`tascade projects list` — List all projects.

Mirrors MCP `list_projects`.

`tascade projects graph <project_id>` — Get the full project graph: phases, milestones, tasks, dependencies.

- `--include-completed` *(flag)* — Include completed tasks.

Mirrors MCP `get_project_graph`.


### `phases`

`tascade phases create` — Create a phase within a project.

- `--project-id` **(required)** — Project id.
- `--name` **(required)** — Phase name.
- `--sequence` — Ordering within the project; starts at 0.

Mirrors MCP `create_phase`.


### `milestones`

`tascade milestones create` — Create a milestone within a phase.

- `--project-id` **(required)** — Project id.
- `--phase-id` **(required)** — Parent phase id.
- `--name` **(required)** — Milestone name.
- `--sequence` — Ordering within the project; starts at 0.

Mirrors MCP `create_milestone`.


### `tasks`

`tascade tasks create` — Create a task within a milestone.

- `--project-id` **(required)** — Project id.
- `--milestone-id` **(required)** — Milestone id.
- `--title` **(required)** — Task title.
- `--task-class` **(required)** — architecture|db_schema|security|cross_cutting|review_gate|merge_gate|frontend|backend|crud|other
- `--work-spec` **(required)** — JSON: {"objective": "...", "acceptance_criteria": ["..."]}
- `--description` — Longer description.
- `--phase-id` — Phase id; inferred from the milestone.
- `--priority` — Lower runs first. Default 100.
- `--capability-tag` *(repeatable)* — Capability tag; repeatable.
- `--expected-touch` *(repeatable)* — Path the task expects to touch; repeatable.
- `--exclusive-path` *(repeatable)* — Path only this task may touch; repeatable.
- `--shared-path` *(repeatable)* — Path shared with other tasks; repeatable.

Mirrors MCP `create_task`.

`tascade tasks get <task_id>` — Get a task by id or short id.


Mirrors MCP `get_task`.

`tascade tasks list` — List tasks in a project, optionally filtered.

- `--project-id` **(required)** — Project id.
- `--state` — Filter by state.
- `--phase-id` — Filter by phase.
- `--capability` — Filter by capability tag.
- `--limit` — Page size. Default 50.
- `--offset` — Page offset.

Mirrors MCP `list_tasks`.

`tascade tasks ready` — List tasks ready for this agent to claim.

- `--project-id` **(required)** — Project id.
- `--agent-id` **(required)** — Your agent id.
- `--capability` *(repeatable)* — Capability you offer; repeatable.

Mirrors MCP `list_ready_tasks`.

`tascade tasks claim <task_id>` — Claim a ready task and take its lease.

- `--project-id` **(required)** — Project id.
- `--agent-id` **(required)** — Your agent id.
- `--claim-mode` — pull|directed. Default pull.
- `--seen-plan-version` — Plan version you last read; rejects a stale claim.

Mirrors MCP `claim_task`.

`tascade tasks heartbeat <task_id>` — Renew the lease on a claimed task.

- `--project-id` **(required)** — Project id.
- `--agent-id` **(required)** — Your agent id.
- `--lease-token` **(required)** — Lease token returned by claim.
- `--seen-plan-version` — Plan version you last read.

Mirrors MCP `heartbeat_task`.

`tascade tasks assign <task_id>` — Reserve a task for a named agent (push model).

- `--project-id` **(required)** — Project id.
- `--assignee-agent-id` **(required)** — Agent the task is reserved for.
- `--created-by` **(required)** — Who is assigning.
- `--ttl-seconds` — Reservation lifetime. Default 1800.

Mirrors MCP `assign_task`.

`tascade tasks state <task_id>` — Transition a task to a new state.

- `--project-id` **(required)** — Project id.
- `--new-state` **(required)** — Target state, for example in_progress or implemented.
- `--actor-id` **(required)** — Who is transitioning.
- `--reason` — Why. Carries the handoff summary.
- `--reviewed-by` — Reviewer id, for integration.
- `--review-evidence-ref` *(repeatable)* — Evidence reference; repeatable.
- `--force` *(flag)* — Bypass transition guards.

Mirrors MCP `transition_task_state`.

`tascade tasks context <task_id>` — Get a task with its dependency ancestors and dependents.

- `--project-id` **(required)** — Project id.
- `--ancestor-depth` — Traversal depth upstream. Default 1.
- `--dependent-depth` — Traversal depth downstream. Default 1.

Mirrors MCP `get_task_context`.

`tascade tasks artifacts-create <task_id>` — Record a branch, commit, and check status for a task.

- `--project-id` **(required)** — Project id.
- `--agent-id` **(required)** — Your agent id.
- `--branch` — Branch name.
- `--commit-sha` — Head commit SHA.
- `--check-suite-ref` — CI run reference.
- `--check-status` — pending|passed|failed.
- `--touched-file` *(repeatable)* — File the task touched; repeatable.

Mirrors MCP `create_task_artifact`.

`tascade tasks artifacts-list <task_id>` — List artifacts recorded for a task.

- `--project-id` **(required)** — Project id.

Mirrors MCP `list_task_artifacts`.

`tascade tasks integrations-enqueue <task_id>` — Enqueue an integration attempt for a task.

- `--project-id` **(required)** — Project id.
- `--base-sha` — Base commit SHA.
- `--head-sha` — Head commit SHA.
- `--diagnostics` — JSON diagnostics object.

Mirrors MCP `enqueue_integration_attempt`.

`tascade tasks integrations-list <task_id>` — List integration attempts for a task.

- `--project-id` **(required)** — Project id.

Mirrors MCP `list_integration_attempts`.

`tascade tasks integrations-result <attempt_id>` — Record the outcome of an integration attempt.

- `--project-id` **(required)** — Project id.
- `--result` **(required)** — success|conflict|failure.
- `--diagnostics` — JSON diagnostics object.

Mirrors MCP `update_integration_attempt_result`.


### `deps`

`tascade deps create` — Create a dependency edge between two tasks.

- `--project-id` **(required)** — Project id.
- `--from-task-id` **(required)** — The task that must finish first.
- `--to-task-id` **(required)** — The task that is unblocked.
- `--unlock-on` **(required)** — implemented|integrated.

Mirrors MCP `create_dependency`.


### `gates`

`tascade gates rule-create` — Create a gate rule.

- `--project-id` **(required)** — Project id.
- `--name` **(required)** — Rule name.
- `--scope` — JSON scope object.
- `--conditions` — JSON conditions object.
- `--required-evidence` — JSON evidence requirements.
- `--required-reviewer-role` *(repeatable)* — Reviewer role; repeatable.
- `--inactive` *(flag)* — Create the rule disabled.

Mirrors MCP `create_gate_rule`.

`tascade gates decision-create` — Record a gate decision.

- `--project-id` **(required)** — Project id.
- `--gate-rule-id` — Rule this decides.
- `--task-id` — Task the decision applies to.
- `--phase-id` — Phase the decision applies to.
- `--outcome` **(required)** — approved|approved_with_risk|rejected.
- `--decided-by` **(required)** — Reviewer id.
- `--rationale` — Why.
- `--evidence-ref` *(repeatable)* — Evidence reference; repeatable.

Mirrors MCP `create_gate_decision`.

`tascade gates decisions-list` — List gate decisions for a project.

- `--project-id` **(required)** — Project id.
- `--task-id` — Filter by task.
- `--phase-id` — Filter by phase.

Mirrors MCP `list_gate_decisions`.

`tascade gates evaluate` — Evaluate gate policies for a project.

- `--project-id` **(required)** — Project id.
- `--actor-id` **(required)** — Who is evaluating.
- `--policy` — JSON policy overrides.

Mirrors MCP `evaluate_gate_policies`.

`tascade gates checkpoints` — List gate checkpoints. REST only; no MCP equivalent.

- `--project-id` **(required)** — Project id.
- `--gate-type` — review_gate|merge_gate.
- `--phase-id` — Filter by phase.
- `--milestone-id` — Filter by milestone.
- `--include-completed` *(flag)* — Include completed checkpoints.
- `--limit` — Page size.
- `--offset` — Page offset.

REST only; no MCP equivalent.


### `plans`

`tascade plans changeset-create` — Create a plan changeset.

- `--project-id` **(required)** — Project id.
- `--base-plan-version` **(required)** — Version the changeset is based on.
- `--target-plan-version` **(required)** — Version the changeset produces.
- `--operations` **(required)** — JSON list: [{"op": "update_task", "task_id": "...", "payload": {...}}]
- `--created-by` **(required)** — Author id.

Mirrors MCP `create_plan_changeset`.

`tascade plans changeset-apply <changeset_id>` — Apply a plan changeset.

- `--allow-rebase` *(flag)* — Rebase automatically on a version conflict.

Mirrors MCP `apply_plan_changeset`.


### Top level

`tascade instructions` — Print the Tascade protocol guide from the server.

Mirrors MCP `get_instructions`.

