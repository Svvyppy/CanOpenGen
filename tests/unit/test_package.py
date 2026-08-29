"""Tests for package bootstrap metadata."""

import canopengen


def test_package_has_development_version() -> None:
    """The initial package exposes a valid pre-release development version."""
    assert canopengen.__version__ == "0.0.0"
