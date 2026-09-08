"""Every declared dependency must carry an upper bound.

CI was red from 2026-02 because `mcp>=1.13.0` had no upper bound: upstream
shipped 2.x, the class `app/mcp_server.py` imported was renamed, and every
fresh `pip install -e ".[dev]"` picked up the break. Lower bounds alone say
what the code needs; only an upper bound stops an unreviewed major from
arriving. This test makes the omission impossible to reintroduce quietly.

The bound is not required to be tight. It has to exist and it has to exclude
some future release, so adopting a major is a deliberate edit here.
"""

import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"

# Specifier operators that put a ceiling on what may be installed.
BOUNDING_OPERATORS = {"<", "<=", "==", "===", "~="}


def _config() -> dict:
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)


def _declared_requirements() -> list[tuple[str, str]]:
    """(group, requirement string) for runtime, every extra, and the build."""
    config = _config()
    out = [("project.dependencies", req) for req in config["project"]["dependencies"]]
    for extra, reqs in config["project"].get("optional-dependencies", {}).items():
        out.extend((f"optional-dependencies.{extra}", req) for req in reqs)
    out.extend(("build-system.requires", req) for req in config["build-system"]["requires"])
    return out


def _is_bounded(specifier: SpecifierSet) -> bool:
    return any(spec.operator in BOUNDING_OPERATORS for spec in specifier)


class TestDependencyPinning:
    def test_there_are_dependencies_to_check(self):
        """Guard against a refactor that makes this whole file vacuous."""
        assert len(_declared_requirements()) >= 8

    @pytest.mark.parametrize(
        "group,text", _declared_requirements(), ids=lambda value: value
    )
    def test_every_requirement_has_an_upper_bound(self, group: str, text: str):
        requirement = Requirement(text)
        assert _is_bounded(requirement.specifier), (
            f"{group}: '{text}' has no upper bound, so an upstream major release "
            "would install into CI unreviewed"
        )

    @pytest.mark.parametrize(
        "group,text", _declared_requirements(), ids=lambda value: value
    )
    def test_every_requirement_has_a_lower_bound(self, group: str, text: str):
        requirement = Requirement(text)
        assert any(
            spec.operator in {">=", ">", "==", "===", "~="}
            for spec in requirement.specifier
        ), f"{group}: '{text}' does not say what minimum version the code needs"

    def test_the_rule_rejects_an_unbounded_requirement(self):
        """The check is only worth having if it can actually fail."""
        assert not _is_bounded(Requirement("mcp>=1.13.0").specifier)
        assert _is_bounded(Requirement("mcp>=1.13.0,<2.0").specifier)
