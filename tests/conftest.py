"""Load pure groups modules without importing the HA __init__."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "groups"


def _load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Minimal package shell so relative imports inside sync.py work.
if "groups" not in sys.modules:
    pkg = types.ModuleType("groups")
    pkg.__path__ = [str(PKG)]  # type: ignore[attr-defined]
    pkg.__file__ = str(PKG / "__init__.py")
    sys.modules["groups"] = pkg

_load("groups.const", PKG / "const.py")
_load("groups.models", PKG / "models.py")
_load("groups.membership", PKG / "membership.py")
_load("groups.sync", PKG / "sync.py")
