"""Unit tests for Lovelace storage key resolution + overview fallbacks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from vizgroups.lovelace_sync import (
    LovelaceSyncEngine,
    storage_key_candidates,
)


def test_storage_key_candidates_overview_includes_lovelace_dot_lovelace() -> None:
    keys = storage_key_candidates(None)
    assert keys[0] == "lovelace"
    assert "lovelace.lovelace" in keys
    assert storage_key_candidates("lovelace") == keys
    assert storage_key_candidates("default") == keys


def test_storage_key_candidates_overview_uses_registry_id() -> None:
    keys = storage_key_candidates(
        "lovelace",
        registry_items=[
            {
                "id": "lovelace",
                "url_path": "lovelace",
                "title": "Overview",
                "mode": "storage",
            }
        ],
    )
    assert "lovelace.lovelace" in keys
    assert keys.count("lovelace.lovelace") == 1


def test_storage_key_candidates_named_dashboard_prefers_registry_id() -> None:
    keys = storage_key_candidates(
        "dashboard-apartment",
        registry_items=[
            {
                "id": "dashboard_apartment",
                "url_path": "dashboard-apartment",
                "title": "Apartment",
                "mode": "storage",
            }
        ],
    )
    assert keys[0] == "lovelace.dashboard_apartment"
    assert "lovelace.dashboard_apartment" in keys
    assert "lovelace.dashboard-apartment" in keys


def test_load_storage_skips_empty_classic_for_taken_control_overview(
    tmp_path: Path,
) -> None:
    """mjm-phl shape: empty/missing classic key, real views in lovelace.lovelace."""
    storage = tmp_path / ".storage"
    storage.mkdir()
    (storage / "lovelace_dashboards").write_text(
        json.dumps(
            {
                "data": {
                    "items": [
                        {
                            "id": "lovelace",
                            "url_path": "lovelace",
                            "title": "Overview",
                            "mode": "storage",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    (storage / "lovelace.lovelace").write_text(
        json.dumps(
            {
                "data": {
                    "config": {
                        "title": "Overview",
                        "views": [
                            {
                                "title": "Building",
                                "type": "sections",
                                "sections": [
                                    {
                                        "title": "Doors",
                                        "visibility": [
                                            {
                                                "condition": "user",
                                                "users": ["u1"],
                                            }
                                        ],
                                        "cards": [],
                                    }
                                ],
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    # Stale classic stub must not win over lovelace.lovelace.
    (storage / "lovelace").write_text(
        json.dumps({"data": {"config": {"title": "Overview", "views": []}}}),
        encoding="utf-8",
    )

    hass = MagicMock()
    hass.config.path = lambda *parts: str(tmp_path.joinpath(*parts))
    engine = LovelaceSyncEngine(hass, store=MagicMock(), options={})

    config = engine._load_storage_file_config("lovelace")
    assert config is not None
    assert len(config["views"]) == 1
    assert config["views"][0]["title"] == "Building"


def test_get_dashboard_prefers_named_lovelace_over_none() -> None:
    classic = MagicMock(name="classic")
    named = MagicMock(name="named")

    class DashMap:
        def get(self, key: Any) -> Any:
            if key is None:
                return classic
            if key == "lovelace":
                return named
            return None

    hass = MagicMock()
    hass.data = {"lovelace": MagicMock(dashboards=DashMap())}
    engine = LovelaceSyncEngine(hass, store=MagicMock(), options={})
    assert engine._get_dashboard(None) is named
    assert engine._get_dashboard("lovelace") is named


def test_list_dashboards_merges_registry(tmp_path: Path) -> None:
    storage = tmp_path / ".storage"
    storage.mkdir()
    (storage / "lovelace_dashboards").write_text(
        json.dumps(
            {
                "data": {
                    "items": [
                        {
                            "id": "lovelace",
                            "url_path": "lovelace",
                            "title": "Overview",
                            "mode": "storage",
                        },
                        {
                            "id": "dashboard_apartment",
                            "url_path": "dashboard-apartment",
                            "title": "Apartment",
                            "mode": "storage",
                        },
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    class DashMap:
        def items(self):
            return []

        def get(self, key: Any) -> Any:
            return None

    hass = MagicMock()
    hass.data = {"lovelace": MagicMock(dashboards=DashMap())}
    hass.config.path = lambda *parts: str(tmp_path.joinpath(*parts))
    engine = LovelaceSyncEngine(hass, store=MagicMock(), options={})
    listed = engine.list_dashboards()
    paths = [d["url_path"] for d in listed]
    assert paths[0] == "lovelace"
    assert "dashboard-apartment" in paths
    assert {d["title"] for d in listed if d["url_path"] == "lovelace"} == {"Overview"}
