"""Packaging guards: one version everywhere, and uv rebuilds on source changes."""

import json
from pathlib import Path

import pytest

import receipt_sweep

tomllib = pytest.importorskip("tomllib")  # stdlib from Python 3.11

ROOT = Path(__file__).resolve().parent.parent


def _pyproject():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_plugin_manifest_matches_package_version():
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["version"] == receipt_sweep.__version__


def test_package_version_comes_from_init():
    data = _pyproject()
    assert "version" in data["project"]["dynamic"]
    assert data["tool"]["hatch"]["version"]["path"] == "src/receipt_sweep/__init__.py"


def test_uv_rebuilds_when_source_files_change():
    # The plugin runs `uvx --from <plugin dir>`; without a source cache key an
    # in-place plugin update keeps serving the previously built code.
    keys = [k.get("file") for k in _pyproject()["tool"]["uv"]["cache-keys"]]
    assert "src/**/*.py" in keys
