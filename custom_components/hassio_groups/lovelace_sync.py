"""Lovelace sync engine — loads/saves storage and YAML dashboards via HA APIs."""

from __future__ import annotations

import logging
from typing import Any

import yaml

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


def _mode_str(mode: Any) -> str:
    if mode is None:
        return "storage"
    return str(getattr(mode, "value", mode)).lower()


class LovelaceSyncEngine:
    """Apply bindings to Lovelace configs (storage or yaml)."""

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

    def _dashboards(self) -> Any:
        lovelace = self.hass.data.get("lovelace")
        if lovelace is None:
            raise HomeAssistantError("Lovelace is not available")
        dashboards = getattr(lovelace, "dashboards", None)
        if dashboards is None:
            raise HomeAssistantError("Lovelace dashboards API unavailable")
        return dashboards

    def _get_dashboard(self, url_path: str | None) -> Any:
        dashboards = self._dashboards()
        try:
            dashboard = dashboards.get(url_path)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Dashboard not found: {url_path}") from err
        if dashboard is None:
            dashboard = dashboards.get(None) or dashboards.get("")
        if dashboard is None:
            raise HomeAssistantError(f"Dashboard not found: {url_path}")
        return dashboard

    async def async_get_lovelace_config(self, url_path: str | None) -> dict[str, Any]:
        """Fetch a dashboard config via lovelace API (storage or yaml)."""
        dashboard = self._get_dashboard(url_path)
        mode_val = _mode_str(getattr(dashboard, "mode", None))
        if mode_val not in ("storage", "yaml"):
            raise HomeAssistantError(
                f"Dashboard '{url_path}' is mode={mode_val}; HA Groups supports storage/yaml"
            )
        config = await dashboard.async_load(False)
        if not isinstance(config, dict):
            raise HomeAssistantError("Invalid lovelace config payload")
        return config

    async def async_save_lovelace_config(
        self, url_path: str | None, config: dict[str, Any]
    ) -> None:
        dashboard = self._get_dashboard(url_path)
        mode_val = _mode_str(getattr(dashboard, "mode", None))
        if mode_val == "storage":
            await dashboard.async_save(config)
            return
        if mode_val == "yaml":
            # LovelaceYAML exposes an absolute `.path`; prefer that over filename guesswork.
            path = getattr(dashboard, "path", None)
            filename: str | None = None
            if path:
                path = str(path)
            else:
                filename = (
                    getattr(dashboard, "filename", None)
                    or getattr(dashboard, "_filename", None)
                )
                cfg = (
                    getattr(dashboard, "_config", None)
                    or getattr(dashboard, "config", None)
                    or {}
                )
                if not filename and isinstance(cfg, dict):
                    filename = cfg.get("filename")
                if not filename and url_path:
                    # Fall back to lovelace.dashboards registration in configuration.yaml
                    try:
                        from homeassistant.config import load_yaml_config_file

                        conf = load_yaml_config_file(
                            self.hass.config.path("configuration.yaml")
                        )
                        dash_conf = (
                            (conf.get("lovelace") or {}).get("dashboards") or {}
                        ).get(url_path) or {}
                        filename = dash_conf.get("filename")
                    except Exception:  # noqa: BLE001
                        filename = None
                if not filename:
                    raise HomeAssistantError(
                        f"YAML dashboard '{url_path}' has no path/filename to write"
                    )
                path = self.hass.config.path(str(filename))

            def _write() -> None:
                with open(path, "w", encoding="utf-8") as handle:
                    yaml.safe_dump(
                        config,
                        handle,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )

            await self.hass.async_add_executor_job(_write)
            # Drop stale YAML cache so the next load sees our write.
            if hasattr(dashboard, "_cache"):
                dashboard._cache = None  # noqa: SLF001
            if self.hass.services.has_service("lovelace", "reload"):
                await self.hass.services.async_call("lovelace", "reload", blocking=True)
            _LOGGER.info(
                "Wrote YAML dashboard %s and reloaded lovelace",
                filename or path,
            )
            return
        raise HomeAssistantError(
            f"Dashboard '{url_path}' is mode={mode_val}; cannot save"
        )

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
