"""Unit tests for Lovelace storage key resolution + registry dashboard list."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from vizgroups.lovelace_sync import LovelaceSyncEngine


def _engine(tmp_path: Path, *, dashboards: Any | None = None) -> LovelaceSyncEngine:
    hass = MagicMock()
    hass.config.path = lambda *parts: str(tmp_path.joinpath(*parts))
    if dashboards is None:

        class EmptyDashMap:
            def items(self):
                return []

            def get(self, key: Any) -> Any:
                return None

        dashboards = EmptyDashMap()
    hass.data = {"lovelace": MagicMock(dashboards=dashboards)}
    return LovelaceSyncEngine(hass, store=MagicMock(), options={})


def test_storage_key_candidates_overview_prefers_lovelace_dot_lovelace(
    tmp_path: Path,
) -> None:
    engine = _engine(tmp_path)
    keys = engine._storage_key_candidates(None)
    assert keys[0] == "lovelace.lovelace"
    assert "lovelace" in keys
    assert engine._storage_key_candidates("lovelace") == keys
    assert engine._storage_key_candidates("default") == keys
    assert engine._storage_key_candidates("") == keys


def test_storage_key_candidates_overview_registry_id_dedupes(tmp_path: Path) -> None:
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
    engine = _engine(tmp_path)
    keys = engine._storage_key_candidates("lovelace")
    assert keys[0] == "lovelace.lovelace"
    assert keys.count("lovelace.lovelace") == 1
    assert "lovelace" in keys


def test_storage_key_candidates_named_dashboard_prefers_registry_id(
    tmp_path: Path,
) -> None:
    storage = tmp_path / ".storage"
    storage.mkdir()
    (storage / "lovelace_dashboards").write_text(
        json.dumps(
            {
                "data": {
                    "items": [
                        {
                            "id": "dashboard_apartment",
                            "url_path": "dashboard-apartment",
                            "title": "Apartment",
                            "mode": "storage",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    engine = _engine(tmp_path)
    keys = engine._storage_key_candidates("dashboard-apartment")
    assert keys[0] == "lovelace.dashboard_apartment"
    assert "lovelace.dashboard_apartment" in keys
    assert "lovelace.dashboard-apartment" in keys


def test_load_storage_prefers_lovelace_dot_lovelace_over_classic_stub(
    tmp_path: Path,
) -> None:
    """Taken-control Overview lives at lovelace.lovelace; prefer it over classic."""
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
    # Classic stub with empty views must not win when lovelace.lovelace exists.
    (storage / "lovelace").write_text(
        json.dumps({"data": {"config": {"title": "Overview", "views": []}}}),
        encoding="utf-8",
    )

    engine = _engine(tmp_path)
    config = engine._load_storage_file_config("lovelace")
    assert config is not None
    assert len(config["views"]) == 1
    assert config["views"][0]["title"] == "Building"


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

    engine = _engine(tmp_path)
    listed = engine.list_dashboards()
    paths = [d["url_path"] for d in listed]
    assert paths[0] == "lovelace"
    assert "dashboard-apartment" in paths
    apartment = next(d for d in listed if d["url_path"] == "dashboard-apartment")
    assert apartment["title"] == "Apartment"
    assert apartment["mode"] == "storage"
    overview = next(d for d in listed if d["url_path"] == "lovelace")
    assert overview["title"] == "Overview"
