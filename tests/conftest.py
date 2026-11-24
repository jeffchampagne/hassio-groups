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


def _ensure_homeassistant_stubs() -> None:
    """Minimal stubs so lovelace_sync/store import without Home Assistant installed."""
    if "homeassistant" in sys.modules and hasattr(sys.modules["homeassistant"], "core"):
        return

    ha = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = type("HomeAssistant", (), {})
    exceptions = types.ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        """Stub HA error."""

    exceptions.HomeAssistantError = HomeAssistantError
    helpers = types.ModuleType("homeassistant.helpers")
    storage = types.ModuleType("homeassistant.helpers.storage")

    class Store:  # noqa: D401
        def __init__(self, *args, **kwargs) -> None:
            pass

    storage.Store = Store
    config = types.ModuleType("homeassistant.config")
    config.load_yaml_config_file = lambda path: {}

    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.exceptions"] = exceptions
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.storage"] = storage
    sys.modules["homeassistant.config"] = config
    ha.core = core
    ha.exceptions = exceptions
    ha.helpers = helpers
    ha.config = config

    if "yaml" not in sys.modules:
        yaml_mod = types.ModuleType("yaml")
        yaml_mod.safe_load = lambda *args, **kwargs: {}
        yaml_mod.safe_dump = lambda *args, **kwargs: None
        sys.modules["yaml"] = yaml_mod


# Minimal package shell so relative imports inside sync.py work.
if "vizgroups" not in sys.modules:
    pkg = types.ModuleType("vizgroups")
    pkg.__path__ = [str(PKG)]  # type: ignore[attr-defined]
    pkg.__file__ = str(PKG / "__init__.py")
    sys.modules["vizgroups"] = pkg

_ensure_homeassistant_stubs()
_load("vizgroups.const", PKG / "const.py")
_load("vizgroups.membership", PKG / "membership.py")
_load("vizgroups.models", PKG / "models.py")
_load("vizgroups.sync", PKG / "sync.py")
_load("vizgroups.store", PKG / "store.py")
_load("vizgroups.lovelace_sync", PKG / "lovelace_sync.py")
