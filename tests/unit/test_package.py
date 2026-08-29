"""Tests for package bootstrap metadata."""

import canopengen


def test_package_has_release_version() -> None:
    """The release package exposes the version declared in project metadata."""
    assert canopengen.__version__ == "1.0.0"
