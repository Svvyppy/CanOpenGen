"""Tests keeping the public JSON Schema synchronized with parser behavior."""

import json
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).parents[2]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "canopengen.schema.json"


def _schema() -> dict[str, Any]:
    """Load the public schema as a typed JSON object."""
    return cast(dict[str, Any], json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_schema_is_valid_draft_2020_12() -> None:
    """The checked-in schema is itself valid JSON Schema."""
    Draft202012Validator.check_schema(_schema())


def test_schema_accepts_all_project_examples() -> None:
    """Every checked-in Device and Module example conforms structurally."""
    validator = Draft202012Validator(_schema())
    paths = sorted((PROJECT_ROOT / "Modules").glob("*.yml")) + sorted(
        (PROJECT_ROOT / "Device").glob("*.yml")
    )

    for path in paths:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert not list(validator.iter_errors(document)), path


def test_schema_rejects_device_and_module_in_same_file() -> None:
    """A definition has exactly one top-level identity kind."""
    validator = Draft202012Validator(_schema())
    document = {
        "schema": 1,
        "device": {"name": "Device"},
        "module": {"name": "Module"},
    }

    assert list(validator.iter_errors(document))


def test_schema_accepts_parameterized_module_import() -> None:
    """The MVP parameter architecture accepts only simple scalar values."""
    validator = Draft202012Validator(_schema())
    document = {
        "schema": 1,
        "device": {"name": "Device"},
        "modules": [
            {
                "name": "Diagnostics",
                "params": {"channel_count": 4, "enabled": True, "label": "main"},
            }
        ],
    }

    assert not list(validator.iter_errors(document))
