from pathlib import Path

import pytest

from app.cli.config import Config, ConfigError, load_config


def test_env_overrides_file(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text('url = "http://file:1"\napi_key = "k_file"\n')
    cfg = load_config(env={"TASCADE_URL": "http://env:2"}, path=p)
    assert cfg.url == "http://env:2"
    assert cfg.api_key == "k_file"


def test_flag_overrides_env(tmp_path: Path) -> None:
    cfg = load_config(
        url="http://flag:3", env={"TASCADE_URL": "http://env:2"}, path=tmp_path / "missing.toml"
    )
    assert cfg.url == "http://flag:3"


def test_env_api_key_overrides_file(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text('api_key = "k_file"\n')
    cfg = load_config(env={"TASCADE_API_KEY": "k_env"}, path=p)
    assert cfg.api_key == "k_env"


def test_default_when_nothing_set(tmp_path: Path) -> None:
    cfg = load_config(env={}, path=tmp_path / "missing.toml")
    assert cfg.url == "http://127.0.0.1:8010"
    assert cfg.api_key is None


def test_default_table_form(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text('[default]\nurl = "http://table:4"\napi_key = "k_table"\n')
    cfg = load_config(env={}, path=p)
    assert cfg.url == "http://table:4"
    assert cfg.api_key == "k_table"


def test_top_level_wins_over_default_table(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text('url = "http://top:5"\n[default]\nurl = "http://table:4"\n')
    assert load_config(env={}, path=p).url == "http://top:5"


def test_trailing_slash_stripped(tmp_path: Path) -> None:
    cfg = load_config(url="http://x:1/", env={}, path=tmp_path / "missing.toml")
    assert cfg.url == "http://x:1"


def test_malformed_file_raises_config_error(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text("this is not = valid = toml\n")
    with pytest.raises(ConfigError) as exc:
        load_config(env={}, path=p)
    assert str(p) in str(exc.value)


def test_config_is_a_plain_value() -> None:
    assert Config(url="http://x", api_key=None).api_key is None
