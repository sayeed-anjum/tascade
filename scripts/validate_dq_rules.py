#!/usr/bin/env python3
"""
Data Quality Rule Validation Script for Tascade Metrics

Validates data quality rules defined in docs/metrics/dq-rulebook-v1.md
against the Tascade database. Outputs pass/fail report for CI.

Usage:
    python scripts/validate_dq_rules.py
    python scripts/validate_dq_rules.py --critical-only
    python scripts/validate_dq_rules.py --table task
    python scripts/validate_dq_rules.py --format json
    python scripts/validate_dq_rules.py --fail-on-error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


# Database configuration
DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/tascade"


def _database_url() -> str:
    return os.getenv("TASCADE_DATABASE_URL", DEFAULT_DATABASE_URL)


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


# Severity levels
class Severity:
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DQViolation:
    rule_id: str
    table: str
    severity: str
    description: str
    count: int = 0
    sample_ids: list[str] = field(default_factory=list)


@dataclass
class DQResult:
    table: str
    passed: bool
    violations: list[DQViolation]
    total_checked: int = 0


@dataclass
class DQRule:
    rule_id: str
    table: str
    severity: str
    description: str
    kind: str
    where_clause: str | None = None
    count_query: str | None = None
    record_query: str | None = None


@dataclass
class DQTableSpec:
    table: str
    key_columns: list[str]


class DQValidator:
    """Validates data quality rules against Tascade tables."""

    def __init__(self, engine: Engine, sample_size: int = 5):
        self.engine = engine
        self.inspector = inspect(engine)
        self.results: list[DQResult] = []
        self.now = datetime.now(timezone.utc)
        self.sample_size = sample_size
        self.table_specs = self._build_table_specs()
        self.rules = self._build_rules()

    def _execute_query(self, query: str, params: dict | None = None) -> list[Any]:
        """Execute a query and return results."""
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return result.fetchall()

    def _get_count(self, query: str, params: dict | None = None) -> int:
        """Execute a count query and return the result."""
        rows = self._execute_query(query, params)
        return rows[0][0] if rows else 0

    def _table_exists(self, table: str) -> bool:
        return self.inspector.has_table(table)

    def _build_table_specs(self) -> dict[str, DQTableSpec]:
        return {
            "project": DQTableSpec(table="project", key_columns=["id"]),
            "task": DQTableSpec(table="task", key_columns=["id"]),
            "phase": DQTableSpec(table="phase", key_columns=["id"]),
            "milestone": DQTableSpec(table="milestone", key_columns=["id"]),
            "dependency_edge": DQTableSpec(table="dependency_edge", key_columns=["id"]),
            "lease": DQTableSpec(table="lease", key_columns=["id"]),
            "task_reservation": DQTableSpec(
                table="task_reservation", key_columns=["id"]
            ),
            "artifact": DQTableSpec(table="artifact", key_columns=["id"]),
            "integration_attempt": DQTableSpec(
                table="integration_attempt", key_columns=["id"]
            ),
            "gate_rule": DQTableSpec(table="gate_rule", key_columns=["id"]),
            "gate_decision": DQTableSpec(table="gate_decision", key_columns=["id"]),
            "gate_candidate_link": DQTableSpec(
                table="gate_candidate_link", key_columns=["id"]
            ),
            "event_log": DQTableSpec(table="event_log", key_columns=["id"]),
            "plan_change_set": DQTableSpec(table="plan_change_set", key_columns=["id"]),
            "plan_version": DQTableSpec(table="plan_version", key_columns=["id"]),
            "task_changelog_entry": DQTableSpec(
                table="task_changelog_entry", key_columns=["id"]
            ),
            "task_execution_snapshot": DQTableSpec(
                table="task_execution_snapshot", key_columns=["id"]
            ),
            "task_context_cache": DQTableSpec(
                table="task_context_cache",
                key_columns=[
                    "project_id",
                    "task_id",
                    "ancestor_depth",
                    "dependent_depth",
                ],
            ),
            "api_key": DQTableSpec(table="api_key", key_columns=["id"]),
        }

    def _record_key_expression(self, key_columns: list[str]) -> str:
        pairs: list[str] = []
        for column in key_columns:
            pairs.append(f"'{column}', {column}")
        return f"jsonb_build_object({', '.join(pairs)})"

    def _format_sample_ids(self, key_columns: list[str], rows: list[Any]) -> list[str]:
        sample_ids = []
        for row in rows:
            record_key = {key_columns[idx]: row[idx] for idx in range(len(key_columns))}
            sample_ids.append(json.dumps(record_key, default=str))
        return sample_ids

    def _duplicate_where_clause(
        self, table: str, key_columns: list[str], extra_where: str | None = None
    ) -> str:
        key_list = ", ".join(key_columns)
        filter_clause = f"WHERE {extra_where}" if extra_where else ""
        if len(key_columns) == 1:
            key = key_columns[0]
            subquery = (
                f"SELECT {key} FROM {table} {filter_clause} "
                f"GROUP BY {key} HAVING COUNT(*) > 1"
            )
            base = f"{key} IN ({subquery})"
        else:
            subquery = (
                f"SELECT {key_list} FROM {table} {filter_clause} "
                f"GROUP BY {key_list} HAVING COUNT(*) > 1"
            )
            base = f"({key_list}) IN ({subquery})"
        if extra_where:
            return f"({base}) AND ({extra_where})"
        return base

    def _rule_count(self, rule: DQRule) -> int:
        if rule.count_query:
            return self._get_count(rule.count_query)
        if rule.record_query:
            return self._get_count(f"SELECT COUNT(*) FROM ({rule.record_query}) dq")
        if rule.where_clause:
            return self._get_count(
                f"SELECT COUNT(*) FROM {rule.table} WHERE {rule.where_clause}"
            )
        return 0

    def _rule_record_query(self, rule: DQRule, key_columns: list[str]) -> str:
        if rule.record_query:
            return rule.record_query
        key_list = ", ".join(key_columns)
        return f"SELECT {key_list} FROM {rule.table} WHERE {rule.where_clause}"

    def _build_rules(self) -> list[DQRule]:
        rules: list[DQRule] = []

        def null_rule(
            table: str,
            field: str,
            rule_id: str,
            severity: str,
            description: str,
        ) -> None:
            rules.append(
                DQRule(
                    rule_id=rule_id,
                    table=table,
                    severity=severity,
                    description=description,
                    kind="null",
                    where_clause=f"{field} IS NULL",
                )
            )

        def null_or_empty_rule(
            table: str,
            field: str,
            rule_id: str,
            severity: str,
            description: str,
        ) -> None:
            rules.append(
                DQRule(
                    rule_id=rule_id,
                    table=table,
                    severity=severity,
                    description=description,
                    kind="null",
                    where_clause=f"{field} IS NULL OR {field} = ''",
                )
            )

        def enum_rule(
            table: str,
            field: str,
            valid_values: list[str],
            rule_id: str,
            severity: str,
            description: str,
        ) -> None:
            value_list = "(" + ", ".join([f"'{value}'" for value in valid_values]) + ")"
            rules.append(
                DQRule(
                    rule_id=rule_id,
                    table=table,
                    severity=severity,
                    description=description,
                    kind="enum",
                    where_clause=f"{field} NOT IN {value_list}",
                )
            )

        def range_rule(
            table: str,
            condition: str,
            rule_id: str,
            severity: str,
            description: str,
        ) -> None:
            rules.append(
                DQRule(
                    rule_id=rule_id,
                    table=table,
                    severity=severity,
                    description=description,
                    kind="outlier",
                    where_clause=condition,
                )
            )

        def time_rule(
            table: str,
            condition: str,
            rule_id: str,
            severity: str,
            description: str,
        ) -> None:
            rules.append(
                DQRule(
                    rule_id=rule_id,
                    table=table,
                    severity=severity,
                    description=description,
                    kind="lag",
                    where_clause=condition,
                )
            )

        def duplicate_rule(
            table: str,
            key_columns: list[str],
            rule_id: str,
            severity: str,
            description: str,
            extra_where: str | None = None,
        ) -> None:
            where_clause = self._duplicate_where_clause(table, key_columns, extra_where)
            rules.append(
                DQRule(
                    rule_id=rule_id,
                    table=table,
                    severity=severity,
                    description=description,
                    kind="duplicate",
                    where_clause=where_clause,
                )
            )

        def referential_rule(
            table: str,
            key_columns: list[str],
            fk_field: str,
            ref_table: str,
            rule_id: str,
            severity: str,
            description: str,
        ) -> None:
            key_select = ", ".join([f"t.{col} AS {col}" for col in key_columns])
            record_query = (
                f"SELECT {key_select} FROM {table} t "
                f"LEFT JOIN {ref_table} r ON t.{fk_field} = r.id "
                f"WHERE t.{fk_field} IS NOT NULL AND r.id IS NULL"
            )
            rules.append(
                DQRule(
                    rule_id=rule_id,
                    table=table,
                    severity=severity,
                    description=description,
                    kind="referential",
                    record_query=record_query,
                )
            )

        # Project stream
        null_rule(
            "project",
            "name",
            "PRJ-COMP-001",
            Severity.CRITICAL,
            "Project name must not be null",
        )
        null_rule(
            "project",
            "status",
            "PRJ-COMP-002",
            Severity.CRITICAL,
            "Project status must not be null",
        )
        rules.append(
            DQRule(
                rule_id="PRJ-COMP-003",
                table="project",
                severity=Severity.ERROR,
                description="Timestamps must be populated",
                kind="null",
                where_clause="created_at IS NULL OR updated_at IS NULL",
            )
        )
        time_rule(
            "project",
            "status = 'active' AND updated_at < NOW() - INTERVAL '30 days'",
            "PRJ-TIME-001",
            Severity.WARNING,
            "Active project not updated in 30 days",
        )
        time_rule(
            "project",
            "updated_at > NOW()",
            "PRJ-TIME-002",
            Severity.ERROR,
            "updated_at must not be in the future",
        )
        duplicate_rule(
            "project",
            ["id"],
            "PRJ-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate project IDs found",
        )
        enum_rule(
            "project",
            "status",
            ["active", "paused", "archived"],
            "PRJ-ACCU-001",
            Severity.ERROR,
            "Invalid project status value",
        )
        rules.append(
            DQRule(
                rule_id="PRJ-ACCU-002",
                table="project",
                severity=Severity.ERROR,
                description="created_at must not be later than updated_at",
                kind="consistency",
                where_clause="created_at > updated_at",
            )
        )

        # Task stream
        null_or_empty_rule(
            "task",
            "title",
            "TSK-COMP-001",
            Severity.CRITICAL,
            "Task title must not be null or empty",
        )
        null_rule(
            "task",
            "project_id",
            "TSK-COMP-002",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "task",
            "state",
            "TSK-COMP-003",
            Severity.CRITICAL,
            "Task state must not be null",
        )
        null_rule(
            "task",
            "task_class",
            "TSK-COMP-004",
            Severity.ERROR,
            "Task class must not be null",
        )
        null_rule(
            "task",
            "work_spec",
            "TSK-COMP-005",
            Severity.ERROR,
            "Work spec must not be null",
        )
        rules.append(
            DQRule(
                rule_id="TSK-TIME-001",
                table="task",
                severity=Severity.ERROR,
                description="Tasks in in_progress must have heartbeated within 1 hour",
                kind="lag",
                record_query=(
                    "SELECT t.id AS id FROM task t "
                    "LEFT JOIN lease l ON l.task_id = t.id AND l.status = 'active' "
                    "WHERE t.state = 'in_progress' AND (l.heartbeat_at IS NULL "
                    "OR l.heartbeat_at < NOW() - INTERVAL '1 hour')"
                ),
            )
        )
        time_rule(
            "task",
            "updated_at > NOW()",
            "TSK-TIME-002",
            Severity.ERROR,
            "updated_at must not exceed current time",
        )
        rules.append(
            DQRule(
                rule_id="TSK-TIME-003",
                table="task",
                severity=Severity.WARNING,
                description="Stale tasks in in_progress without heartbeat > 24h",
                kind="lag",
                record_query=(
                    "SELECT t.id AS id FROM task t "
                    "LEFT JOIN lease l ON l.task_id = t.id AND l.status = 'active' "
                    "WHERE t.state = 'in_progress' AND (l.heartbeat_at IS NULL "
                    "OR l.heartbeat_at < NOW() - INTERVAL '24 hours')"
                ),
            )
        )
        duplicate_rule(
            "task",
            ["id"],
            "TSK-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate task IDs found",
        )
        enum_rule(
            "task",
            "state",
            [
                "backlog",
                "ready",
                "reserved",
                "claimed",
                "in_progress",
                "implemented",
                "integrated",
                "conflict",
                "blocked",
                "abandoned",
                "cancelled",
            ],
            "TSK-ACCU-001",
            Severity.CRITICAL,
            "Invalid task state value",
        )
        enum_rule(
            "task",
            "task_class",
            [
                "architecture",
                "db_schema",
                "security",
                "cross_cutting",
                "review_gate",
                "merge_gate",
                "frontend",
                "backend",
                "crud",
                "other",
            ],
            "TSK-ACCU-002",
            Severity.ERROR,
            "Invalid task class value",
        )
        range_rule(
            "task",
            "priority < 1 OR priority > 1000",
            "TSK-ACCU-003",
            Severity.WARNING,
            "Priority must be between 1-1000",
        )
        rules.append(
            DQRule(
                rule_id="TSK-ACCU-004",
                table="task",
                severity=Severity.ERROR,
                description="Plan version consistency violated",
                kind="consistency",
                where_clause=(
                    "deprecated_in_plan_version IS NOT NULL "
                    "AND introduced_in_plan_version IS NOT NULL "
                    "AND deprecated_in_plan_version < introduced_in_plan_version"
                ),
            )
        )
        referential_rule(
            "task",
            ["id"],
            "project_id",
            "project",
            "TSK-ACCU-005",
            Severity.CRITICAL,
            "Orphan tasks with non-existent project_id",
        )
        referential_rule(
            "task",
            ["id"],
            "phase_id",
            "phase",
            "TSK-ACCU-006",
            Severity.ERROR,
            "Orphan tasks with non-existent phase_id",
        )
        referential_rule(
            "task",
            ["id"],
            "milestone_id",
            "milestone",
            "TSK-ACCU-007",
            Severity.ERROR,
            "Orphan tasks with non-existent milestone_id",
        )

        # Phase stream
        null_rule(
            "phase",
            "name",
            "PHS-COMP-001",
            Severity.CRITICAL,
            "Phase name must not be null",
        )
        null_rule(
            "phase",
            "project_id",
            "PHS-COMP-002",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "phase",
            "sequence",
            "PHS-COMP-003",
            Severity.ERROR,
            "Sequence must not be null",
        )
        duplicate_rule(
            "phase",
            ["id"],
            "PHS-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate phase IDs found",
        )
        duplicate_rule(
            "phase",
            ["project_id", "sequence"],
            "PHS-UNIQ-002",
            Severity.ERROR,
            "Duplicate project + sequence phases found",
        )
        range_rule(
            "phase",
            "sequence < 0",
            "PHS-ACCU-001",
            Severity.ERROR,
            "Sequence must be non-negative",
        )
        referential_rule(
            "phase",
            ["id"],
            "project_id",
            "project",
            "PHS-ACCU-002",
            Severity.CRITICAL,
            "Phases with non-existent project_id",
        )

        # Milestone stream
        null_rule(
            "milestone",
            "name",
            "MST-COMP-001",
            Severity.CRITICAL,
            "Milestone name must not be null",
        )
        null_rule(
            "milestone",
            "project_id",
            "MST-COMP-002",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "milestone",
            "sequence",
            "MST-COMP-003",
            Severity.ERROR,
            "Sequence must not be null",
        )
        duplicate_rule(
            "milestone",
            ["id"],
            "MST-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate milestone IDs found",
        )
        duplicate_rule(
            "milestone",
            ["project_id", "sequence"],
            "MST-UNIQ-002",
            Severity.ERROR,
            "Duplicate project + sequence milestones found",
        )
        range_rule(
            "milestone",
            "sequence < 0",
            "MST-ACCU-001",
            Severity.ERROR,
            "Sequence must be non-negative",
        )
        referential_rule(
            "milestone",
            ["id"],
            "project_id",
            "project",
            "MST-ACCU-002",
            Severity.CRITICAL,
            "Milestones with non-existent project_id",
        )
        referential_rule(
            "milestone",
            ["id"],
            "phase_id",
            "phase",
            "MST-ACCU-003",
            Severity.ERROR,
            "Milestones with non-existent phase_id",
        )

        # Dependency edge stream
        null_rule(
            "dependency_edge",
            "project_id",
            "DEP-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "dependency_edge",
            "from_task_id",
            "DEP-COMP-002",
            Severity.CRITICAL,
            "From task ID must not be null",
        )
        null_rule(
            "dependency_edge",
            "to_task_id",
            "DEP-COMP-003",
            Severity.CRITICAL,
            "To task ID must not be null",
        )
        null_rule(
            "dependency_edge",
            "unlock_on",
            "DEP-COMP-004",
            Severity.ERROR,
            "Unlock_on must not be null",
        )
        duplicate_rule(
            "dependency_edge",
            ["id"],
            "DEP-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate dependency edge IDs found",
        )
        duplicate_rule(
            "dependency_edge",
            ["project_id", "from_task_id", "to_task_id"],
            "DEP-UNIQ-002",
            Severity.ERROR,
            "Duplicate dependency edges found",
        )
        enum_rule(
            "dependency_edge",
            "unlock_on",
            ["implemented", "integrated"],
            "DEP-ACCU-001",
            Severity.ERROR,
            "Invalid unlock_on value",
        )
        rules.append(
            DQRule(
                rule_id="DEP-ACCU-002",
                table="dependency_edge",
                severity=Severity.CRITICAL,
                description="Self-loop dependencies found",
                kind="consistency",
                where_clause="from_task_id = to_task_id",
            )
        )
        referential_rule(
            "dependency_edge",
            ["id"],
            "project_id",
            "project",
            "DEP-ACCU-003",
            Severity.CRITICAL,
            "Edges with non-existent project_id",
        )
        referential_rule(
            "dependency_edge",
            ["id"],
            "from_task_id",
            "task",
            "DEP-ACCU-004",
            Severity.CRITICAL,
            "Edges with non-existent from_task_id",
        )
        referential_rule(
            "dependency_edge",
            ["id"],
            "to_task_id",
            "task",
            "DEP-ACCU-005",
            Severity.CRITICAL,
            "Edges with non-existent to_task_id",
        )
        rules.append(
            DQRule(
                rule_id="DEP-ACCU-006",
                table="dependency_edge",
                severity=Severity.ERROR,
                description="Dependency tasks must belong to same project",
                kind="referential",
                record_query=(
                    "SELECT de.id AS id FROM dependency_edge de "
                    "LEFT JOIN task tf ON de.from_task_id = tf.id "
                    "LEFT JOIN task tt ON de.to_task_id = tt.id "
                    "WHERE tf.project_id IS NOT NULL AND tt.project_id IS NOT NULL "
                    "AND (de.project_id <> tf.project_id OR de.project_id <> tt.project_id)"
                ),
            )
        )

        # Lease stream
        null_rule(
            "lease",
            "project_id",
            "LSE-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "lease",
            "task_id",
            "LSE-COMP-002",
            Severity.CRITICAL,
            "Task ID must not be null",
        )
        null_rule(
            "lease",
            "agent_id",
            "LSE-COMP-003",
            Severity.CRITICAL,
            "Agent ID must not be null",
        )
        null_rule(
            "lease",
            "token",
            "LSE-COMP-004",
            Severity.CRITICAL,
            "Token must not be null",
        )
        null_rule(
            "lease",
            "status",
            "LSE-COMP-005",
            Severity.CRITICAL,
            "Status must not be null",
        )
        null_rule(
            "lease",
            "expires_at",
            "LSE-COMP-006",
            Severity.CRITICAL,
            "Expiration timestamp must not be null",
        )
        time_rule(
            "lease",
            "status = 'active' AND expires_at < NOW()",
            "LSE-TIME-001",
            Severity.CRITICAL,
            "Active leases that have expired",
        )
        time_rule(
            "lease",
            "status = 'active' AND heartbeat_at < NOW() - INTERVAL '5 minutes'",
            "LSE-TIME-002",
            Severity.WARNING,
            "Active leases missing recent heartbeat",
        )
        time_rule(
            "lease",
            "status = 'expired' AND released_at IS NULL AND expires_at > NOW()",
            "LSE-TIME-003",
            Severity.ERROR,
            "Expired leases missing released_at or past expiration",
        )
        duplicate_rule(
            "lease",
            ["id"],
            "LSE-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate lease IDs found",
        )
        duplicate_rule(
            "lease",
            ["task_id"],
            "LSE-UNIQ-002",
            Severity.CRITICAL,
            "Multiple active leases per task",
            extra_where="status = 'active'",
        )
        duplicate_rule(
            "lease",
            ["token"],
            "LSE-UNIQ-003",
            Severity.CRITICAL,
            "Duplicate lease tokens found",
        )
        enum_rule(
            "lease",
            "status",
            ["active", "expired", "released", "consumed"],
            "LSE-ACCU-001",
            Severity.CRITICAL,
            "Invalid lease status value",
        )
        range_rule(
            "lease",
            "expires_at <= created_at",
            "LSE-ACCU-002",
            Severity.ERROR,
            "expires_at must be after created_at",
        )
        range_rule(
            "lease",
            "fencing_counter <= 0",
            "LSE-ACCU-003",
            Severity.WARNING,
            "Fencing counter must be positive",
        )
        referential_rule(
            "lease",
            ["id"],
            "project_id",
            "project",
            "LSE-ACCU-004",
            Severity.CRITICAL,
            "Leases with non-existent project_id",
        )
        referential_rule(
            "lease",
            ["id"],
            "task_id",
            "task",
            "LSE-ACCU-005",
            Severity.CRITICAL,
            "Leases with non-existent task_id",
        )

        # Task reservation stream
        null_rule(
            "task_reservation",
            "project_id",
            "RSV-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "task_reservation",
            "task_id",
            "RSV-COMP-002",
            Severity.CRITICAL,
            "Task ID must not be null",
        )
        null_rule(
            "task_reservation",
            "assignee_agent_id",
            "RSV-COMP-003",
            Severity.CRITICAL,
            "Assignee agent ID must not be null",
        )
        null_rule(
            "task_reservation",
            "created_by",
            "RSV-COMP-004",
            Severity.ERROR,
            "Created by must not be null",
        )
        time_rule(
            "task_reservation",
            "status = 'active' AND expires_at < NOW()",
            "RSV-TIME-001",
            Severity.CRITICAL,
            "Active reservations must not be expired",
        )
        range_rule(
            "task_reservation",
            "ttl_seconds < 60 OR ttl_seconds > 86400",
            "RSV-TIME-002",
            Severity.ERROR,
            "TTL must be between 60-86400 seconds",
        )
        duplicate_rule(
            "task_reservation",
            ["id"],
            "RSV-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate reservation IDs found",
        )
        duplicate_rule(
            "task_reservation",
            ["task_id"],
            "RSV-UNIQ-002",
            Severity.CRITICAL,
            "Multiple active reservations per task",
            extra_where="status = 'active'",
        )
        enum_rule(
            "task_reservation",
            "status",
            ["active", "expired", "released", "consumed"],
            "RSV-ACCU-001",
            Severity.CRITICAL,
            "Invalid reservation status value",
        )
        enum_rule(
            "task_reservation",
            "mode",
            ["hard"],
            "RSV-ACCU-002",
            Severity.ERROR,
            "Invalid reservation mode value",
        )
        range_rule(
            "task_reservation",
            "expires_at <= created_at",
            "RSV-ACCU-003",
            Severity.ERROR,
            "expires_at must be after created_at",
        )
        referential_rule(
            "task_reservation",
            ["id"],
            "project_id",
            "project",
            "RSV-ACCU-004",
            Severity.CRITICAL,
            "Reservations with non-existent project_id",
        )
        referential_rule(
            "task_reservation",
            ["id"],
            "task_id",
            "task",
            "RSV-ACCU-005",
            Severity.CRITICAL,
            "Reservations with non-existent task_id",
        )

        # Artifact stream
        null_rule(
            "artifact",
            "project_id",
            "ART-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "artifact",
            "task_id",
            "ART-COMP-002",
            Severity.CRITICAL,
            "Task ID must not be null",
        )
        null_rule(
            "artifact",
            "agent_id",
            "ART-COMP-003",
            Severity.CRITICAL,
            "Agent ID must not be null",
        )
        rules.append(
            DQRule(
                rule_id="ART-COMP-004",
                table="artifact",
                severity=Severity.ERROR,
                description="Touched files must be valid JSON array",
                kind="accuracy",
                where_clause="touched_files IS NULL OR jsonb_typeof(touched_files) <> 'array'",
            )
        )
        time_rule(
            "artifact",
            "created_at > NOW()",
            "ART-TIME-001",
            Severity.ERROR,
            "created_at must not be in the future",
        )
        duplicate_rule(
            "artifact",
            ["id"],
            "ART-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate artifact IDs found",
        )
        enum_rule(
            "artifact",
            "check_status",
            ["pending", "passed", "failed"],
            "ART-ACCU-001",
            Severity.ERROR,
            "Invalid check_status value",
        )
        range_rule(
            "artifact",
            "commit_sha IS NOT NULL AND LENGTH(commit_sha) != 40",
            "ART-ACCU-002",
            Severity.WARNING,
            "Invalid commit SHA format (expected 40 hex chars)",
        )
        referential_rule(
            "artifact",
            ["id"],
            "project_id",
            "project",
            "ART-ACCU-003",
            Severity.CRITICAL,
            "Artifacts with non-existent project_id",
        )
        referential_rule(
            "artifact",
            ["id"],
            "task_id",
            "task",
            "ART-ACCU-004",
            Severity.CRITICAL,
            "Artifacts with non-existent task_id",
        )
        rules.append(
            DQRule(
                rule_id="ART-ACCU-005",
                table="artifact",
                severity=Severity.WARNING,
                description="Touched files elements must be non-empty strings",
                kind="accuracy",
                where_clause=(
                    "EXISTS (SELECT 1 FROM jsonb_array_elements(touched_files) elem "
                    "WHERE jsonb_typeof(elem) IS DISTINCT FROM 'string' OR elem::text = '\"\"')"
                ),
            )
        )

        # Integration attempt stream
        null_rule(
            "integration_attempt",
            "project_id",
            "INT-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "integration_attempt",
            "task_id",
            "INT-COMP-002",
            Severity.CRITICAL,
            "Task ID must not be null",
        )
        null_rule(
            "integration_attempt",
            "result",
            "INT-COMP-003",
            Severity.CRITICAL,
            "Result must not be null",
        )
        null_rule(
            "integration_attempt",
            "diagnostics",
            "INT-COMP-004",
            Severity.ERROR,
            "Diagnostics must be valid JSON",
        )
        time_rule(
            "integration_attempt",
            "started_at > NOW()",
            "INT-TIME-001",
            Severity.ERROR,
            "started_at must not be in the future",
        )
        rules.append(
            DQRule(
                rule_id="INT-TIME-002",
                table="integration_attempt",
                severity=Severity.ERROR,
                description="ended_at must be after started_at",
                kind="consistency",
                where_clause="ended_at IS NOT NULL AND ended_at < started_at",
            )
        )
        rules.append(
            DQRule(
                rule_id="INT-TIME-003",
                table="integration_attempt",
                severity=Severity.WARNING,
                description="Completed attempts should have ended_at",
                kind="lag",
                where_clause="result <> 'queued' AND ended_at IS NULL",
            )
        )
        duplicate_rule(
            "integration_attempt",
            ["id"],
            "INT-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate integration attempt IDs found",
        )
        enum_rule(
            "integration_attempt",
            "result",
            ["queued", "success", "conflict", "failed_checks"],
            "INT-ACCU-001",
            Severity.CRITICAL,
            "Invalid integration attempt result",
        )
        range_rule(
            "integration_attempt",
            "base_sha IS NOT NULL AND LENGTH(base_sha) != 40",
            "INT-ACCU-002",
            Severity.WARNING,
            "Invalid base SHA format",
        )
        range_rule(
            "integration_attempt",
            "head_sha IS NOT NULL AND LENGTH(head_sha) != 40",
            "INT-ACCU-003",
            Severity.WARNING,
            "Invalid head SHA format",
        )
        referential_rule(
            "integration_attempt",
            ["id"],
            "project_id",
            "project",
            "INT-ACCU-004",
            Severity.CRITICAL,
            "Integration attempts with non-existent project_id",
        )
        referential_rule(
            "integration_attempt",
            ["id"],
            "task_id",
            "task",
            "INT-ACCU-005",
            Severity.CRITICAL,
            "Integration attempts with non-existent task_id",
        )

        # Gate rule stream
        null_rule(
            "gate_rule",
            "project_id",
            "GTR-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "gate_rule",
            "name",
            "GTR-COMP-002",
            Severity.CRITICAL,
            "Rule name must not be null",
        )
        null_rule(
            "gate_rule",
            "scope",
            "GTR-COMP-003",
            Severity.ERROR,
            "Scope JSON must be valid",
        )
        null_rule(
            "gate_rule",
            "conditions",
            "GTR-COMP-004",
            Severity.ERROR,
            "Conditions JSON must be valid",
        )
        null_rule(
            "gate_rule",
            "required_evidence",
            "GTR-COMP-005",
            Severity.ERROR,
            "Required evidence JSON must be valid",
        )
        duplicate_rule(
            "gate_rule",
            ["id"],
            "GTR-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate gate rule IDs found",
        )
        rules.append(
            DQRule(
                rule_id="GTR-ACCU-001",
                table="gate_rule",
                severity=Severity.ERROR,
                description="is_active must not be null",
                kind="accuracy",
                where_clause="is_active IS NULL",
            )
        )
        referential_rule(
            "gate_rule",
            ["id"],
            "project_id",
            "project",
            "GTR-ACCU-002",
            Severity.CRITICAL,
            "Gate rules with non-existent project_id",
        )
        rules.append(
            DQRule(
                rule_id="GTR-ACCU-003",
                table="gate_rule",
                severity=Severity.WARNING,
                description="Required reviewer roles must be non-empty when specified",
                kind="accuracy",
                where_clause="required_reviewer_roles IS NOT NULL AND array_length(required_reviewer_roles, 1) = 0",
            )
        )

        # Gate decision stream
        null_rule(
            "gate_decision",
            "project_id",
            "GTD-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "gate_decision",
            "gate_rule_id",
            "GTD-COMP-002",
            Severity.CRITICAL,
            "Gate rule ID must not be null",
        )
        null_rule(
            "gate_decision",
            "outcome",
            "GTD-COMP-003",
            Severity.CRITICAL,
            "Outcome must not be null",
        )
        null_rule(
            "gate_decision",
            "actor_id",
            "GTD-COMP-004",
            Severity.CRITICAL,
            "Actor ID must not be null",
        )
        null_rule(
            "gate_decision",
            "reason",
            "GTD-COMP-005",
            Severity.ERROR,
            "Reason must not be null",
        )
        null_rule(
            "gate_decision",
            "evidence_refs",
            "GTD-COMP-006",
            Severity.ERROR,
            "Evidence refs must be valid JSON",
        )
        duplicate_rule(
            "gate_decision",
            ["id"],
            "GTD-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate gate decision IDs found",
        )
        enum_rule(
            "gate_decision",
            "outcome",
            ["approved", "rejected", "approved_with_risk"],
            "GTD-ACCU-001",
            Severity.CRITICAL,
            "Invalid gate decision outcome value",
        )
        rules.append(
            DQRule(
                rule_id="GTD-ACCU-002",
                table="gate_decision",
                severity=Severity.CRITICAL,
                description="Either task_id or phase_id must be set",
                kind="consistency",
                where_clause="task_id IS NULL AND phase_id IS NULL",
            )
        )
        referential_rule(
            "gate_decision",
            ["id"],
            "project_id",
            "project",
            "GTD-ACCU-003",
            Severity.CRITICAL,
            "Decisions with non-existent project_id",
        )
        referential_rule(
            "gate_decision",
            ["id"],
            "gate_rule_id",
            "gate_rule",
            "GTD-ACCU-004",
            Severity.CRITICAL,
            "Decisions with non-existent gate_rule_id",
        )
        referential_rule(
            "gate_decision",
            ["id"],
            "task_id",
            "task",
            "GTD-ACCU-005",
            Severity.ERROR,
            "Decisions with non-existent task_id",
        )
        referential_rule(
            "gate_decision",
            ["id"],
            "phase_id",
            "phase",
            "GTD-ACCU-006",
            Severity.ERROR,
            "Decisions with non-existent phase_id",
        )

        # Gate candidate link stream
        null_rule(
            "gate_candidate_link",
            "project_id",
            "GCL-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "gate_candidate_link",
            "gate_task_id",
            "GCL-COMP-002",
            Severity.CRITICAL,
            "Gate task ID must not be null",
        )
        null_rule(
            "gate_candidate_link",
            "candidate_task_id",
            "GCL-COMP-003",
            Severity.CRITICAL,
            "Candidate task ID must not be null",
        )
        duplicate_rule(
            "gate_candidate_link",
            ["id"],
            "GCL-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate gate candidate link IDs found",
        )
        duplicate_rule(
            "gate_candidate_link",
            ["gate_task_id", "candidate_task_id"],
            "GCL-UNIQ-002",
            Severity.CRITICAL,
            "Duplicate gate/candidate pairs found",
        )
        range_rule(
            "gate_candidate_link",
            "candidate_order < 0",
            "GCL-ACCU-001",
            Severity.WARNING,
            "Candidate order must be non-negative",
        )
        referential_rule(
            "gate_candidate_link",
            ["id"],
            "project_id",
            "project",
            "GCL-ACCU-002",
            Severity.CRITICAL,
            "Gate candidate links with non-existent project_id",
        )
        referential_rule(
            "gate_candidate_link",
            ["id"],
            "gate_task_id",
            "task",
            "GCL-ACCU-003",
            Severity.CRITICAL,
            "Gate candidate links with non-existent gate_task_id",
        )
        referential_rule(
            "gate_candidate_link",
            ["id"],
            "candidate_task_id",
            "task",
            "GCL-ACCU-004",
            Severity.CRITICAL,
            "Gate candidate links with non-existent candidate_task_id",
        )
        rules.append(
            DQRule(
                rule_id="GCL-ACCU-005",
                table="gate_candidate_link",
                severity=Severity.ERROR,
                description="Gate task and candidate task must be different",
                kind="consistency",
                where_clause="gate_task_id = candidate_task_id",
            )
        )

        # Event log stream
        null_rule(
            "event_log",
            "project_id",
            "EVT-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "event_log",
            "entity_type",
            "EVT-COMP-002",
            Severity.CRITICAL,
            "Entity type must not be null",
        )
        null_rule(
            "event_log",
            "event_type",
            "EVT-COMP-003",
            Severity.CRITICAL,
            "Event type must not be null",
        )
        null_rule(
            "event_log",
            "payload",
            "EVT-COMP-004",
            Severity.ERROR,
            "Payload must be valid JSON",
        )
        time_rule(
            "event_log",
            "created_at > NOW()",
            "EVT-TIME-001",
            Severity.ERROR,
            "created_at must not be in the future",
        )
        rules.append(
            DQRule(
                rule_id="EVT-TIME-002",
                table="event_log",
                severity=Severity.WARNING,
                description="Recent events should not have significant lag (>1 hour)",
                kind="lag",
                record_query=(
                    "SELECT id AS id FROM event_log "
                    "WHERE id IN (SELECT id FROM event_log ORDER BY created_at DESC LIMIT 1000) "
                    "AND created_at < NOW() - INTERVAL '1 hour'"
                ),
            )
        )
        duplicate_rule(
            "event_log",
            ["id"],
            "EVT-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate event IDs found",
        )
        enum_rule(
            "event_log",
            "entity_type",
            ["task", "gate_decision"],
            "EVT-ACCU-001",
            Severity.WARNING,
            "Entity type must be from allowed set",
        )
        referential_rule(
            "event_log",
            ["id"],
            "project_id",
            "project",
            "EVT-ACCU-002",
            Severity.CRITICAL,
            "Events with non-existent project_id",
        )

        # Plan change set stream
        null_rule(
            "plan_change_set",
            "project_id",
            "PCS-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "plan_change_set",
            "base_plan_version",
            "PCS-COMP-002",
            Severity.CRITICAL,
            "Base plan version must not be null",
        )
        null_rule(
            "plan_change_set",
            "target_plan_version",
            "PCS-COMP-003",
            Severity.CRITICAL,
            "Target plan version must not be null",
        )
        null_rule(
            "plan_change_set",
            "operations",
            "PCS-COMP-004",
            Severity.CRITICAL,
            "Operations must be valid JSON",
        )
        null_rule(
            "plan_change_set",
            "created_by",
            "PCS-COMP-005",
            Severity.ERROR,
            "Created by must not be null",
        )
        duplicate_rule(
            "plan_change_set",
            ["id"],
            "PCS-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate change set IDs found",
        )
        duplicate_rule(
            "plan_change_set",
            ["project_id", "target_plan_version"],
            "PCS-UNIQ-002",
            Severity.CRITICAL,
            "Duplicate project + target plan version change sets found",
        )
        enum_rule(
            "plan_change_set",
            "status",
            ["draft", "validated", "applied", "rejected"],
            "PCS-ACCU-001",
            Severity.ERROR,
            "Invalid change set status",
        )
        range_rule(
            "plan_change_set",
            "target_plan_version <= base_plan_version",
            "PCS-ACCU-002",
            Severity.ERROR,
            "Target version must be > base version",
        )
        range_rule(
            "plan_change_set",
            "base_plan_version < 1 OR target_plan_version < 1",
            "PCS-ACCU-003",
            Severity.ERROR,
            "Plan versions must be >= 1",
        )
        referential_rule(
            "plan_change_set",
            ["id"],
            "project_id",
            "project",
            "PCS-ACCU-004",
            Severity.CRITICAL,
            "Plan change sets with non-existent project_id",
        )
        rules.append(
            DQRule(
                rule_id="PCS-ACCU-005",
                table="plan_change_set",
                severity=Severity.ERROR,
                description="Applied fields must be set when status='applied'",
                kind="consistency",
                where_clause="status = 'applied' AND (applied_by IS NULL OR applied_at IS NULL)",
            )
        )

        # Plan version stream
        null_rule(
            "plan_version",
            "project_id",
            "PVN-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "plan_version",
            "version_number",
            "PVN-COMP-002",
            Severity.CRITICAL,
            "Version number must not be null",
        )
        null_rule(
            "plan_version",
            "created_by",
            "PVN-COMP-003",
            Severity.ERROR,
            "Created by must not be null",
        )
        duplicate_rule(
            "plan_version",
            ["id"],
            "PVN-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate plan version IDs found",
        )
        duplicate_rule(
            "plan_version",
            ["project_id", "version_number"],
            "PVN-UNIQ-002",
            Severity.CRITICAL,
            "Duplicate project + version number plan versions found",
        )
        range_rule(
            "plan_version",
            "version_number < 1",
            "PVN-ACCU-001",
            Severity.ERROR,
            "Version number must be >= 1",
        )
        referential_rule(
            "plan_version",
            ["id"],
            "project_id",
            "project",
            "PVN-ACCU-002",
            Severity.CRITICAL,
            "Plan versions with non-existent project_id",
        )
        referential_rule(
            "plan_version",
            ["id"],
            "change_set_id",
            "plan_change_set",
            "PVN-ACCU-003",
            Severity.ERROR,
            "Plan versions with non-existent change_set_id",
        )

        # Task changelog entry stream
        null_rule(
            "task_changelog_entry",
            "project_id",
            "TCL-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "task_changelog_entry",
            "task_id",
            "TCL-COMP-002",
            Severity.CRITICAL,
            "Task ID must not be null",
        )
        null_rule(
            "task_changelog_entry",
            "author_type",
            "TCL-COMP-003",
            Severity.CRITICAL,
            "Author type must not be null",
        )
        null_rule(
            "task_changelog_entry",
            "entry_type",
            "TCL-COMP-004",
            Severity.CRITICAL,
            "Entry type must not be null",
        )
        null_rule(
            "task_changelog_entry",
            "content",
            "TCL-COMP-005",
            Severity.CRITICAL,
            "Content must not be null",
        )
        null_rule(
            "task_changelog_entry",
            "artifact_refs",
            "TCL-COMP-006",
            Severity.ERROR,
            "Artifact refs must be valid JSON",
        )
        duplicate_rule(
            "task_changelog_entry",
            ["id"],
            "TCL-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate changelog entry IDs found",
        )
        enum_rule(
            "task_changelog_entry",
            "author_type",
            ["human", "agent", "system"],
            "TCL-ACCU-001",
            Severity.CRITICAL,
            "Invalid author type",
        )
        enum_rule(
            "task_changelog_entry",
            "entry_type",
            ["summary", "decision", "risk", "note", "outcome"],
            "TCL-ACCU-002",
            Severity.CRITICAL,
            "Invalid entry type",
        )
        referential_rule(
            "task_changelog_entry",
            ["id"],
            "project_id",
            "project",
            "TCL-ACCU-003",
            Severity.CRITICAL,
            "Changelog entries with non-existent project_id",
        )
        referential_rule(
            "task_changelog_entry",
            ["id"],
            "task_id",
            "task",
            "TCL-ACCU-004",
            Severity.CRITICAL,
            "Changelog entries with non-existent task_id",
        )

        # Task execution snapshot stream
        null_rule(
            "task_execution_snapshot",
            "project_id",
            "TES-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "task_execution_snapshot",
            "task_id",
            "TES-COMP-002",
            Severity.CRITICAL,
            "Task ID must not be null",
        )
        null_rule(
            "task_execution_snapshot",
            "lease_id",
            "TES-COMP-003",
            Severity.CRITICAL,
            "Lease ID must not be null",
        )
        null_rule(
            "task_execution_snapshot",
            "work_spec_payload",
            "TES-COMP-004",
            Severity.CRITICAL,
            "Work spec payload must be valid JSON",
        )
        null_rule(
            "task_execution_snapshot",
            "work_spec_hash",
            "TES-COMP-005",
            Severity.CRITICAL,
            "Work spec hash must not be null",
        )
        null_rule(
            "task_execution_snapshot",
            "captured_by",
            "TES-COMP-006",
            Severity.ERROR,
            "Captured by must not be null",
        )
        duplicate_rule(
            "task_execution_snapshot",
            ["id"],
            "TES-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate snapshot IDs found",
        )
        duplicate_rule(
            "task_execution_snapshot",
            ["lease_id"],
            "TES-UNIQ-002",
            Severity.CRITICAL,
            "Duplicate lease IDs in snapshots",
        )
        range_rule(
            "task_execution_snapshot",
            "captured_plan_version < 1",
            "TES-ACCU-001",
            Severity.ERROR,
            "Captured plan version must be >= 1",
        )
        referential_rule(
            "task_execution_snapshot",
            ["id"],
            "project_id",
            "project",
            "TES-ACCU-002",
            Severity.CRITICAL,
            "Snapshots with non-existent project_id",
        )
        referential_rule(
            "task_execution_snapshot",
            ["id"],
            "task_id",
            "task",
            "TES-ACCU-003",
            Severity.CRITICAL,
            "Snapshots with non-existent task_id",
        )
        referential_rule(
            "task_execution_snapshot",
            ["id"],
            "lease_id",
            "lease",
            "TES-ACCU-004",
            Severity.CRITICAL,
            "Snapshots with non-existent lease_id",
        )

        # Task context cache stream
        null_rule(
            "task_context_cache",
            "project_id",
            "TCC-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "task_context_cache",
            "task_id",
            "TCC-COMP-002",
            Severity.CRITICAL,
            "Task ID must not be null",
        )
        null_rule(
            "task_context_cache",
            "payload",
            "TCC-COMP-003",
            Severity.CRITICAL,
            "Payload must be valid JSON",
        )
        time_rule(
            "task_context_cache",
            "computed_at < NOW() - INTERVAL '7 days'",
            "TCC-TIME-001",
            Severity.WARNING,
            "Cache entries older than 7 days may be stale",
        )
        duplicate_rule(
            "task_context_cache",
            ["project_id", "task_id", "ancestor_depth", "dependent_depth"],
            "TCC-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate task context cache entries found",
        )
        range_rule(
            "task_context_cache",
            "ancestor_depth < 0 OR ancestor_depth > 5",
            "TCC-ACCU-001",
            Severity.ERROR,
            "Ancestor depth must be between 0-5",
        )
        range_rule(
            "task_context_cache",
            "dependent_depth < 0 OR dependent_depth > 5",
            "TCC-ACCU-002",
            Severity.ERROR,
            "Dependent depth must be between 0-5",
        )
        referential_rule(
            "task_context_cache",
            ["project_id", "task_id", "ancestor_depth", "dependent_depth"],
            "project_id",
            "project",
            "TCC-ACCU-003",
            Severity.CRITICAL,
            "Task context cache entries with non-existent project_id",
        )
        referential_rule(
            "task_context_cache",
            ["project_id", "task_id", "ancestor_depth", "dependent_depth"],
            "task_id",
            "task",
            "TCC-ACCU-004",
            Severity.CRITICAL,
            "Task context cache entries with non-existent task_id",
        )

        # API key stream
        null_rule(
            "api_key",
            "project_id",
            "KEY-COMP-001",
            Severity.CRITICAL,
            "Project ID must not be null",
        )
        null_rule(
            "api_key",
            "name",
            "KEY-COMP-002",
            Severity.CRITICAL,
            "Key name must not be null",
        )
        null_rule(
            "api_key",
            "hash",
            "KEY-COMP-003",
            Severity.CRITICAL,
            "Hash must not be null",
        )
        null_rule(
            "api_key",
            "created_by",
            "KEY-COMP-004",
            Severity.ERROR,
            "Created by must not be null",
        )
        duplicate_rule(
            "api_key",
            ["id"],
            "KEY-UNIQ-001",
            Severity.CRITICAL,
            "Duplicate API key IDs found",
        )
        duplicate_rule(
            "api_key",
            ["hash"],
            "KEY-UNIQ-002",
            Severity.CRITICAL,
            "Duplicate API key hashes found",
        )
        enum_rule(
            "api_key",
            "status",
            ["active", "revoked"],
            "KEY-ACCU-001",
            Severity.CRITICAL,
            "Invalid api_key status",
        )
        rules.append(
            DQRule(
                rule_id="KEY-ACCU-002",
                table="api_key",
                severity=Severity.WARNING,
                description="If revoked_at is set, status should be 'revoked'",
                kind="consistency",
                where_clause="revoked_at IS NOT NULL AND status <> 'revoked'",
            )
        )
        rules.append(
            DQRule(
                rule_id="KEY-ACCU-003",
                table="api_key",
                severity=Severity.ERROR,
                description="last_used_at should be >= created_at if set",
                kind="consistency",
                where_clause="last_used_at IS NOT NULL AND last_used_at < created_at",
            )
        )
        referential_rule(
            "api_key",
            ["id"],
            "project_id",
            "project",
            "KEY-ACCU-004",
            Severity.CRITICAL,
            "API keys with non-existent project_id",
        )

        return rules

    def validate_project(self) -> DQResult:
        """Validate project table DQ rules."""
        violations = []
        total = self._get_count("SELECT COUNT(*) FROM project")

        # Completeness Rules
        # PRJ-COMP-001: Project name must not be null
        null_names = self._get_count("SELECT COUNT(*) FROM project WHERE name IS NULL")
        if null_names > 0:
            violations.append(
                DQViolation(
                    rule_id="PRJ-COMP-001",
                    table="project",
                    severity=Severity.CRITICAL,
                    description="Project name must not be null",
                    count=null_names,
                )
            )

        # PRJ-COMP-002: Project status must not be null
        null_status = self._get_count(
            "SELECT COUNT(*) FROM project WHERE status IS NULL"
        )
        if null_status > 0:
            violations.append(
                DQViolation(
                    rule_id="PRJ-COMP-002",
                    table="project",
                    severity=Severity.CRITICAL,
                    description="Project status must not be null",
                    count=null_status,
                )
            )

        # PRJ-COMP-003: Timestamps must be populated
        null_timestamps = self._get_count(
            "SELECT COUNT(*) FROM project WHERE created_at IS NULL OR updated_at IS NULL"
        )
        if null_timestamps > 0:
            violations.append(
                DQViolation(
                    rule_id="PRJ-COMP-003",
                    table="project",
                    severity=Severity.ERROR,
                    description="Timestamps must be populated",
                    count=null_timestamps,
                )
            )

        # Timeliness Rules
        # PRJ-TIME-001: updated_at should be within 30 days for active projects
        stale_active = self._get_count(
            """SELECT COUNT(*) FROM project 
               WHERE status = 'active' 
               AND updated_at < NOW() - INTERVAL '30 days'"""
        )
        if stale_active > 0:
            violations.append(
                DQViolation(
                    rule_id="PRJ-TIME-001",
                    table="project",
                    severity=Severity.WARNING,
                    description="Active project not updated in 30 days",
                    count=stale_active,
                )
            )

        # PRJ-TIME-002: updated_at must not be in the future
        future_update = self._get_count(
            "SELECT COUNT(*) FROM project WHERE updated_at > NOW()"
        )
        if future_update > 0:
            violations.append(
                DQViolation(
                    rule_id="PRJ-TIME-002",
                    table="project",
                    severity=Severity.ERROR,
                    description="updated_at must not be in the future",
                    count=future_update,
                )
            )

        # Uniqueness Rules
        # PRJ-UNIQ-001: Project ID must be unique
        dup_ids = self._get_count(
            """SELECT COUNT(*) FROM (
                SELECT id, COUNT(*) as cnt FROM project GROUP BY id HAVING COUNT(*) > 1
            ) sub"""
        )
        if dup_ids > 0:
            violations.append(
                DQViolation(
                    rule_id="PRJ-UNIQ-001",
                    table="project",
                    severity=Severity.CRITICAL,
                    description="Duplicate project IDs found",
                    count=dup_ids,
                )
            )

        # Accuracy Rules
        # PRJ-ACCU-001: status must be valid enum value
        invalid_status = self._get_count(
            "SELECT COUNT(*) FROM project WHERE status NOT IN ('active', 'paused', 'archived')"
        )
        if invalid_status > 0:
            violations.append(
                DQViolation(
                    rule_id="PRJ-ACCU-001",
                    table="project",
                    severity=Severity.ERROR,
                    description="Invalid project status value",
                    count=invalid_status,
                )
            )

        # PRJ-ACCU-002: created_at must not be later than updated_at
        invalid_timeline = self._get_count(
            "SELECT COUNT(*) FROM project WHERE created_at > updated_at"
        )
        if invalid_timeline > 0:
            violations.append(
                DQViolation(
                    rule_id="PRJ-ACCU-002",
                    table="project",
                    severity=Severity.ERROR,
                    description="created_at must not be later than updated_at",
                    count=invalid_timeline,
                )
            )

        passed = len(violations) == 0
        return DQResult(
            table="project", passed=passed, violations=violations, total_checked=total
        )

    def validate_task(self) -> DQResult:
        """Validate task table DQ rules."""
        violations = []
        total = self._get_count("SELECT COUNT(*) FROM task")

        # Completeness Rules
        # TSK-COMP-001: Task title must not be null or empty
        null_titles = self._get_count(
            "SELECT COUNT(*) FROM task WHERE title IS NULL OR title = ''"
        )
        if null_titles > 0:
            violations.append(
                DQViolation(
                    rule_id="TSK-COMP-001",
                    table="task",
                    severity=Severity.CRITICAL,
                    description="Task title must not be null or empty",
                    count=null_titles,
                )
            )

        # TSK-COMP-002: Project ID must not be null
        null_proj = self._get_count(
            "SELECT COUNT(*) FROM task WHERE project_id IS NULL"
        )
        if null_proj > 0:
            violations.append(
                DQViolation(
                    rule_id="TSK-COMP-002",
                    table="task",
                    severity=Severity.CRITICAL,
                    description="Project ID must not be null",
                    count=null_proj,
                )
            )

        # TSK-COMP-003: Task state must not be null
        null_state = self._get_count("SELECT COUNT(*) FROM task WHERE state IS NULL")
        if null_state > 0:
            violations.append(
                DQViolation(
                    rule_id="TSK-COMP-003",
                    table="task",
                    severity=Severity.CRITICAL,
                    description="Task state must not be null",
                    count=null_state,
                )
            )

        # TSK-COMP-004: Task class must not be null
        null_class = self._get_count(
            "SELECT COUNT(*) FROM task WHERE task_class IS NULL"
        )
        if null_class > 0:
            violations.append(
                DQViolation(
                    rule_id="TSK-COMP-004",
                    table="task",
                    severity=Severity.ERROR,
                    description="Task class must not be null",
                    count=null_class,
                )
            )

        # TSK-COMP-005: Work spec must be valid JSON (not null when it should exist)
        null_spec = self._get_count("SELECT COUNT(*) FROM task WHERE work_spec IS NULL")
        if null_spec > 0:
            violations.append(
                DQViolation(
                    rule_id="TSK-COMP-005",
                    table="task",
                    severity=Severity.ERROR,
                    description="Work spec must not be null",
                    count=null_spec,
                )
            )

        # Timeliness Rules
        # TSK-TIME-002: Task updated_at must not exceed current time
        future_update = self._get_count(
            "SELECT COUNT(*) FROM task WHERE updated_at > NOW()"
        )
        if future_update > 0:
            violations.append(
                DQViolation(
                    rule_id="TSK-TIME-002",
                    table="task",
                    severity=Severity.ERROR,
                    description="updated_at must not exceed current time",
                    count=future_update,
                )
            )

        # Uniqueness Rules
        # TSK-UNIQ-001: Task ID must be unique
        dup_ids = self._get_count(
            """SELECT COUNT(*) FROM (
                SELECT id, COUNT(*) FROM task GROUP BY id HAVING COUNT(*) > 1
            ) sub"""
        )
        if dup_ids > 0:
            violations.append(
                DQViolation(
                    rule_id="TSK-UNIQ-001",
                    table="task",
                    severity=Severity.CRITICAL,
                    description="Duplicate task IDs found",
                    count=dup_ids,
                )
            )

        # Accuracy Rules
        # TSK-ACCU-001: state must be valid enum value
        valid_states = [
            "backlog",
            "ready",
            "reserved",
            "claimed",
            "in_progress",
            "implemented",
            "integrated",
            "conflict",
            "blocked",
            "abandoned",
            "cancelled",
        ]
        invalid_state = self._get_count(
            f"SELECT COUNT(*) FROM task WHERE state NOT IN {tuple(valid_states)}"
        )
        if invalid_state > 0:
            violations.append(
                DQViolation(
                    rule_id="TSK-ACCU-001",
                    table="task",
                    severity=Severity.CRITICAL,
                    description="Invalid task state value",
                    count=invalid_state,
                )
            )

        # TSK-ACCU-002: task_class must be valid enum value
        valid_classes = [
            "architecture",
            "db_schema",
            "security",
            "cross_cutting",
            "review_gate",
            "merge_gate",
            "frontend",
            "backend",
            "crud",
            "other",
        ]
        invalid_class = self._get_count(
            f"SELECT COUNT(*) FROM task WHERE task_class NOT IN {tuple(valid_classes)}"
        )
        if invalid_class > 0:
            violations.append(
                DQViolation(
                    rule_id="TSK-ACCU-002",
                    table="task",
                    severity=Severity.ERROR,
                    description="Invalid task class value",
                    count=invalid_class,
                )
            )

        # TSK-ACCU-003: priority must be between 1-1000
        invalid_priority = self._get_count(
            "SELECT COUNT(*) FROM task WHERE priority < 1 OR priority > 1000"
        )
        if invalid_priority > 0:
            violations.append(
                DQViolation(
                    rule_id="TSK-ACCU-003",
                    table="task",
                    severity=Severity.WARNING,
                    description="Priority must be between 1-1000",
                    count=invalid_priority,
                )
            )

        # TSK-ACCU-005: Referential integrity - project_id must exist
        orphan_tasks = self._get_count(
            """SELECT COUNT(*) FROM task t
               LEFT JOIN project p ON t.project_id = p.id
               WHERE p.id IS NULL"""
        )
        if orphan_tasks > 0:
            violations.append(
                DQViolation(
                    rule_id="TSK-ACCU-005",
                    table="task",
                    severity=Severity.CRITICAL,
                    description="Orphan tasks with non-existent project_id",
                    count=orphan_tasks,
                )
            )

        passed = len(violations) == 0
        return DQResult(
            table="task", passed=passed, violations=violations, total_checked=total
        )

    def validate_dependency_edge(self) -> DQResult:
        """Validate dependency_edge table DQ rules."""
        violations = []
        total = self._get_count("SELECT COUNT(*) FROM dependency_edge")

        # Completeness Rules
        # DEP-COMP-001: Project ID must not be null
        null_proj = self._get_count(
            "SELECT COUNT(*) FROM dependency_edge WHERE project_id IS NULL"
        )
        if null_proj > 0:
            violations.append(
                DQViolation(
                    rule_id="DEP-COMP-001",
                    table="dependency_edge",
                    severity=Severity.CRITICAL,
                    description="Project ID must not be null",
                    count=null_proj,
                )
            )

        # DEP-COMP-002: From task ID must not be null
        null_from = self._get_count(
            "SELECT COUNT(*) FROM dependency_edge WHERE from_task_id IS NULL"
        )
        if null_from > 0:
            violations.append(
                DQViolation(
                    rule_id="DEP-COMP-002",
                    table="dependency_edge",
                    severity=Severity.CRITICAL,
                    description="From task ID must not be null",
                    count=null_from,
                )
            )

        # DEP-COMP-003: To task ID must not be null
        null_to = self._get_count(
            "SELECT COUNT(*) FROM dependency_edge WHERE to_task_id IS NULL"
        )
        if null_to > 0:
            violations.append(
                DQViolation(
                    rule_id="DEP-COMP-003",
                    table="dependency_edge",
                    severity=Severity.CRITICAL,
                    description="To task ID must not be null",
                    count=null_to,
                )
            )

        # DEP-COMP-004: Unlock state must not be null
        null_unlock = self._get_count(
            "SELECT COUNT(*) FROM dependency_edge WHERE unlock_on IS NULL"
        )
        if null_unlock > 0:
            violations.append(
                DQViolation(
                    rule_id="DEP-COMP-004",
                    table="dependency_edge",
                    severity=Severity.ERROR,
                    description="Unlock_on must not be null",
                    count=null_unlock,
                )
            )

        # Uniqueness Rules
        # DEP-UNIQ-001: Edge ID must be unique
        dup_ids = self._get_count(
            """SELECT COUNT(*) FROM (
                SELECT id, COUNT(*) FROM dependency_edge GROUP BY id HAVING COUNT(*) > 1
            ) sub"""
        )
        if dup_ids > 0:
            violations.append(
                DQViolation(
                    rule_id="DEP-UNIQ-001",
                    table="dependency_edge",
                    severity=Severity.CRITICAL,
                    description="Duplicate dependency edge IDs found",
                    count=dup_ids,
                )
            )

        # DEP-UNIQ-002: Project + from_task + to_task must be unique
        dup_edges = self._get_count(
            """SELECT COUNT(*) FROM (
                SELECT project_id, from_task_id, to_task_id, COUNT(*) as cnt 
                FROM dependency_edge 
                GROUP BY project_id, from_task_id, to_task_id 
                HAVING COUNT(*) > 1
            ) sub"""
        )
        if dup_edges > 0:
            violations.append(
                DQViolation(
                    rule_id="DEP-UNIQ-002",
                    table="dependency_edge",
                    severity=Severity.ERROR,
                    description="Duplicate dependency edges found",
                    count=dup_edges,
                )
            )

        # Accuracy Rules
        # DEP-ACCU-001: unlock_on must be valid enum value
        invalid_unlock = self._get_count(
            "SELECT COUNT(*) FROM dependency_edge WHERE unlock_on NOT IN ('implemented', 'integrated')"
        )
        if invalid_unlock > 0:
            violations.append(
                DQViolation(
                    rule_id="DEP-ACCU-001",
                    table="dependency_edge",
                    severity=Severity.ERROR,
                    description="Invalid unlock_on value",
                    count=invalid_unlock,
                )
            )

        # DEP-ACCU-002: From task and to task must not be the same
        self_loops = self._get_count(
            "SELECT COUNT(*) FROM dependency_edge WHERE from_task_id = to_task_id"
        )
        if self_loops > 0:
            violations.append(
                DQViolation(
                    rule_id="DEP-ACCU-002",
                    table="dependency_edge",
                    severity=Severity.CRITICAL,
                    description="Self-loop dependencies found",
                    count=self_loops,
                )
            )

        # DEP-ACCU-003: Referential integrity - project_id must exist
        orphan_proj = self._get_count(
            """SELECT COUNT(*) FROM dependency_edge de
               LEFT JOIN project p ON de.project_id = p.id
               WHERE p.id IS NULL"""
        )
        if orphan_proj > 0:
            violations.append(
                DQViolation(
                    rule_id="DEP-ACCU-003",
                    table="dependency_edge",
                    severity=Severity.CRITICAL,
                    description="Edges with non-existent project_id",
                    count=orphan_proj,
                )
            )

        # DEP-ACCU-004/005: Referential integrity - task IDs must exist
        orphan_from = self._get_count(
            """SELECT COUNT(*) FROM dependency_edge de
               LEFT JOIN task t ON de.from_task_id = t.id
               WHERE t.id IS NULL"""
        )
        if orphan_from > 0:
            violations.append(
                DQViolation(
                    rule_id="DEP-ACCU-004",
                    table="dependency_edge",
                    severity=Severity.CRITICAL,
                    description="Edges with non-existent from_task_id",
                    count=orphan_from,
                )
            )

        orphan_to = self._get_count(
            """SELECT COUNT(*) FROM dependency_edge de
               LEFT JOIN task t ON de.to_task_id = t.id
               WHERE t.id IS NULL"""
        )
        if orphan_to > 0:
            violations.append(
                DQViolation(
                    rule_id="DEP-ACCU-005",
                    table="dependency_edge",
                    severity=Severity.CRITICAL,
                    description="Edges with non-existent to_task_id",
                    count=orphan_to,
                )
            )

        passed = len(violations) == 0
        return DQResult(
            table="dependency_edge",
            passed=passed,
            violations=violations,
            total_checked=total,
        )

    def validate_lease(self) -> DQResult:
        """Validate lease table DQ rules."""
        violations = []
        total = self._get_count("SELECT COUNT(*) FROM lease")

        # Completeness Rules
        required_fields = [
            ("project_id", "LSE-COMP-001", Severity.CRITICAL),
            ("task_id", "LSE-COMP-002", Severity.CRITICAL),
            ("agent_id", "LSE-COMP-003", Severity.CRITICAL),
            ("token", "LSE-COMP-004", Severity.CRITICAL),
            ("status", "LSE-COMP-005", Severity.CRITICAL),
            ("expires_at", "LSE-COMP-006", Severity.CRITICAL),
        ]

        for field, rule_id, severity in required_fields:
            null_count = self._get_count(
                f"SELECT COUNT(*) FROM lease WHERE {field} IS NULL"
            )
            if null_count > 0:
                violations.append(
                    DQViolation(
                        rule_id=rule_id,
                        table="lease",
                        severity=severity,
                        description=f"{field} must not be null",
                        count=null_count,
                    )
                )

        # Timeliness Rules
        # LSE-TIME-001: Active leases must not be expired
        expired_active = self._get_count(
            """SELECT COUNT(*) FROM lease 
               WHERE status = 'active' AND expires_at < NOW()"""
        )
        if expired_active > 0:
            violations.append(
                DQViolation(
                    rule_id="LSE-TIME-001",
                    table="lease",
                    severity=Severity.CRITICAL,
                    description="Active leases that have expired",
                    count=expired_active,
                )
            )

        # Uniqueness Rules
        # LSE-UNIQ-001: Lease ID must be unique
        dup_ids = self._get_count(
            """SELECT COUNT(*) FROM (
                SELECT id, COUNT(*) FROM lease GROUP BY id HAVING COUNT(*) > 1
            ) sub"""
        )
        if dup_ids > 0:
            violations.append(
                DQViolation(
                    rule_id="LSE-UNIQ-001",
                    table="lease",
                    severity=Severity.CRITICAL,
                    description="Duplicate lease IDs found",
                    count=dup_ids,
                )
            )

        # LSE-UNIQ-003: Token must be unique
        dup_tokens = self._get_count(
            """SELECT COUNT(*) FROM (
                SELECT token, COUNT(*) FROM lease GROUP BY token HAVING COUNT(*) > 1
            ) sub"""
        )
        if dup_tokens > 0:
            violations.append(
                DQViolation(
                    rule_id="LSE-UNIQ-003",
                    table="lease",
                    severity=Severity.CRITICAL,
                    description="Duplicate lease tokens found",
                    count=dup_tokens,
                )
            )

        # Accuracy Rules
        # LSE-ACCU-001: status must be valid enum value
        valid_statuses = ("active", "expired", "released", "consumed")
        invalid_status = self._get_count(
            f"SELECT COUNT(*) FROM lease WHERE status NOT IN {valid_statuses}"
        )
        if invalid_status > 0:
            violations.append(
                DQViolation(
                    rule_id="LSE-ACCU-001",
                    table="lease",
                    severity=Severity.CRITICAL,
                    description="Invalid lease status value",
                    count=invalid_status,
                )
            )

        # LSE-ACCU-002: expires_at must be after created_at
        invalid_timing = self._get_count(
            "SELECT COUNT(*) FROM lease WHERE expires_at <= created_at"
        )
        if invalid_timing > 0:
            violations.append(
                DQViolation(
                    rule_id="LSE-ACCU-002",
                    table="lease",
                    severity=Severity.ERROR,
                    description="expires_at must be after created_at",
                    count=invalid_timing,
                )
            )

        passed = len(violations) == 0
        return DQResult(
            table="lease", passed=passed, violations=violations, total_checked=total
        )

    def validate_artifact(self) -> DQResult:
        """Validate artifact table DQ rules."""
        violations = []
        total = self._get_count("SELECT COUNT(*) FROM artifact")

        # Completeness Rules
        # ART-COMP-001: Project ID must not be null
        null_proj = self._get_count(
            "SELECT COUNT(*) FROM artifact WHERE project_id IS NULL"
        )
        if null_proj > 0:
            violations.append(
                DQViolation(
                    rule_id="ART-COMP-001",
                    table="artifact",
                    severity=Severity.CRITICAL,
                    description="Project ID must not be null",
                    count=null_proj,
                )
            )

        # ART-COMP-002: Task ID must not be null
        null_task = self._get_count(
            "SELECT COUNT(*) FROM artifact WHERE task_id IS NULL"
        )
        if null_task > 0:
            violations.append(
                DQViolation(
                    rule_id="ART-COMP-002",
                    table="artifact",
                    severity=Severity.CRITICAL,
                    description="Task ID must not be null",
                    count=null_task,
                )
            )

        # ART-COMP-003: Agent ID must not be null
        null_agent = self._get_count(
            "SELECT COUNT(*) FROM artifact WHERE agent_id IS NULL"
        )
        if null_agent > 0:
            violations.append(
                DQViolation(
                    rule_id="ART-COMP-003",
                    table="artifact",
                    severity=Severity.CRITICAL,
                    description="Agent ID must not be null",
                    count=null_agent,
                )
            )

        # Timeliness Rules
        # ART-TIME-001: created_at must not be in the future
        future_created = self._get_count(
            "SELECT COUNT(*) FROM artifact WHERE created_at > NOW()"
        )
        if future_created > 0:
            violations.append(
                DQViolation(
                    rule_id="ART-TIME-001",
                    table="artifact",
                    severity=Severity.ERROR,
                    description="created_at must not be in the future",
                    count=future_created,
                )
            )

        # Uniqueness Rules
        # ART-UNIQ-001: Artifact ID must be unique
        dup_ids = self._get_count(
            """SELECT COUNT(*) FROM (
                SELECT id, COUNT(*) FROM artifact GROUP BY id HAVING COUNT(*) > 1
            ) sub"""
        )
        if dup_ids > 0:
            violations.append(
                DQViolation(
                    rule_id="ART-UNIQ-001",
                    table="artifact",
                    severity=Severity.CRITICAL,
                    description="Duplicate artifact IDs found",
                    count=dup_ids,
                )
            )

        # Accuracy Rules
        # ART-ACCU-001: check_status must be valid enum value
        valid_statuses = ("pending", "passed", "failed")
        invalid_status = self._get_count(
            f"SELECT COUNT(*) FROM artifact WHERE check_status NOT IN {valid_statuses}"
        )
        if invalid_status > 0:
            violations.append(
                DQViolation(
                    rule_id="ART-ACCU-001",
                    table="artifact",
                    severity=Severity.ERROR,
                    description="Invalid check_status value",
                    count=invalid_status,
                )
            )

        # ART-ACCU-002: Commit SHA format validation (40 hex chars if not null)
        invalid_sha = self._get_count(
            """SELECT COUNT(*) FROM artifact 
               WHERE commit_sha IS NOT NULL 
               AND LENGTH(commit_sha) != 40"""
        )
        if invalid_sha > 0:
            violations.append(
                DQViolation(
                    rule_id="ART-ACCU-002",
                    table="artifact",
                    severity=Severity.WARNING,
                    description="Invalid commit SHA format (expected 40 hex chars)",
                    count=invalid_sha,
                )
            )

        # ART-ACCU-003/004: Referential integrity
        orphan_proj = self._get_count(
            """SELECT COUNT(*) FROM artifact a
               LEFT JOIN project p ON a.project_id = p.id
               WHERE p.id IS NULL"""
        )
        if orphan_proj > 0:
            violations.append(
                DQViolation(
                    rule_id="ART-ACCU-003",
                    table="artifact",
                    severity=Severity.CRITICAL,
                    description="Artifacts with non-existent project_id",
                    count=orphan_proj,
                )
            )

        orphan_task = self._get_count(
            """SELECT COUNT(*) FROM artifact a
               LEFT JOIN task t ON a.task_id = t.id
               WHERE t.id IS NULL"""
        )
        if orphan_task > 0:
            violations.append(
                DQViolation(
                    rule_id="ART-ACCU-004",
                    table="artifact",
                    severity=Severity.CRITICAL,
                    description="Artifacts with non-existent task_id",
                    count=orphan_task,
                )
            )

        passed = len(violations) == 0
        return DQResult(
            table="artifact", passed=passed, violations=violations, total_checked=total
        )

    def validate_gate_decision(self) -> DQResult:
        """Validate gate_decision table DQ rules."""
        violations = []
        total = self._get_count("SELECT COUNT(*) FROM gate_decision")

        # Completeness Rules
        required_fields = [
            ("project_id", "GTD-COMP-001", Severity.CRITICAL),
            ("gate_rule_id", "GTD-COMP-002", Severity.CRITICAL),
            ("outcome", "GTD-COMP-003", Severity.CRITICAL),
            ("actor_id", "GTD-COMP-004", Severity.CRITICAL),
            ("reason", "GTD-COMP-005", Severity.ERROR),
        ]

        for field, rule_id, severity in required_fields:
            null_count = self._get_count(
                f"SELECT COUNT(*) FROM gate_decision WHERE {field} IS NULL"
            )
            if null_count > 0:
                violations.append(
                    DQViolation(
                        rule_id=rule_id,
                        table="gate_decision",
                        severity=severity,
                        description=f"{field} must not be null",
                        count=null_count,
                    )
                )

        # Uniqueness Rules
        # GTD-UNIQ-001: Gate decision ID must be unique
        dup_ids = self._get_count(
            """SELECT COUNT(*) FROM (
                SELECT id, COUNT(*) FROM gate_decision GROUP BY id HAVING COUNT(*) > 1
            ) sub"""
        )
        if dup_ids > 0:
            violations.append(
                DQViolation(
                    rule_id="GTD-UNIQ-001",
                    table="gate_decision",
                    severity=Severity.CRITICAL,
                    description="Duplicate gate decision IDs found",
                    count=dup_ids,
                )
            )

        # Accuracy Rules
        # GTD-ACCU-001: outcome must be valid enum value
        valid_outcomes = ("approved", "rejected", "approved_with_risk")
        invalid_outcome = self._get_count(
            f"SELECT COUNT(*) FROM gate_decision WHERE outcome NOT IN {valid_outcomes}"
        )
        if invalid_outcome > 0:
            violations.append(
                DQViolation(
                    rule_id="GTD-ACCU-001",
                    table="gate_decision",
                    severity=Severity.CRITICAL,
                    description="Invalid gate decision outcome value",
                    count=invalid_outcome,
                )
            )

        # GTD-ACCU-002: Either task_id or phase_id must be set
        missing_target = self._get_count(
            "SELECT COUNT(*) FROM gate_decision WHERE task_id IS NULL AND phase_id IS NULL"
        )
        if missing_target > 0:
            violations.append(
                DQViolation(
                    rule_id="GTD-ACCU-002",
                    table="gate_decision",
                    severity=Severity.CRITICAL,
                    description="Either task_id or phase_id must be set",
                    count=missing_target,
                )
            )

        # GTD-ACCU-003/004: Referential integrity
        orphan_proj = self._get_count(
            """SELECT COUNT(*) FROM gate_decision gd
               LEFT JOIN project p ON gd.project_id = p.id
               WHERE p.id IS NULL"""
        )
        if orphan_proj > 0:
            violations.append(
                DQViolation(
                    rule_id="GTD-ACCU-003",
                    table="gate_decision",
                    severity=Severity.CRITICAL,
                    description="Decisions with non-existent project_id",
                    count=orphan_proj,
                )
            )

        orphan_rule = self._get_count(
            """SELECT COUNT(*) FROM gate_decision gd
               LEFT JOIN gate_rule gr ON gd.gate_rule_id = gr.id
               WHERE gr.id IS NULL"""
        )
        if orphan_rule > 0:
            violations.append(
                DQViolation(
                    rule_id="GTD-ACCU-004",
                    table="gate_decision",
                    severity=Severity.CRITICAL,
                    description="Decisions with non-existent gate_rule_id",
                    count=orphan_rule,
                )
            )

        passed = len(violations) == 0
        return DQResult(
            table="gate_decision",
            passed=passed,
            violations=violations,
            total_checked=total,
        )

    def validate_all(
        self, tables: list[str] | None = None, severity_filter: str | None = None
    ) -> list[DQResult]:
        """Run all validations."""
        tables_to_validate = tables or list(self.table_specs.keys())
        rules_by_table: dict[str, list[DQRule]] = {}
        for rule in self.rules:
            rules_by_table.setdefault(rule.table, []).append(rule)

        results: list[DQResult] = []
        for table in tables_to_validate:
            if not self._table_exists(table):
                continue
            table_spec = self.table_specs.get(table)
            if table_spec is None:
                continue
            total = self._get_count(f"SELECT COUNT(*) FROM {table}")
            violations: list[DQViolation] = []
            for rule in rules_by_table.get(table, []):
                if severity_filter and (
                    self._severity_rank(rule.severity)
                    < self._severity_rank(severity_filter)
                ):
                    continue
                count = self._rule_count(rule)
                if count <= 0:
                    continue
                key_columns = table_spec.key_columns
                record_query = self._rule_record_query(rule, key_columns)
                rows = self._execute_query(f"{record_query} LIMIT {self.sample_size}")
                sample_ids = self._format_sample_ids(key_columns, rows)
                violations.append(
                    DQViolation(
                        rule_id=rule.rule_id,
                        table=rule.table,
                        severity=rule.severity,
                        description=rule.description,
                        count=count,
                        sample_ids=sample_ids,
                    )
                )

            passed = len(violations) == 0
            results.append(
                DQResult(
                    table=table,
                    passed=passed,
                    violations=violations,
                    total_checked=total,
                )
            )

        self.results = results
        return results

    def _severity_rank(self, severity: str) -> int:
        """Return numeric rank for severity comparison."""
        ranks = {Severity.WARNING: 1, Severity.ERROR: 2, Severity.CRITICAL: 3}
        return ranks.get(severity, 0)


class DQEnforcer:
    """Persists DQ violations and flags/quarantines records."""

    def __init__(self, engine: Engine, inspector, run_id: str):
        self.engine = engine
        self.inspector = inspector
        self.run_id = run_id

    def _execute(self, query: str, params: dict | None = None) -> None:
        with self.engine.begin() as conn:
            conn.execute(text(query), params or {})

    def ensure_support_tables(self) -> None:
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS dq_violations (
                id TEXT PRIMARY KEY,
                run_id UUID NOT NULL,
                table_name TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                kind TEXT NOT NULL,
                description TEXT NOT NULL,
                violation_count INTEGER NOT NULL,
                total_checked INTEGER NOT NULL,
                sample_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                detected_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS dq_record_flags (
                id TEXT PRIMARY KEY,
                run_id UUID NOT NULL,
                table_name TEXT NOT NULL,
                record_key JSONB NOT NULL,
                rule_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                kind TEXT NOT NULL,
                reason TEXT NOT NULL,
                flagged_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        self._execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_dq_record_flags
            ON dq_record_flags(run_id, table_name, record_key, rule_id);
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS dq_quarantine (
                id TEXT PRIMARY KEY,
                run_id UUID NOT NULL,
                table_name TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                kind TEXT NOT NULL,
                reason TEXT NOT NULL,
                violation_ratio NUMERIC NOT NULL,
                quarantined_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
        self._execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_dq_quarantine
            ON dq_quarantine(run_id, table_name, rule_id);
            """
        )

    def record_violation(
        self,
        *,
        rule: DQRule,
        result: DQResult,
        violation: DQViolation,
    ) -> None:
        self._execute(
            """
            INSERT INTO dq_violations (
                id,
                run_id,
                table_name,
                rule_id,
                severity,
                kind,
                description,
                violation_count,
                total_checked,
                sample_ids
            ) VALUES (
                :id,
                :run_id,
                :table_name,
                :rule_id,
                :severity,
                :kind,
                :description,
                :violation_count,
                :total_checked,
                CAST(:sample_ids AS JSONB)
            );
            """,
            {
                "id": str(uuid.uuid4()),
                "run_id": self.run_id,
                "table_name": result.table,
                "rule_id": rule.rule_id,
                "severity": rule.severity,
                "kind": rule.kind,
                "description": rule.description,
                "violation_count": violation.count,
                "total_checked": result.total_checked,
                "sample_ids": json.dumps(violation.sample_ids),
            },
        )

    def flag_records(
        self,
        *,
        rule: DQRule,
        table_spec: DQTableSpec,
        record_query: str,
    ) -> None:
        record_key_expression = (
            "jsonb_build_object("
            + ", ".join([f"'{col}', {col}" for col in table_spec.key_columns])
            + ")"
        )

        self._execute(
            f"""
            INSERT INTO dq_record_flags (
                id, run_id, table_name, record_key, rule_id, severity, kind, reason
            )
            SELECT
                :id,
                :run_id,
                :table_name,
                {record_key_expression},
                :rule_id,
                :severity,
                :kind,
                :reason
            FROM ({record_query}) dq
            ON CONFLICT DO NOTHING;
            """,
            {
                "id": str(uuid.uuid4()),
                "run_id": self.run_id,
                "table_name": table_spec.table,
                "rule_id": rule.rule_id,
                "severity": rule.severity,
                "kind": rule.kind,
                "reason": rule.description,
            },
        )

        columns = {col["name"] for col in self.inspector.get_columns(table_spec.table)}
        if rule.where_clause and {
            "dq_flagged",
            "dq_flag_reason",
            "dq_flag_severity",
        }.issubset(columns):
            self._execute(
                f"""
                UPDATE {table_spec.table}
                SET dq_flagged = true,
                    dq_flag_reason = CASE
                        WHEN dq_flag_reason IS NULL OR dq_flag_reason = '' THEN '{rule.rule_id}'
                        WHEN dq_flag_reason NOT LIKE '%{rule.rule_id}%' THEN dq_flag_reason || ',' || '{rule.rule_id}'
                        ELSE dq_flag_reason
                    END,
                    dq_flag_severity = CASE
                        WHEN dq_flag_severity = 'CRITICAL' THEN dq_flag_severity
                        WHEN dq_flag_severity = 'ERROR' AND '{rule.severity}' = 'CRITICAL' THEN '{rule.severity}'
                        WHEN dq_flag_severity = 'WARNING' AND '{rule.severity}' IN ('ERROR', 'CRITICAL') THEN '{rule.severity}'
                        WHEN dq_flag_severity IS NULL THEN '{rule.severity}'
                        ELSE dq_flag_severity
                    END
                WHERE {rule.where_clause};
                """
            )

    def quarantine_if_needed(
        self,
        *,
        rule: DQRule,
        result: DQResult,
        violation: DQViolation,
    ) -> None:
        if rule.severity != Severity.CRITICAL:
            return
        total = max(result.total_checked, 1)
        ratio = violation.count / total
        should_quarantine = ratio > 0.01 or rule.kind in {"duplicate", "referential"}
        if not should_quarantine:
            return
        reason = (
            f"{rule.rule_id} triggered quarantine: {violation.count}/{total} "
            f"({ratio:.2%})"
        )
        self._execute(
            """
            INSERT INTO dq_quarantine (
                id, run_id, table_name, rule_id, severity, kind, reason, violation_ratio
            ) VALUES (
                :id, :run_id, :table_name, :rule_id, :severity, :kind, :reason, :ratio
            )
            ON CONFLICT DO NOTHING;
            """,
            {
                "id": str(uuid.uuid4()),
                "run_id": self.run_id,
                "table_name": result.table,
                "rule_id": rule.rule_id,
                "severity": rule.severity,
                "kind": rule.kind,
                "reason": reason,
                "ratio": ratio,
            },
        )


def format_text_report(results: list[DQResult]) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append("DATA QUALITY VALIDATION REPORT")
    lines.append("=" * 80)
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")

    total_violations = 0
    critical_count = 0
    error_count = 0
    warning_count = 0
    passed_tables = 0
    failed_tables = 0

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"\n{'-' * 80}")
        lines.append(
            f"Table: {result.table:20} | Status: {status} | Records: {result.total_checked}"
        )
        lines.append("-" * 80)

        if result.violations:
            failed_tables += 1
            for v in result.violations:
                total_violations += 1
                if v.severity == Severity.CRITICAL:
                    critical_count += 1
                elif v.severity == Severity.ERROR:
                    error_count += 1
                else:
                    warning_count += 1

                lines.append(
                    f"  [{v.severity:8}] {v.rule_id:15} | Count: {v.count:5} | {v.description}"
                )
        else:
            passed_tables += 1
            lines.append("  No violations found")

    lines.append("\n" + "=" * 80)
    lines.append("SUMMARY")
    lines.append("=" * 80)
    lines.append(f"Tables Validated: {len(results)}")
    lines.append(f"Tables Passed:    {passed_tables}")
    lines.append(f"Tables Failed:    {failed_tables}")
    lines.append(f"Total Violations: {total_violations}")
    lines.append(f"  - CRITICAL: {critical_count}")
    lines.append(f"  - ERROR:    {error_count}")
    lines.append(f"  - WARNING:  {warning_count}")
    lines.append("=" * 80)

    return "\n".join(lines)


def format_json_report(results: list[DQResult]) -> str:
    """Format results as JSON."""
    data = []
    for result in results:
        data.append(
            {
                "table": result.table,
                "passed": result.passed,
                "total_checked": result.total_checked,
                "violations": [
                    {
                        "rule_id": v.rule_id,
                        "severity": v.severity,
                        "description": v.description,
                        "count": v.count,
                    }
                    for v in result.violations
                ],
            }
        )
    return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Validate data quality rules for Tascade metrics"
    )
    parser.add_argument(
        "--critical-only",
        action="store_true",
        help="Only report CRITICAL severity violations",
    )
    parser.add_argument(
        "--error-and-above",
        action="store_true",
        help="Report ERROR and CRITICAL severity violations",
    )
    parser.add_argument("--table", help="Validate specific table only")
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit with non-zero status if any ERROR or CRITICAL violations found",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit with non-zero status if any CRITICAL violations found",
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="Persist violations and flag/quarantine records",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="Number of sample record keys to include per violation",
    )

    args = parser.parse_args()

    if args.enforce and not args.fail_on_error and not args.fail_on_critical:
        args.fail_on_critical = True

    # Determine severity filter
    severity_filter = None
    if args.critical_only:
        severity_filter = Severity.CRITICAL
    elif args.error_and_above:
        severity_filter = Severity.ERROR

    # Determine tables to validate
    tables = None
    if args.table:
        tables = [args.table]

    # Setup database connection
    database_url = _database_url()
    engine = create_engine(database_url, future=True, **_engine_kwargs(database_url))

    # Run validation
    validator = DQValidator(engine, sample_size=args.sample_size)
    results = validator.validate_all(tables=tables, severity_filter=severity_filter)

    if args.enforce:
        run_id = str(uuid.uuid4())
        enforcer = DQEnforcer(engine, inspect(engine), run_id)
        enforcer.ensure_support_tables()
        rules_by_id = {rule.rule_id: rule for rule in validator.rules}
        for result in results:
            table_spec = validator.table_specs.get(result.table)
            if not table_spec:
                continue
            for violation in result.violations:
                rule = rules_by_id.get(violation.rule_id)
                if not rule:
                    continue
                record_query = validator._rule_record_query(
                    rule, table_spec.key_columns
                )
                enforcer.record_violation(rule=rule, result=result, violation=violation)
                enforcer.flag_records(
                    rule=rule,
                    table_spec=table_spec,
                    record_query=record_query,
                )
                enforcer.quarantine_if_needed(
                    rule=rule, result=result, violation=violation
                )

    # Output report
    if args.format == "json":
        print(format_json_report(results))
    else:
        print(format_text_report(results))

    # Determine exit status
    has_critical = any(
        any(v.severity == Severity.CRITICAL for v in r.violations) for r in results
    )
    has_error = any(
        any(v.severity in (Severity.ERROR, Severity.CRITICAL) for v in r.violations)
        for r in results
    )

    if args.fail_on_critical and has_critical:
        sys.exit(1)
    if args.fail_on_error and has_error:
        sys.exit(1)

    # Implicit strictness for enforcement mode
    if args.enforce and has_error:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
