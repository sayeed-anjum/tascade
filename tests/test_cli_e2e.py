"""The CLI driven end to end against the real API through a TestClient transport."""

import json

import pytest
from fastapi.testclient import TestClient

from app.cli.main import main
from app.main import app


@pytest.fixture()
def transport():
    """Adapt the CLI's transport contract onto a FastAPI TestClient."""
    client = TestClient(app)

    def _transport(method, url, headers, body):
        path = url.removeprefix("http://127.0.0.1:8010")
        response = client.request(method, path, headers=headers, content=body)
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
