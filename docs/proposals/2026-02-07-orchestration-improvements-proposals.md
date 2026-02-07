# Orchestration Improvements Proposals (Backlog)

Date: 2026-02-07
Status: Proposal Backlog (for planning phase)

This document captures candidate improvements for future planning. These are not committed as active execution scope for the current plan.

## Proposal 1: First-class Parent/Child Task Linkage

Add explicit parent-child linkage in the task data model and expose it in MCP/API, so umbrella and child task relationships are queryable without relying on free-form text.

Expected value:
- Better auditability and automation for umbrella rollups.
- Reduced ambiguity in lane-to-umbrella mapping.

## Proposal 2: "Create Child Tasks from Umbrella" Helper

Add an MCP/API helper to scaffold child tasks from an umbrella task with optional lane templates.

Expected value:
- Faster decomposition for multi-lane execution.
- More consistent child task metadata and linkage.

## Proposal 3: Umbrella Rollup Dashboard/Report

Add orchestrator-facing report that summarizes umbrella status:
- child task state rollup,
- missing artifact fields,
- integration readiness indicator.

Expected value:
- Faster decision-making for integration.
- Less manual status inspection.

## Proposal 4: Backfill Existing Umbrella/Child Relations

Backfill recent tasks into first-class linkage once model support exists (for example, P3.M1.T8 and related follow-ons), so historical traces are queryable.

Expected value:
- Historical consistency.
- Accurate reporting over past and future work.

## Planning Notes

Recommended planning order:
1. Parent/child model and API.
2. Child-task scaffold helper.
3. Umbrella rollup report.
4. Historical backfill.

## Additional Brainstorm (Status Sync 2026-02-07)

### Proposal 5: Gate Policy Dry-Run Simulator

Add a simulation endpoint/UI mode that evaluates gate policies without creating tasks, so operators can tune thresholds before rollout.

Expected value:
- Safer policy tuning.
- Lower chance of gate-noise regressions.

### Proposal 6: Reviewer Workload Balancer

Add reviewer routing logic that assigns/queues gate checkpoints based on active load, SLA age, and capability tags.

Expected value:
- Better reviewer throughput.
- Reduced gate aging bottlenecks.

### Proposal 7: Integration Conflict Risk Scoring

Compute a pre-merge risk score from touched paths, dependency fan-in, and historical conflict data to prioritize integration order.

Expected value:
- Earlier conflict discovery.
- Better merge queue ordering.

### Proposal 8: Release Readiness Report API

Add a single report endpoint for phase/milestone readiness: gate backlog, implemented-age risk, integration outcomes, and blocking dependencies.

Expected value:
- Faster go/no-go decisions.
- Shared status truth for human reviewers and orchestrators.
