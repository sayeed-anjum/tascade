"""The CLI driven end to end against the real API through a TestClient transport."""

import json
from urllib.parse import urlsplit, urlunsplit

import pytest
from fastapi.testclient import TestClient

from app.cli.main import main
from app.main import app


@pytest.fixture()
def transport():
    """Adapt the CLI's transport contract onto a FastAPI TestClient."""
    client = TestClient(app)

    def _transport(method, url, headers, body):
        # Route on the path and query alone, so the test does not depend on
        # which base URL the CLI resolved.
        parts = urlsplit(url)
        target = urlunsplit(("", "", parts.path, parts.query, ""))
        response = client.request(method, target, headers=headers, content=body)
        return response.status_code, response.content

    return _transport


@pytest.fixture()
def cli(transport, capsys):
    def _run(*argv, expect: int = 0):
        code = main([*argv, "--json"], transport=transport)
        out = capsys.readouterr().out
        assert code == expect, out
        return json.loads(out) if out.strip() else None

    return _run


@pytest.fixture()
def cli_text(transport, capsys):
    def _run(*argv, expect: int = 0):
        code = main(list(argv), transport=transport)
        captured = capsys.readouterr()
        assert code == expect, captured.err
        return captured.out + captured.err

    return _run


class TestWorkerLoop:
    def test_project_phase_milestone_task_flow(self, cli):
        project = cli("projects", "create", "--name", "Demo")
        phase = cli(
            "phases", "create", "--project-id", project["id"], "--name", "P", "--sequence", "0"
        )
        assert phase["short_id"] == "P1"

        milestone = cli(
            "milestones", "create",
            "--project-id", project["id"], "--phase-id", phase["id"],
            "--name", "M", "--sequence", "0",
        )
        assert milestone["short_id"] == "P1.M1"

        task = cli(
            "tasks", "create",
            "--project-id", project["id"], "--milestone-id", milestone["id"],
            "--title", "Build the CLI", "--task-class", "backend",
            "--work-spec", '{"objective": "o", "acceptance_criteria": ["a"]}',
            "--capability-tag", "python",
        )
        assert task["short_id"] == "P1.M1.T1"
        assert task["capability_tags"] == ["python"]

        assert cli("tasks", "get", task["id"])["id"] == task["id"]

        ready = cli(
            "tasks", "ready",
            "--project-id", project["id"], "--agent-id", "a1", "--capability", "python",
        )
        assert [item["id"] for item in ready["items"]] == [task["id"]]

        claimed = cli(
            "tasks", "claim", task["id"], "--project-id", project["id"], "--agent-id", "a1"
        )
        assert claimed["task"]["state"] == "claimed"
        lease_token = claimed["lease"]["token"]

        beat = cli(
            "tasks", "heartbeat", task["id"],
            "--project-id", project["id"], "--agent-id", "a1", "--lease-token", lease_token,
        )
        assert beat["lease_expires_at"]

        moved = cli(
            "tasks", "state", task["id"],
            "--project-id", project["id"], "--new-state", "in_progress",
            "--actor-id", "a1", "--reason", "starting",
        )
        assert moved["task"]["state"] == "in_progress"

        artifact = cli(
            "tasks", "artifacts-create", task["id"],
            "--project-id", project["id"], "--agent-id", "a1",
            "--branch", "task/demo", "--commit-sha", "abc123",
            "--check-status", "passed", "--touched-file", "app/cli/main.py",
        )
        assert artifact["branch"] == "task/demo"
        assert artifact["touched_files"] == ["app/cli/main.py"]

        listed = cli("tasks", "artifacts-list", task["id"], "--project-id", project["id"])
        assert len(listed["items"]) == 1

        implemented = cli(
            "tasks", "state", task["id"],
            "--project-id", project["id"], "--new-state", "implemented",
            "--actor-id", "a1", "--reason", "handoff summary",
        )
        assert implemented["task"]["state"] == "implemented"


class TestOtherSurfaces:
    def test_dependencies_graph_and_context(self, cli):
        project = cli("projects", "create", "--name", "Graph")
        phase = cli(
            "phases", "create", "--project-id", project["id"], "--name", "P", "--sequence", "0"
        )
        milestone = cli(
            "milestones", "create",
            "--project-id", project["id"], "--phase-id", phase["id"],
            "--name", "M", "--sequence", "0",
        )

        def _task(title):
            return cli(
                "tasks", "create",
                "--project-id", project["id"], "--milestone-id", milestone["id"],
                "--title", title, "--task-class", "backend",
                "--work-spec", '{"objective": "o", "acceptance_criteria": ["a"]}',
            )

        upstream, downstream = _task("Upstream"), _task("Downstream")
        edge = cli(
            "deps", "create",
            "--project-id", project["id"],
            "--from-task-id", upstream["id"], "--to-task-id", downstream["id"],
            "--unlock-on", "implemented",
        )
        assert edge["unlock_on"] == "implemented"

        context = cli("tasks", "context", upstream["id"], "--project-id", project["id"])
        assert [item["id"] for item in context["dependents"]] == [downstream["id"]]

        graph = cli("projects", "graph", project["id"])
        assert len(graph["tasks"]) == 2

        assert cli("tasks", "list", "--project-id", project["id"])["total"] == 2
        assert cli("tasks", "list", "--project-id", project["id"], "--state", "ready")["total"] == 2
        assert len(cli("projects", "list")["items"]) >= 1

    def test_gates_and_plans(self, cli):
        project = cli("projects", "create", "--name", "Gates")
        rule = cli(
            "gates", "rule-create",
            "--project-id", project["id"], "--name", "review",
            "--required-reviewer-role", "reviewer",
        )
        assert rule["required_reviewer_roles"] == ["reviewer"]

        evaluated = cli(
            "gates", "evaluate", "--project-id", project["id"], "--actor-id", "a1"
        )
        assert "evaluated" in evaluated

        assert cli("gates", "decisions-list", "--project-id", project["id"])["items"] == []
        assert "items" in cli("gates", "checkpoints", "--project-id", project["id"])

        changeset = cli(
            "plans", "changeset-create",
            "--project-id", project["id"],
            "--base-plan-version", "1", "--target-plan-version", "2",
            "--operations", "[]", "--created-by", "a1",
        )
        applied = cli("plans", "changeset-apply", changeset["id"])
        assert applied["changeset"]["id"] == changeset["id"]

    def test_assign_and_integration_attempts(self, cli):
        project = cli("projects", "create", "--name", "Assign")
        phase = cli(
            "phases", "create", "--project-id", project["id"], "--name", "P", "--sequence", "0"
        )
        milestone = cli(
            "milestones", "create",
            "--project-id", project["id"], "--phase-id", phase["id"],
            "--name", "M", "--sequence", "0",
        )
        task = cli(
            "tasks", "create",
            "--project-id", project["id"], "--milestone-id", milestone["id"],
            "--title", "T", "--task-class", "backend",
            "--work-spec", '{"objective": "o", "acceptance_criteria": ["a"]}',
        )

        reservation = cli(
            "tasks", "assign", task["id"],
            "--project-id", project["id"],
            "--assignee-agent-id", "a2", "--created-by", "orchestrator",
        )
        assert reservation["assignee_agent_id"] == "a2"

        attempt = cli(
            "tasks", "integrations-enqueue", task["id"],
            "--project-id", project["id"], "--base-sha", "aaa", "--head-sha", "bbb",
        )
        result = cli(
            "tasks", "integrations-result", attempt["id"],
            "--project-id", project["id"], "--result", "success",
        )
        assert result["result"] == "success"
        assert len(
            cli("tasks", "integrations-list", task["id"], "--project-id", project["id"])["items"]
        ) == 1

    def test_instructions(self, cli):
        assert "Tascade" in cli("instructions")["instructions"]


class TestOutputAndErrors:
    def test_human_output_is_not_json(self, cli_text):
        out = cli_text("projects", "create", "--name", "Human")
        assert not out.strip().startswith("{")
        assert "Human" in out

    def test_json_flag_emits_parseable_json(self, cli):
        assert cli("projects", "create", "--name", "Json")["name"] == "Json"

    def test_api_error_exits_one_and_reports_the_code(self, cli_text):
        out = cli_text(
            "tasks", "get", "00000000-0000-0000-0000-000000000000", expect=1
        )
        assert "TASK_NOT_FOUND" in out

    def test_invalid_json_argument_is_a_usage_error(self, cli_text):
        out = cli_text(
            "tasks", "create",
            "--project-id", "p", "--milestone-id", "m", "--title", "t",
            "--task-class", "backend", "--work-spec", "not json",
            expect=2,
        )
        assert "invalid JSON" in out

    def test_no_subcommand_prints_help(self, cli_text):
        assert "usage: tascade" in cli_text(expect=2)


class TestHermeticConfig:
    """The CLI tests must not read the developer's environment or user config.

    Without the ``isolated_cli_config`` fixture in conftest, a real
    TASCADE_API_KEY in the environment is sent as an Authorization header by
    every CLI test, and a real ~/.config/tascade/config.toml changes the
    endpoint under test. Run this file with those set to see the difference.
    """

    def test_the_environment_overrides_are_cleared(self):
        import os

        assert "TASCADE_URL" not in os.environ
        assert "TASCADE_API_KEY" not in os.environ

    def test_the_user_config_file_is_out_of_reach(self):
        from app.cli import config as config_module

        assert not config_module.DEFAULT_CONFIG_PATH.exists()
        assert "/.config/tascade/" not in str(config_module.DEFAULT_CONFIG_PATH)

    def test_resolved_config_is_the_built_in_default(self):
        from app.cli.config import DEFAULT_URL, load_config

        config = load_config()
        assert config.url == DEFAULT_URL
        assert config.api_key is None

    def test_no_authorization_header_is_sent(self, capsys):
        seen: dict = {}

        def transport(method, url, headers, body):
            seen.update(headers=headers, url=url)
            return 200, b'{"items": []}'

        assert main(["projects", "list", "--json"], transport=transport) == 0
        capsys.readouterr()
        assert "Authorization" not in seen["headers"]
        assert seen["url"] == "http://127.0.0.1:8010/v1/projects"

    def test_transport_routes_on_the_path_whatever_the_base_url(self, cli):
        """The e2e transport must not depend on a hardcoded base URL."""
        assert cli("projects", "list") is not None


class TestGateDecisionEndToEnd:
    """Finding 2: `gates decision-create` 422'd on every invocation, untested."""

    def _project_with_rule(self, cli):
        project = cli("projects", "create", "--name", "Gate decisions")
        rule = cli(
            "gates", "rule-create",
            "--project-id", project["id"], "--name", "review-gate",
        )
        phase = cli(
            "phases", "create", "--project-id", project["id"], "--name", "P", "--sequence", "0"
        )
        # The server requires a decision to reference a task or a phase.
        return project, rule, phase

    def test_decision_create_is_accepted_by_the_server(self, cli):
        project, rule, phase = self._project_with_rule(cli)
        decision = cli(
            "gates", "decision-create",
            "--project-id", project["id"], "--gate-rule-id", rule["id"],
            "--phase-id", phase["id"],
            "--outcome", "approved", "--actor-id", "reviewer-1",
            "--reason", "criteria met", "--evidence-ref", "pytest: 334 passed",
        )
        assert decision["outcome"] == "approved"
        assert decision["gate_rule_id"] == rule["id"]

    def test_the_decision_is_then_listed(self, cli):
        project, rule, phase = self._project_with_rule(cli)
        cli(
            "gates", "decision-create",
            "--project-id", project["id"], "--gate-rule-id", rule["id"],
            "--phase-id", phase["id"],
            "--outcome", "approved_with_risk", "--actor-id", "reviewer-1",
            "--reason", "accepted with risk",
        )
        listed = cli("gates", "decisions-list", "--project-id", project["id"])
        assert len(listed["items"]) == 1
        assert listed["items"][0]["outcome"] == "approved_with_risk"


class TestIntegrationResultOutcome:
    """Finding 5: the third outcome is failed_checks, not failure."""

    def _attempt(self, cli):
        project = cli("projects", "create", "--name", "Outcomes")
        phase = cli(
            "phases", "create", "--project-id", project["id"], "--name", "P", "--sequence", "0"
        )
        milestone = cli(
            "milestones", "create",
            "--project-id", project["id"], "--phase-id", phase["id"],
            "--name", "M", "--sequence", "0",
        )
        task = cli(
            "tasks", "create",
            "--project-id", project["id"], "--milestone-id", milestone["id"],
            "--title", "T", "--task-class", "backend",
            "--work-spec", '{"objective": "o", "acceptance_criteria": ["a"]}',
        )
        attempt = cli(
            "tasks", "integrations-enqueue", task["id"], "--project-id", project["id"]
        )
        return project, attempt

    def test_failed_checks_is_accepted(self, cli):
        project, attempt = self._attempt(cli)
        result = cli(
            "tasks", "integrations-result", attempt["id"],
            "--project-id", project["id"], "--result", "failed_checks",
        )
        assert result["result"] == "failed_checks"

    def test_the_old_wrong_value_is_rejected(self, cli_text):
        out = cli_text(
            "tasks", "integrations-result", "some-id",
            "--project-id", "p", "--result", "failure", expect=1,
        )
        assert "HTTP_422" in out or "422" in out


class TestStateReasonIsRequired:
    """Finding 4: --reason is required server-side."""

    def test_omitting_reason_is_a_usage_error_not_a_server_422(self, capsys):
        import pytest as _pytest

        from app.cli.main import build_parser

        with _pytest.raises(SystemExit) as exc:
            build_parser().parse_args(
                ["tasks", "state", "t1", "--project-id", "p",
                 "--new-state", "in_progress", "--actor-id", "a"]
            )
        assert exc.value.code == 2
        assert "--reason" in capsys.readouterr().err
