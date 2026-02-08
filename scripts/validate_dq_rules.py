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


class DQValidator:
    """Validates data quality rules against Tascade tables."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.inspector = inspect(engine)
        self.results: list[DQResult] = []
        self.now = datetime.now(timezone.utc)

    def _execute_query(self, query: str, params: dict | None = None) -> list[Any]:
        """Execute a query and return results."""
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            return result.fetchall()

    def _get_count(self, query: str, params: dict | None = None) -> int:
        """Execute a count query and return the result."""
        rows = self._execute_query(query, params)
        return rows[0][0] if rows else 0

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
        validators = {
            "project": self.validate_project,
            "task": self.validate_task,
            "dependency_edge": self.validate_dependency_edge,
            "lease": self.validate_lease,
            "artifact": self.validate_artifact,
            "gate_decision": self.validate_gate_decision,
        }

        tables_to_validate = tables or list(validators.keys())
        results = []

        for table in tables_to_validate:
            if table in validators:
                result = validators[table]()
                if severity_filter:
                    result.violations = [
                        v
                        for v in result.violations
                        if self._severity_rank(v.severity)
                        >= self._severity_rank(severity_filter)
                    ]
                    result.passed = len(result.violations) == 0
                results.append(result)

        self.results = results
        return results

    def _severity_rank(self, severity: str) -> int:
        """Return numeric rank for severity comparison."""
        ranks = {Severity.WARNING: 1, Severity.ERROR: 2, Severity.CRITICAL: 3}
        return ranks.get(severity, 0)


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

    args = parser.parse_args()

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
    validator = DQValidator(engine)
    results = validator.validate_all(tables=tables, severity_filter=severity_filter)

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

    sys.exit(0)


if __name__ == "__main__":
    main()
