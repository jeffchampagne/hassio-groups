"""Load pure vizgroups modules without importing the HA __init__."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "vizgroups"


def _load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Minimal package shell so relative imports inside sync.py work.
if "vizgroups" not in sys.modules:
    pkg = types.ModuleType("vizgroups")
    pkg.__path__ = [str(PKG)]  # type: ignore[attr-defined]
    pkg.__file__ = str(PKG / "__init__.py")
    sys.modules["vizgroups"] = pkg

_load("vizgroups.const", PKG / "const.py")
_load("vizgroups.models", PKG / "models.py")
_load("vizgroups.membership", PKG / "membership.py")
_load("vizgroups.sync", PKG / "sync.py")
