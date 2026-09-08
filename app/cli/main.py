"""``tascade`` command-line entry point.

Argparse is built from the declarative table in :mod:`app.cli.commands`, so the
CLI surface and the MCP parity test share one source of truth.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.cli.client import ApiClient, ApiError, TransportError
from app.cli.commands import (
    COMMANDS,
    KIND_BOOL,
    KIND_INT,
    KIND_JSON,
    KIND_LIST,
    LOC_BODY,
    LOC_PATH,
    LOC_QUERY,
    Arg,
    Command,
)
from app.cli.config import ConfigError, load_config
from app.cli.render import render

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2

SKILL_FILENAME = "cli-skill.md"


def _skill_path() -> Path:
    """Locate docs/cli-skill.md relative to the installed package."""
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "docs" / SKILL_FILENAME


def _add_argument(parser: argparse.ArgumentParser, arg: Arg) -> None:
    if arg.location == LOC_PATH:
        parser.add_argument(arg.dest, help=arg.help)
        return

    kwargs: dict[str, Any] = {"dest": arg.dest, "help": arg.help, "required": arg.required}
    if arg.kind == KIND_BOOL:
        # A boolean flag is absent by default so the server's own default applies.
        kwargs.pop("required")
        parser.add_argument(arg.name, action="store_true", default=None, **kwargs)
        return
    if arg.kind == KIND_LIST:
        parser.add_argument(arg.name, action="append", default=None, **kwargs)
        return
    if arg.kind == KIND_INT:
        parser.add_argument(arg.name, type=int, default=None, **kwargs)
        return
    parser.add_argument(arg.name, default=None, **kwargs)


def _attach(parser: argparse.ArgumentParser, command: Command) -> None:
    for arg in command.args:
        _add_argument(parser, arg)
    parser.add_argument(
        "--json",
        dest="json",
        action="store_true",
        help="Print the raw JSON response instead of a summary.",
    )
    parser.set_defaults(_command=command)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tascade",
        description="Thin client for the Tascade control-plane API.",
    )
    parser.add_argument("--url", dest="url", default=None, help="API endpoint; overrides config.")
    parser.add_argument(
        "--api-key", dest="api_key", default=None, help="API key; overrides config."
    )
    parser.add_argument(
        "--skill",
        action="store_true",
        help="Print the agent skill file describing every subcommand.",
    )
    parser.set_defaults(_command=None, json=False)

    top = parser.add_subparsers(dest="_group", metavar="<group>")
    groups: dict[str, Any] = {}

    for command in COMMANDS:
        if len(command.path) == 1:
            _attach(top.add_parser(command.path[0], help=command.help), command)
            continue

        group_name, leaf = command.path
        if group_name not in groups:
            group_parser = top.add_parser(group_name, help=f"{group_name} commands")
            groups[group_name] = group_parser.add_subparsers(
                dest=f"_{group_name}_command", metavar="<command>"
            )
        _attach(groups[group_name].add_parser(leaf, help=command.help), command)

    return parser


def _value_for(arg: Arg, namespace: argparse.Namespace) -> Any:
    value = getattr(namespace, arg.dest, None)
    if value is None:
        return None
    if arg.kind == KIND_JSON:
        return json.loads(value)
    return value


def _split_arguments(command: Command, namespace: argparse.Namespace) -> tuple[str, dict, dict]:
    path_values: dict[str, Any] = {}
    query: dict[str, Any] = {}
    body: dict[str, Any] = {}

    for arg in command.args:
        value = _value_for(arg, namespace)
        if arg.location == LOC_PATH:
            path_values[arg.dest] = value
        elif value is None:
            continue
        elif arg.location == LOC_QUERY:
            query[arg.dest] = value
        elif arg.location == LOC_BODY:
            body[arg.dest] = value

    url = command.url.format(**path_values)
    return url, query, (body if command.method != "GET" else {})


def run(command: Command, namespace: argparse.Namespace, transport=None) -> int:
    config = load_config(url=namespace.url, api_key=namespace.api_key)
    client = ApiClient(config, transport=transport)
    url, query, body = _split_arguments(command, namespace)
    result = client.request(
        command.method, url, query=query, body=body if command.method != "GET" else None
    )
    print(json.dumps(result, indent=2, default=str) if namespace.json else render(result))
    return EXIT_OK


def main(argv: list[str] | None = None, transport=None) -> int:
    parser = build_parser()
    namespace = parser.parse_args(argv)

    if getattr(namespace, "skill", False):
        path = _skill_path()
        if not path.exists():
            print(f"error: skill file not found at {path}", file=sys.stderr)
            return EXIT_ERROR
        print(path.read_text(), end="")
        return EXIT_OK

    command: Command | None = getattr(namespace, "_command", None)
    if command is None:
        parser.print_help()
        return EXIT_USAGE

    try:
        return run(command, namespace, transport=transport)
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON argument: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except TransportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except ApiError as exc:
        print(f"error: {exc.code}: {exc.message}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
