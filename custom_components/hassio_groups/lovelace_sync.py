"""Lovelace sync engine skeleton — loads/saves storage dashboards via HA APIs."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_DASHBOARDS,
    CONF_DRY_RUN,
    CONF_NORMALIZE_DUPLICATES,
    DEFAULT_DRY_RUN,
    DEFAULT_NORMALIZE_DUPLICATES,
    EVENT_SYNCED,
    MERGE_ENSURE_USER_BRANCH,
)
from .membership import effective_users
from .models import Binding, SyncMetadata, _utcnow_iso
from .store import GroupsStore
from .sync import apply_binding_to_config

_LOGGER = logging.getLogger(__name__)


class LovelaceSyncEngine:
    """Apply bindings to storage-mode Lovelace configs."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: GroupsStore,
        *,
        options: dict[str, Any] | None = None,
    ) -> None:
        self.hass = hass
        self.store = store
        self.options = options or {}

    @property
    def dry_run(self) -> bool:
        return bool(self.options.get(CONF_DRY_RUN, DEFAULT_DRY_RUN))

    @property
    def normalize_duplicates(self) -> bool:
        return bool(
            self.options.get(CONF_NORMALIZE_DUPLICATES, DEFAULT_NORMALIZE_DUPLICATES)
        )

    @property
    def dashboard_allowlist(self) -> list[str]:
        return list(self.options.get(CONF_DASHBOARDS) or [])

    def compute_users_for_binding(self, binding: Binding) -> list[str]:
        return effective_users(
            binding.expression.include,
            binding.expression.exclude,
            self.store.members_by_group(),
            normalize_duplicates=self.normalize_duplicates,
        )

    async def async_get_lovelace_config(self, url_path: str | None) -> dict[str, Any]:
        """Fetch a dashboard config via lovelace websocket API path."""
        # Prefer the lovelace component's internal API when available.
        lovelace = self.hass.data.get("lovelace")
        if lovelace is None:
            raise HomeAssistantError("Lovelace is not available")

        # HA stores dashboards under lovelace dashboards collection.
        dashboards = getattr(lovelace, "dashboards", None)
        if dashboards is None:
            raise HomeAssistantError("Lovelace dashboards API unavailable")

        key = url_path  # None / "lovelace" → default dashboard depending on HA version
        try:
            dashboard = dashboards.get(key)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Dashboard not found: {url_path}") from err

        if dashboard is None:
            # Fallback: try empty string / None for Overview
            dashboard = dashboards.get(None) or dashboards.get("")
        if dashboard is None:
            raise HomeAssistantError(f"Dashboard not found: {url_path}")

        mode = getattr(dashboard, "mode", None)
        mode_val = getattr(mode, "value", mode)
        if mode_val and str(mode_val) != "storage":
            raise HomeAssistantError(
                f"Dashboard '{url_path}' is mode={mode_val}; HA Groups only writes storage dashboards"
            )

        config = await dashboard.async_load(False)
        if not isinstance(config, dict):
            raise HomeAssistantError("Invalid lovelace config payload")
        return config

    async def async_save_lovelace_config(
        self, url_path: str | None, config: dict[str, Any]
    ) -> None:
        lovelace = self.hass.data.get("lovelace")
        dashboards = getattr(lovelace, "dashboards", None)
        dashboard = dashboards.get(url_path) if dashboards else None
        if dashboard is None and dashboards is not None:
            dashboard = dashboards.get(None) or dashboards.get("")
        if dashboard is None:
            raise HomeAssistantError(f"Dashboard not found: {url_path}")
        await dashboard.async_save(config)

    async def async_sync(
        self, *, dashboard: str | None = None, dry_run: bool | None = None
    ) -> dict[str, Any]:
        """Sync all (or filtered) bindings. Returns a result summary."""
        do_dry = self.dry_run if dry_run is None else dry_run
        allow = self.dashboard_allowlist
        results: list[dict[str, Any]] = []
        errors: list[str] = []

        # Group bindings by dashboard for fewer loads
        by_dash: dict[str, list[Binding]] = {}
        for binding in self.store.bindings.values():
            path = binding.dashboard_url_path or "lovelace"
            if dashboard and path != dashboard:
                continue
            if allow and path not in allow:
                continue
            by_dash.setdefault(path, []).append(binding)

        for path, bindings in by_dash.items():
            url_key: str | None = None if path in ("lovelace", "default") else path
            try:
                config = await self.async_get_lovelace_config(url_key)
            except HomeAssistantError as err:
                msg = str(err)
                errors.append(msg)
                for binding in bindings:
                    results.append(
                        {
                            "binding_id": binding.id,
                            "dashboard": path,
                            "status": "error",
                            "error": msg,
                        }
                    )
                continue

            dirty = False
            for binding in bindings:
                users = self.compute_users_for_binding(binding)
                new_config, status = apply_binding_to_config(
                    config,
                    binding.locator,
                    users,
                    merge_mode=binding.merge_mode or MERGE_ENSURE_USER_BRANCH,
                    expected_fingerprint=binding.fingerprint or None,
                )
                entry: dict[str, Any] = {
                    "binding_id": binding.id,
                    "dashboard": path,
                    "status": status,
                    "users": users,
                }
                if status == "stale":
                    binding.stale = True
                    await self.store.upsert_binding(binding)
                elif status == "ok" and new_config is not None:
                    config = new_config
                    dirty = True
                    if binding.stale:
                        binding.stale = False
                        await self.store.upsert_binding(binding)
                results.append(entry)

            if dirty and not do_dry:
                try:
                    await self.async_save_lovelace_config(url_key, config)
                except HomeAssistantError as err:
                    errors.append(str(err))

        meta = SyncMetadata(
            last_sync=_utcnow_iso(),
            last_error="; ".join(errors) if errors else None,
            dry_run_last=do_dry,
        )
        self.store.sync_meta = meta
        await self.store.async_save()

        summary = {
            "dry_run": do_dry,
            "results": results,
            "errors": errors,
            "last_sync": meta.last_sync,
        }
        self.hass.bus.async_fire(EVENT_SYNCED, summary)
        _LOGGER.info(
            "HA Groups sync finished dry_run=%s bindings=%s errors=%s",
            do_dry,
            len(results),
            len(errors),
        )
        return summary
