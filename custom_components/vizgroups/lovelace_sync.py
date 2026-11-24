"""Lovelace sync engine — loads/saves storage and YAML dashboards via HA APIs."""

from __future__ import annotations

import json
import os
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

    def compute_users_for_binding(
        self,
        binding: Binding,
        *,
        members_by_group: dict[str, list[str]] | None = None,
    ) -> list[str]:
        return effective_users(
            binding.expression.include,
            binding.expression.exclude,
            members_by_group
            if members_by_group is not None
            else self.store.members_by_group(),
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


    def list_dashboards(self) -> list[dict[str, Any]]:
        """Enumerate dashboards for the panel browser (url_path + title)."""
        items: list[dict[str, Any]] = [
            {"url_path": "lovelace", "title": "Overview", "mode": "storage"}
        ]
        seen = {"lovelace", "default"}
        try:
            dashboards = self._dashboards()
        except Exception:  # noqa: BLE001
            return items

        def _add(path: str | None, dash: Any) -> None:
            url = "lovelace" if path in (None, "", "default") else str(path)
            if url in seen:
                # Prefer richer title if we already have the stub Overview entry
                if url == "lovelace" and items:
                    cfg = getattr(dash, "config", None) or {}
                    title = (
                        getattr(dash, "title", None)
                        or (cfg.get("title") if isinstance(cfg, dict) else None)
                    )
                    if title:
                        items[0]["title"] = str(title)
                    mode = _mode_str(getattr(dash, "mode", None))
                    if mode:
                        items[0]["mode"] = mode
                return
            seen.add(url)
            cfg = getattr(dash, "config", None) or {}
            title = (
                getattr(dash, "title", None)
                or (cfg.get("title") if isinstance(cfg, dict) else None)
                or url
            )
            items.append(
                {
                    "url_path": url,
                    "title": str(title),
                    "mode": _mode_str(getattr(dash, "mode", None)) or "storage",
                }
            )

        # Mapping / collection styles across HA versions
        if hasattr(dashboards, "items"):
            try:
                for key, dash in list(dashboards.items()):
                    _add(key, dash)
            except Exception:  # noqa: BLE001
                pass
        elif isinstance(dashboards, dict):
            for key, dash in dashboards.items():
                _add(key, dash)

        # YAML dashboards registered in configuration.yaml (in case not yet in API)
        try:
            from homeassistant.config import load_yaml_config_file

            conf = load_yaml_config_file(self.hass.config.path("configuration.yaml"))
            registered = (conf.get("lovelace") or {}).get("dashboards") or {}
            if isinstance(registered, dict):
                for key, cfg in registered.items():
                    if key in seen:
                        continue
                    seen.add(str(key))
                    items.append(
                        {
                            "url_path": str(key),
                            "title": str((cfg or {}).get("title") or key),
                            "mode": str((cfg or {}).get("mode") or "yaml"),
                        }
                    )
        except Exception:  # noqa: BLE001
            pass

        # Discover YAML files under lovelace/ that are not yet registered.
        try:
            lovelace_dir = self.hass.config.path("lovelace")
            if os.path.isdir(lovelace_dir):
                for name in sorted(os.listdir(lovelace_dir)):
                    if not name.endswith(".yaml"):
                        continue
                    stem = name[:-5]
                    url = stem.replace("_", "-")
                    if url in seen or stem in seen:
                        continue
                    seen.add(url)
                    title = "Viz Groups Lab" if url == "vizgroups-lab" else url.replace("-", " ").title()
                    items.append(
                        {
                            "url_path": url,
                            "title": title,
                            "mode": "yaml",
                        }
                    )
        except Exception:  # noqa: BLE001
            pass

        # Registry is the source of truth for storage dashboards (Overview + user).
        # HA's in-memory dashboards map sometimes omits the default Overview.
        try:
            reg_path = self.hass.config.path(".storage/lovelace_dashboards")
            with open(reg_path, encoding="utf-8") as handle:
                reg = json.load(handle)
            for item in ((reg.get("data") or {}).get("items") or []):
                if not isinstance(item, dict):
                    continue
                url = item.get("url_path") or item.get("id")
                if not url:
                    continue
                url = "lovelace" if url in ("default",) else str(url)
                if url in seen:
                    # Refresh title/mode from registry when richer.
                    for row in items:
                        if row["url_path"] != url:
                            continue
                        if item.get("title"):
                            row["title"] = str(item["title"])
                        if item.get("mode"):
                            row["mode"] = str(item["mode"])
                        break
                    continue
                seen.add(url)
                items.append(
                    {
                        "url_path": url,
                        "title": str(item.get("title") or url),
                        "mode": str(item.get("mode") or "storage"),
                    }
                )
        except Exception:  # noqa: BLE001
            pass

        items.sort(key=lambda d: (d["url_path"] != "lovelace", d["title"].casefold()))
        return items

    def _get_dashboard(self, url_path: str | None) -> Any:
        """Resolve a dashboard. Do not silently fall back when a specific path was requested."""
        dashboards = self._dashboards()
        # Default overview
        if url_path in (None, "", "lovelace", "default"):
            dashboard = None
            try:
                dashboard = dashboards.get(None)
            except Exception:  # noqa: BLE001
                dashboard = None
            if dashboard is None:
                try:
                    dashboard = dashboards.get("")
                except Exception:  # noqa: BLE001
                    dashboard = None
            if dashboard is None:
                raise HomeAssistantError("Default Lovelace dashboard not found")
            return dashboard

        try:
            dashboard = dashboards.get(url_path)
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Dashboard not found: {url_path}") from err
        if dashboard is None:
            raise HomeAssistantError(f"Dashboard not found: {url_path}")
        return dashboard

    def _yaml_filename_for(self, url_path: str | None, dashboard: Any | None = None) -> str | None:
        """Resolve YAML filename for a dashboard url_path."""
        if dashboard is not None:
            filename = (
                getattr(dashboard, "filename", None)
                or getattr(dashboard, "_filename", None)
            )
            cfg = getattr(dashboard, "_config", None) or getattr(dashboard, "config", None) or {}
            if not filename and isinstance(cfg, dict):
                filename = cfg.get("filename")
            if filename:
                return str(filename)
        if not url_path:
            return None
        try:
            from homeassistant.config import load_yaml_config_file

            conf = load_yaml_config_file(self.hass.config.path("configuration.yaml"))
            dash_conf = ((conf.get("lovelace") or {}).get("dashboards") or {}).get(url_path) or {}
            if isinstance(dash_conf, dict) and dash_conf.get("filename"):
                return str(dash_conf.get("filename"))
        except Exception:  # noqa: BLE001
            pass
        # Convention: lovelace/<url_path>.yaml (and underscore variant).
        for candidate in (f"lovelace/{url_path}.yaml", f"lovelace/{str(url_path).replace('-', '_')}.yaml"):
            if os.path.isfile(self.hass.config.path(candidate)):
                return candidate
        return None


    def _storage_key_candidates(self, url_path: str | None) -> list[str]:
        """Possible .storage keys for a dashboard url_path.

        Overview is stored as ``lovelace.lovelace`` on modern HA (not bare
        ``lovelace``). Custom dashboards use ``lovelace.<id>``.
        """
        is_overview = url_path in (None, "", "lovelace", "default")
        path = "lovelace" if is_overview else str(url_path)
        underscored = path.replace("-", "_")
        keys: list[str] = []
        if is_overview:
            keys.extend(["lovelace.lovelace", "lovelace"])
        else:
            keys.append(f"lovelace.{underscored}")
            if underscored != path:
                keys.append(f"lovelace.{path}")
        # Prefer registry id from lovelace_dashboards when present
        try:
            reg_path = self.hass.config.path(".storage/lovelace_dashboards")
            with open(reg_path, encoding="utf-8") as handle:
                reg = json.load(handle)
            for item in ((reg.get("data") or {}).get("items") or []):
                if not isinstance(item, dict):
                    continue
                if (
                    item.get("url_path") == path
                    or item.get("id") == underscored
                    or item.get("id") == path
                ):
                    dash_id = item.get("id")
                    if dash_id:
                        key = f"lovelace.{dash_id}"
                        if key not in keys:
                            keys.insert(0, key)
        except Exception:  # noqa: BLE001
            pass
        out: list[str] = []
        for key in keys:
            if key not in out:
                out.append(key)
        return out

    def _load_storage_file_config(self, url_path: str | None) -> dict[str, Any] | None:
        """Load Lovelace config from .storage JSON when async_load fails."""
        for key in self._storage_key_candidates(url_path):
            path = self.hass.config.path(f".storage/{key}")
            try:
                with open(path, encoding="utf-8") as handle:
                    payload = json.load(handle)
            except FileNotFoundError:
                continue
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Failed reading storage %s: %s", key, err)
                continue
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, dict):
                continue
            config = data.get("config")
            if isinstance(config, dict) and isinstance(config.get("views"), list):
                _LOGGER.info(
                    "Loaded storage dashboard %s from .storage/%s (%s views)",
                    url_path or "lovelace",
                    key,
                    len(config.get("views") or []),
                )
                return config
        return None

    def _load_yaml_file_config(self, filename: str) -> dict[str, Any]:
        path = self.hass.config.path(str(filename))
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise HomeAssistantError(f"YAML dashboard {filename} is not a mapping")
        return data

    async def async_get_lovelace_config(self, url_path: str | None) -> dict[str, Any]:
        """Fetch a dashboard config via lovelace API (storage or yaml), with YAML file fallback."""
        display = url_path or "lovelace"
        try:
            dashboard = self._get_dashboard(url_path)
        except HomeAssistantError:
            # YAML-only registration may exist in configuration.yaml before API exposes it.
            filename = await self.hass.async_add_executor_job(
                self._yaml_filename_for, url_path, None
            )
            if not filename:
                raise
            config = await self.hass.async_add_executor_job(self._load_yaml_file_config, filename)
            if not isinstance(config.get("views"), list):
                raise HomeAssistantError(
                    f"Dashboard '{display}' YAML {filename} has no views"
                )
            return config

        mode_val = _mode_str(getattr(dashboard, "mode", None))
        if mode_val not in ("storage", "yaml"):
            raise HomeAssistantError(
                f"Dashboard '{display}' is mode={mode_val}; Viz Groups supports storage/yaml"
            )

        config: dict[str, Any] | None = None
        try:
            loaded = await dashboard.async_load(False)
            if isinstance(loaded, dict):
                config = loaded
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Lovelace async_load failed for %s: %s", display, err)
            config = None

        # Some YAML dashboards return empty/partial payloads — fall back to file.
        if mode_val == "yaml" and (
            not isinstance(config, dict) or not isinstance(config.get("views"), list)
        ):
            filename = self._yaml_filename_for(url_path if url_path not in (None, "", "lovelace", "default") else None, dashboard)
            if not filename and url_path not in (None, "", "lovelace", "default"):
                filename = await self.hass.async_add_executor_job(
                    self._yaml_filename_for, url_path, None
                )
            if filename:
                config = await self.hass.async_add_executor_job(
                    self._load_yaml_file_config, filename
                )
                _LOGGER.info(
                    "Loaded YAML dashboard %s from file %s (%s views)",
                    display,
                    filename,
                    len(config.get("views") or []) if isinstance(config, dict) else 0,
                )

        # Storage dashboards: async_load can fail (esp. Overview) — read .storage JSON.
        if mode_val == "storage" and (
            not isinstance(config, dict) or not isinstance(config.get("views"), list)
        ):
            stored = await self.hass.async_add_executor_job(
                self._load_storage_file_config, url_path
            )
            if isinstance(stored, dict):
                config = stored

        if not isinstance(config, dict) or not isinstance(config.get("views"), list):
            # Overview often has no .storage/lovelace yet — return empty rather than hard-fail
            # so the panel can show a clear empty state instead of a WS error.
            if url_path in (None, "", "lovelace", "default"):
                _LOGGER.info(
                    "Overview has no loadable views; returning empty config for preview"
                )
                return {"title": "Overview", "views": []}
            raise HomeAssistantError(
                f"Invalid lovelace config payload for '{display}' "
                f"(mode={mode_val}, type={type(config).__name__})"
            )
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
            filename = (
                getattr(dashboard, "filename", None)
                or getattr(dashboard, "_filename", None)
            )
            cfg = getattr(dashboard, "_config", None) or getattr(dashboard, "config", None) or {}
            if not filename and isinstance(cfg, dict):
                filename = cfg.get("filename")
            if not filename and url_path:
                # Fall back to lovelace.dashboards registration in configuration.yaml
                try:
                    from homeassistant.config import load_yaml_config_file

                    conf = load_yaml_config_file(self.hass.config.path("configuration.yaml"))
                    dash_conf = (
                        (conf.get("lovelace") or {}).get("dashboards") or {}
                    ).get(url_path) or {}
                    filename = dash_conf.get("filename")
                except Exception:  # noqa: BLE001
                    filename = None
            if not filename and url_path:
                filename = self._yaml_filename_for(url_path, dashboard)
            # Prefer LovelaceYAML absolute path when present.
            abs_path = getattr(dashboard, "path", None)
            if abs_path:
                path = str(abs_path)
            else:
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

        # Membership map once per sync — bindings only read it.
        members_by_group = self.store.members_by_group()

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
                users = self.compute_users_for_binding(
                    binding, members_by_group=members_by_group
                )
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
                    # Mutate in place; persisted with the single store save below.
                    binding.stale = True
                elif status == "ok" and new_config is not None:
                    config = new_config
                    dirty = True
                    binding.stale = False
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
        # One store write for sync meta + any stale-flag flips (avoid per-binding I/O).
        await self.store.async_save()

        summary = {
            "dry_run": do_dry,
            "results": results,
            "errors": errors,
            "last_sync": meta.last_sync,
        }
        self.hass.bus.async_fire(EVENT_SYNCED, summary)
        _LOGGER.info(
            "Viz Groups sync finished dry_run=%s bindings=%s errors=%s",
            do_dry,
            len(results),
            len(errors),
        )
        return summary
