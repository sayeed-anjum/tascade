"""Command table shape, MCP parity, and the thin-client boundary."""

from pathlib import Path

import pytest

from app.cli.commands import COMMANDS, Arg, Command, find_command
from app.cli.main import build_parser, main
from app.mcp_server import MCP_TOOL_NAMES

CLI_ROOT = Path(__file__).resolve().parents[1] / "app" / "cli"


def _covered_tools() -> set[str]:
    return {command.mcp_tool for command in COMMANDS if command.mcp_tool}


class TestMcpParity:
    def test_every_mcp_tool_has_a_cli_command(self):
        missing = set(MCP_TOOL_NAMES) - _covered_tools()
        assert missing == set(), f"MCP tools with no CLI subcommand: {sorted(missing)}"

    def test_no_command_claims_an_unknown_mcp_tool(self):
        unknown = _covered_tools() - set(MCP_TOOL_NAMES)
        assert unknown == set(), f"CLI commands naming a non-existent MCP tool: {sorted(unknown)}"

    def test_mcp_tool_mapping_is_one_to_one(self):
        tools = [command.mcp_tool for command in COMMANDS if command.mcp_tool]
        assert len(tools) == len(set(tools))


class TestCommandTable:
    def test_command_paths_are_unique(self):
        paths = [command.path for command in COMMANDS]
        assert len(paths) == len(set(paths))

    def test_every_command_has_help_text(self):
        assert all(command.help for command in COMMANDS)

    def test_every_path_argument_appears_in_the_url_template(self):
        for command in COMMANDS:
            for arg in command.args:
                if arg.location == "path":
                    assert "{" + arg.dest + "}" in command.url, command.path

    def test_every_url_placeholder_has_a_path_argument(self):
        for command in COMMANDS:
            placeholders = {
                piece.split("}")[0] for piece in command.url.split("{")[1:]
            }
            path_args = {arg.dest for arg in command.args if arg.location == "path"}
            assert placeholders == path_args, command.path

    def test_get_commands_send_no_body_arguments(self):
        for command in COMMANDS:
            if command.method == "GET":
                assert all(arg.location != "body" for arg in command.args), command.path

    def test_find_command_resolves_a_path(self):
        assert find_command(("tasks", "claim")).mcp_tool == "claim_task"

    def test_find_command_returns_none_for_unknown_path(self):
        assert find_command(("tasks", "nope")) is None


def _minimal_argv(command: Command) -> list[str]:
    argv: list[str] = list(command.path)
    for arg in command.args:
        if not arg.required:
            continue
        if arg.location == "path":
            argv.append("value")
        elif arg.kind == "json":
            argv.extend([arg.name, "{}"])
        elif arg.kind == "int":
            argv.extend([arg.name, "0"])
        else:
            argv.extend([arg.name, "value"])
    return argv


class TestParser:
    def test_every_command_is_reachable_and_accepts_json(self):
        parser = build_parser()
        for command in COMMANDS:
            namespace = parser.parse_args([*_minimal_argv(command), "--json"])
            assert namespace.json is True, command.path
            assert namespace._command is command, command.path

    def test_json_defaults_to_false(self):
        parser = build_parser()
        namespace = parser.parse_args(_minimal_argv(find_command(("projects", "list"))))
        assert namespace.json is False

    def test_global_url_and_api_key_flags_exist(self):
        parser = build_parser()
        namespace = parser.parse_args(
            ["--url", "http://x:1", "--api-key", "k", *_minimal_argv(find_command(("projects", "list")))]
        )
        assert namespace.url == "http://x:1"
        assert namespace.api_key == "k"

    def test_missing_required_argument_is_a_usage_error(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["tasks", "claim", "task-1"])


class TestThinClientBoundary:
    def test_cli_never_imports_the_server_side(self):
        source = "\n".join(path.read_text() for path in sorted(CLI_ROOT.glob("*.py")))
        for banned in ("app.store", "app.mcp_tools", "app.main", "sqlalchemy", "fastapi"):
            assert banned not in source, f"{banned} must not be imported by the CLI"


class TestSkillFlag:
    def test_skill_flag_prints_the_skill_file(self, capsys):
        assert main(["--skill"]) == 0
        out = capsys.readouterr().out
        assert "tascade tasks claim" in out

    def test_skill_file_documents_every_command_path(self):
        text = (Path(__file__).resolve().parents[1] / "docs" / "cli-skill.md").read_text()
        for command in COMMANDS:
            invocation = " ".join(("tascade", *command.path))
            assert invocation in text, f"docs/cli-skill.md does not document: {invocation}"


class TestBooleanAndListEncoding:
    """Flags whose sense or shape differs from a plain repeated string."""

    def test_exclude_completed_turns_the_graph_filter_off(self):
        from app.cli.main import _split_arguments

        command = find_command(("projects", "graph"))
        parser = build_parser()
        namespace = parser.parse_args(["projects", "graph", "p1", "--exclude-completed"])
        _, query, _ = _split_arguments(command, namespace)
        assert query["include_completed"] is False

    def test_graph_filter_is_absent_when_the_flag_is_not_given(self):
        from app.cli.main import _split_arguments

        command = find_command(("projects", "graph"))
        namespace = build_parser().parse_args(["projects", "graph", "p1"])
        _, query, _ = _split_arguments(command, namespace)
        assert "include_completed" not in query

    def test_inactive_flag_creates_a_disabled_rule(self):
        from app.cli.main import _split_arguments

        command = find_command(("gates", "rule-create"))
        namespace = build_parser().parse_args(
            ["gates", "rule-create", "--project-id", "p", "--name", "n", "--inactive"]
        )
        _, _, body = _split_arguments(command, namespace)
        assert body["is_active"] is False

    def test_repeated_capabilities_are_sent_as_one_comma_delimited_value(self):
        from app.cli.main import _split_arguments

        command = find_command(("tasks", "ready"))
        namespace = build_parser().parse_args(
            [
                "tasks", "ready", "--project-id", "p", "--agent-id", "a",
                "--capability", "python", "--capability", "go",
            ]
        )
        _, query, _ = _split_arguments(command, namespace)
        assert query["capabilities"] == "python,go"


class TestArgumentsMatchTheServerContract:
    """Arguments whose names or requiredness must match the request schemas."""

    def test_gate_decision_sends_the_field_names_the_schema_expects(self):
        from app.cli.main import _split_arguments

        command = find_command(("gates", "decision-create"))
        namespace = build_parser().parse_args(
            [
                "gates", "decision-create", "--project-id", "p",
                "--gate-rule-id", "r", "--outcome", "approved",
                "--actor-id", "reviewer-1", "--reason", "looks good",
            ]
        )
        _, _, body = _split_arguments(command, namespace)
        assert body["actor_id"] == "reviewer-1"
        assert body["reason"] == "looks good"
        assert "decided_by" not in body and "rationale" not in body

    def test_gate_decision_requires_the_fields_the_schema_requires(self):
        required = {
            arg.dest for arg in find_command(("gates", "decision-create")).args if arg.required
        }
        assert {"project_id", "gate_rule_id", "outcome", "actor_id", "reason"} <= required

    def test_task_state_reason_is_required(self):
        reason = next(
            arg for arg in find_command(("tasks", "state")).args if arg.dest == "reason"
        )
        assert reason.required, "the server rejects a transition with no reason"

    def test_integration_result_help_names_the_real_outcomes(self):
        result = next(
            arg for arg in find_command(("tasks", "integrations-result")).args
            if arg.dest == "result"
        )
        assert "failed_checks" in result.help
        assert "failure" not in result.help


class TestGroupHelp:
    def test_bare_group_prints_that_group_and_not_the_top_level(self, capsys):
        assert main(["tasks"]) == 2
        out = capsys.readouterr().out
        assert "artifacts-create" in out, "expected the tasks group's own commands"
        assert "milestones" not in out, "printed the top-level help instead"

    def test_bare_invocation_still_prints_the_top_level_help(self, capsys):
        assert main([]) == 2
        assert "milestones" in capsys.readouterr().out


class TestSkillFileAccuracy:
    def test_skill_file_does_not_name_a_nonexistent_integration_result(self):
        from pathlib import Path

        text = (Path(__file__).resolve().parents[1] / "docs" / "cli-skill.md").read_text()
        assert "failed_checks" in text
        assert "success|conflict|failure" not in text


class TestPackagedSkillFile:
    """The skill file ships inside the package and is read from there once installed."""

    def test_the_packaged_copy_matches_the_documented_one(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        packaged = root / "app" / "cli" / "cli-skill.md"
        documented = root / "docs" / "cli-skill.md"
        assert packaged.exists(), "the skill file must ship inside the package"
        assert packaged.read_text() == documented.read_text(), (
            "app/cli/cli-skill.md and docs/cli-skill.md have drifted"
        )

    def test_skill_lookup_prefers_the_packaged_copy(self):
        from app.cli.main import _skill_path

        assert _skill_path() == Path(__file__).resolve().parents[1] / "app" / "cli" / "cli-skill.md"

    def test_skill_lookup_reports_absence_instead_of_raising(self, monkeypatch, capsys):
        import app.cli.main as cli_main

        monkeypatch.setattr(cli_main, "_skill_path", lambda: None)
        assert cli_main.main(["--skill"]) == 1
        assert "not found" in capsys.readouterr().err

    def test_package_data_declares_the_skill_file(self):
        import tomllib
        from pathlib import Path

        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        with pyproject.open("rb") as handle:
            config = tomllib.load(handle)
        assert config["build-system"]["build-backend"] == "setuptools.build_meta"
        assert config["tool"]["setuptools"]["package-data"]["app.cli"] == ["cli-skill.md"]
        assert config["project"]["scripts"]["tascade"] == "app.cli.main:main"
