"""Endpoint and API key resolution for the ``tascade`` CLI.

Precedence, highest first: explicit command-line flag, environment variable,
config file, built-in default.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_URL = "http://127.0.0.1:8010"
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "tascade" / "config.toml"

ENV_URL = "TASCADE_URL"
ENV_API_KEY = "TASCADE_API_KEY"


class ConfigError(Exception):
    """The config file exists but could not be read."""


@dataclass(frozen=True)
class Config:
    url: str
    api_key: str | None


def _read_file(path: Path) -> dict[str, object]:
    """Return the config file's values, or an empty mapping when it is absent.

    Top-level keys win over the equivalent keys in a ``[default]`` table, so a
    file may use either shape.
    """
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise ConfigError(f"could not read config file {path}: {exc}") from exc

    values: dict[str, object] = {}
    default_table = data.get("default")
    if isinstance(default_table, dict):
        values.update(default_table)
    values.update({k: v for k, v in data.items() if not isinstance(v, dict)})
    return values


def _first(*candidates: object) -> str | None:
    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def load_config(
    url: str | None = None,
    api_key: str | None = None,
    env: Mapping[str, str] | None = None,
    path: Path | None = None,
) -> Config:
    env = os.environ if env is None else env
    path = DEFAULT_CONFIG_PATH if path is None else path
    file_values = _read_file(path)

    resolved_url = _first(url, env.get(ENV_URL), file_values.get("url")) or DEFAULT_URL
    resolved_key = _first(api_key, env.get(ENV_API_KEY), file_values.get("api_key"))
    return Config(url=resolved_url.rstrip("/"), api_key=resolved_key)
