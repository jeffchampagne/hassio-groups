"""Viz Groups — user groups for Lovelace visibility + automation conditions."""

from __future__ import annotations

import importlib
import inspect
import logging
import sys
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_BINDING_ID,
    ATTR_DASHBOARD,
    ATTR_EXCLUDE,
    ATTR_GROUP_ID,
    ATTR_INCLUDE,
    ATTR_IS_MEMBER,
    ATTR_MEMBERS,
    ATTR_USER_ID,
    CONF_AUTO_SYNC,
    DEFAULT_AUTO_SYNC,
    DOMAIN,
    EVENT_MEMBERSHIP_CHANGED,
    MERGE_ENSURE_USER_BRANCH,
    MERGE_MODES,
    NAME,
    PLATFORMS,
)
from .lovelace_sync import LovelaceSyncEngine
from .membership import is_member
from .models import GroupExpression, Locator, new_binding, new_group, utcnow_iso
from .panel import async_register_panel, async_register_websocket
from .sensor import GroupMembershipSensor
from .store import GroupsStore

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

def _reload_ws_modules() -> None:
    """Reload integration modules from disk without a Core restart.

    Order matters: models → sync → lovelace_sync → panel. Also refresh
    ``LovelaceSyncEngine`` / ``GroupsStore`` symbols imported into this module
    so config-entry reload picks up breadcrumb backfill and related fixes.
    """
    pkg = __package__ or "custom_components.vizgroups"
    for mod_name in (
        f"{pkg}.models",
        f"{pkg}.sync",
        f"{pkg}.lovelace_sync",
        f"{pkg}.panel",
    ):
        mod = sys.modules.get(mod_name)
        if mod is not None:
            importlib.reload(mod)
    # Re-bind names this module imported at load time.
    this = sys.modules[__name__]
    ls = sys.modules.get(f"{pkg}.lovelace_sync")
    if ls is not None and hasattr(ls, "LovelaceSyncEngine"):
        this.LovelaceSyncEngine = ls.LovelaceSyncEngine
    st = sys.modules.get(f"{pkg}.store")
    if st is not None and hasattr(st, "GroupsStore"):
        this.GroupsStore = st.GroupsStore




async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register panel + websocket early so the sidebar appears after setup."""
    hass.data.setdefault(DOMAIN, {})
    _reload_ws_modules()
    from .panel import async_register_panel as _reg_panel
    from .panel import async_register_websocket as _reg_ws
    _reg_ws(hass)
    await _reg_panel(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Viz Groups from a config entry."""
    store = GroupsStore(hass)
    await store.async_load()

    runtime = GroupsRuntime(hass, store, entry)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = runtime

    _reload_ws_modules()
    from .panel import async_register_panel as _reg_panel
    from .panel import async_register_websocket as _reg_ws
    _reg_ws(hass)
    # Always invoke — re-registers when PANEL_MODULE_URL cache-busts.
    await _reg_panel(hass)

    await runtime.async_prune_users()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    runtime.register_services()

    entry.async_on_unload(entry.add_update_listener(_async_reload_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    except Exception:  # noqa: BLE001
        # Platforms may never have loaded (not_loaded → reload).
        unload_ok = True
    runtime = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if runtime:
        runtime.unregister_services_if_last()
    return True if unload_ok is None else bool(unload_ok)


async def _async_reload_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime:
        runtime.entry = entry
        runtime.sync_engine.options = dict(entry.options)


class GroupsRuntime:
    """Owns store, sensors, services, and sync engine."""

    def __init__(
        self, hass: HomeAssistant, store: GroupsStore, entry: ConfigEntry
    ) -> None:
        self.hass = hass
        self.store = store
        self.entry = entry
        self.sync_engine = LovelaceSyncEngine(
            hass, store, options=dict(entry.options)
        )
        self.sensors: dict[str, GroupMembershipSensor] = {}
        self.sensor_add_entities: Any | None = None
        self._services_registered = False


    def _get_users_sync(self) -> list[Any]:
        """Return HA users; compatible with sync or async async_get_users()."""
        result = self.hass.auth.async_get_users()
        if not inspect.isawaitable(result):
            return list(result)
        # HA 2026+: async_get_users is a coroutine — close it; do not leave un-awaited.
        close = getattr(result, "close", None)
        if callable(close):
            close()
        # Prefer auth store, else person-linked stubs.
        store = getattr(self.hass.auth, "_store", None)
        for attr in ("users", "_users", "data"):
            users = getattr(store, attr, None) if store is not None else None
            if isinstance(users, dict):
                vals = list(users.values())
                if vals and all(hasattr(u, "id") for u in vals):
                    return vals
            if isinstance(users, list) and users and hasattr(users[0], "id"):
                return list(users)
        # Minimal stubs from person entities so sensors/panel still render.
        class _Stub:
            def __init__(self, uid: str, name: str) -> None:
                self.id = uid
                self.name = name
                self.is_active = True
                self.is_owner = False
                self.system_generated = False

        stubs: list[Any] = []
        seen: set[str] = set()
        for state in self.hass.states.async_all("person"):
            uid = state.attributes.get("user_id")
            if isinstance(uid, str) and uid and uid not in seen:
                seen.add(uid)
                stubs.append(
                    _Stub(uid, state.attributes.get("friendly_name") or state.name or uid)
                )
        return stubs

    async def _async_get_users(self) -> list[Any]:
        result = self.hass.auth.async_get_users()
        if inspect.isawaitable(result):
            return list(await result)
        return list(result)


    def _person_names_by_user(self) -> dict[str, str]:
        person_by_user: dict[str, str] = {}
        for state in self.hass.states.async_all("person"):
            uid = state.attributes.get("user_id")
            if isinstance(uid, str) and uid:
                person_by_user[uid] = state.attributes.get("friendly_name") or state.name
        return person_by_user

    def list_users_for_panel(self) -> list[dict[str, Any]]:
        """Friendly-name-first user rows for the admin UI."""
        person_by_user = self._person_names_by_user()
        rows: list[dict[str, Any]] = []
        for user in self._get_users_sync():
            if user.system_generated:
                continue
            person_name = person_by_user.get(user.id)
            name = person_name or user.name or user.id
            rows.append(
                {
                    "id": user.id,
                    "name": name,
                    "username": getattr(user, "name", None),
                    "is_person": bool(person_name),
                    "is_active": bool(user.is_active),
                    "is_owner": bool(user.is_owner),
                }
            )
        rows.sort(key=lambda r: r["name"].casefold())
        return rows

    def display_names_for(self, user_ids: list[str]) -> list[str]:
        """Resolve friendly names without building/sorting the full panel user list."""
        if not user_ids:
            return []
        person_by_user = self._person_names_by_user()
        lookup: dict[str, str] = {}
        for user in self._get_users_sync():
            if user.system_generated:
                continue
            lookup[user.id] = person_by_user.get(user.id) or user.name or user.id
        for uid, name in person_by_user.items():
            lookup.setdefault(uid, name)
        return [lookup.get(uid, uid) for uid in user_ids]

    async def async_prune_users(self) -> None:
        users = await self._async_get_users()
        valid = {u.id for u in users}
        touched = await self.store.prune_missing_users(valid)
        if touched:
            _LOGGER.info("Pruned missing users from groups: %s", touched)

    async def async_refresh_sensors(self) -> None:
        """Create/update/remove membership sensors to match store."""
        if self.sensor_add_entities is None:
            return
        existing = set(self.sensors)
        current = set(self.store.groups)
        # Update (skip sensors not yet attached to hass)
        for gid in existing & current:
            sensor = self.sensors[gid]
            if getattr(sensor, "hass", None) is None:
                continue
            sensor.apply_group(self.store.groups[gid])
        # Add
        to_add = []
        for gid in current - existing:
            sensor = GroupMembershipSensor(self, self.store.groups[gid])
            self.sensors[gid] = sensor
            to_add.append(sensor)
        if to_add:
            self.sensor_add_entities(to_add)
        # Remove
        for gid in existing - current:
            sensor = self.sensors.pop(gid)
            await sensor.async_remove()

    async def async_maybe_autosync(self) -> None:
        # Auto-sync is always on (UI toggle removed).
        try:
            await self.sync_engine.async_sync()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Auto-sync failed")

    def register_services(self) -> None:
        if self._services_registered:
            return
        if self.hass.services.has_service(DOMAIN, "create_group"):
            self._services_registered = True
            return

        async def create_group(call: ServiceCall) -> None:
            data = dict(call.data)
            group = new_group(
                name=data["name"],
                group_id=data.get("group_id"),
                description=data.get("description") or "",
                icon=data.get("icon") or "mdi:account-group",
                member_user_ids=list(data.get("member_user_ids") or []),
            )
            if self.store.get_group(group.id):
                raise ValueError(f"Group {group.id} already exists")
            await self.store.upsert_group(group)
            await self.async_refresh_sensors()
            self.hass.bus.async_fire(
                EVENT_MEMBERSHIP_CHANGED, {"group_id": group.id, "action": "create"}
            )
            await self.async_maybe_autosync()

        async def update_group(call: ServiceCall) -> None:
            group = self.store.get_group(call.data["group_id"])
            if not group:
                raise ValueError("Unknown group")
            if "name" in call.data:
                group.name = call.data["name"]
            if "description" in call.data:
                group.description = call.data["description"]
            if "icon" in call.data:
                group.icon = call.data["icon"]
            if "member_user_ids" in call.data:
                group.member_user_ids = list(call.data["member_user_ids"] or [])
            group.updated = utcnow_iso()
            await self.store.upsert_group(group)
            await self.async_refresh_sensors()
            self.hass.bus.async_fire(
                EVENT_MEMBERSHIP_CHANGED, {"group_id": group.id, "action": "update"}
            )
            await self.async_maybe_autosync()

        async def delete_group(call: ServiceCall) -> None:
            gid = call.data["group_id"]
            await self.store.delete_group(gid)
            await self.async_refresh_sensors()
            self.hass.bus.async_fire(
                EVENT_MEMBERSHIP_CHANGED, {"group_id": gid, "action": "delete"}
            )
            await self.async_maybe_autosync()

        async def set_members(call: ServiceCall) -> None:
            group = await self.store.set_members(
                call.data["group_id"], list(call.data["user_ids"])
            )
            await self.async_refresh_sensors()
            self.hass.bus.async_fire(
                EVENT_MEMBERSHIP_CHANGED,
                {"group_id": group.id, "action": "set_members"},
            )
            await self.async_maybe_autosync()

        async def add_members(call: ServiceCall) -> None:
            group = await self.store.add_members(
                call.data["group_id"], list(call.data["user_ids"])
            )
            await self.async_refresh_sensors()
            self.hass.bus.async_fire(
                EVENT_MEMBERSHIP_CHANGED,
                {"group_id": group.id, "action": "add_members"},
            )
            await self.async_maybe_autosync()

        async def remove_members(call: ServiceCall) -> None:
            group = await self.store.remove_members(
                call.data["group_id"], list(call.data["user_ids"])
            )
            await self.async_refresh_sensors()
            self.hass.bus.async_fire(
                EVENT_MEMBERSHIP_CHANGED,
                {"group_id": group.id, "action": "remove_members"},
            )
            await self.async_maybe_autosync()

        async def bind_element(call: ServiceCall) -> None:
            include = list(call.data.get(ATTR_INCLUDE) or [])
            if not include:
                raise ValueError("At least one include group is required")
            binding = new_binding(
                expression=GroupExpression(
                    include=include, exclude=list(call.data.get(ATTR_EXCLUDE) or [])
                ),
                dashboard_url_path=call.data["dashboard_url_path"],
                locator=Locator.from_dict(call.data["locator"]),
                merge_mode=call.data.get("merge_mode") or MERGE_ENSURE_USER_BRANCH,
                fingerprint=call.data.get("fingerprint") or "",
                label=call.data.get("label") or "",
                breadcrumb=call.data.get("breadcrumb") or "",
            )
            await self.store.upsert_binding(binding)
            await self.async_maybe_autosync()

        async def unbind_element(call: ServiceCall) -> None:
            await self.store.delete_binding(call.data[ATTR_BINDING_ID])

        async def debug_dashboard(call: ServiceCall) -> dict[str, Any]:
            path = call.data.get("dashboard") or call.data.get(ATTR_DASHBOARD) or "lovelace"
            url_key: str | None = None if path in ("lovelace", "default") else str(path)
            dashboards = []
            try:
                dashboards = self.sync_engine.list_dashboards()
            except Exception as err:  # noqa: BLE001
                dashboards = [{"error": str(err)}]
            payload: dict[str, Any] = {
                "requested": path,
                "url_key": url_key,
                "dashboards": dashboards,
            }
            try:
                config = await self.sync_engine.async_get_lovelace_config(url_key)
                from .sync import build_dashboard_preview_tree, list_visibility_nodes

                tree = build_dashboard_preview_tree(config)
                nodes = list_visibility_nodes(config)
                payload.update(
                    {
                        "ok": True,
                        "config_keys": sorted(config.keys()),
                        "view_count": len(config.get("views") or []),
                        "view_titles": [
                            (v.get("title") or v.get("path") or f"view-{i}")
                            for i, v in enumerate(config.get("views") or [])
                            if isinstance(v, dict)
                        ],
                        "tree_count": len(tree),
                        "node_count": len(nodes),
                        "tree_summary": [
                            {
                                "label": v.get("label"),
                                "path": v.get("path"),
                                "sections": len(v.get("sections") or []),
                                "cards": len(v.get("cards") or []),
                            }
                            for v in tree
                        ],
                    }
                )
            except Exception as err:  # noqa: BLE001
                payload.update({"ok": False, "error": str(err)})
            return payload

        async def sync_now(call: ServiceCall) -> None:
            await self.sync_engine.async_sync(
                dashboard=call.data.get(ATTR_DASHBOARD),
                dry_run=call.data.get("dry_run"),
            )

        async def is_member_svc(call: ServiceCall) -> dict[str, Any]:
            group = self.store.get_group(call.data[ATTR_GROUP_ID])
            if not group:
                raise ValueError("Unknown group")
            uid = call.data[ATTR_USER_ID]
            return {
                ATTR_GROUP_ID: group.id,
                ATTR_USER_ID: uid,
                ATTR_IS_MEMBER: is_member(uid, group.member_user_ids),
                ATTR_MEMBERS: list(group.member_user_ids),
            }

        schemas = {
            "create_group": vol.Schema(
                {
                    vol.Required("name"): cv.string,
                    vol.Optional("group_id"): cv.string,
                    vol.Optional("description"): cv.string,
                    vol.Optional("icon"): cv.string,
                    vol.Optional("member_user_ids", default=[]): vol.All(
                        cv.ensure_list, [cv.string]
                    ),
                }
            ),
            "update_group": vol.Schema(
                {
                    vol.Required("group_id"): cv.string,
                    vol.Optional("name"): cv.string,
                    vol.Optional("description"): cv.string,
                    vol.Optional("icon"): cv.string,
                    vol.Optional("member_user_ids"): vol.All(
                        cv.ensure_list, [cv.string]
                    ),
                }
            ),
            "delete_group": vol.Schema({vol.Required("group_id"): cv.string}),
            "set_members": vol.Schema(
                {
                    vol.Required("group_id"): cv.string,
                    vol.Required("user_ids"): vol.All(cv.ensure_list, [cv.string]),
                }
            ),
            "add_members": vol.Schema(
                {
                    vol.Required("group_id"): cv.string,
                    vol.Required("user_ids"): vol.All(cv.ensure_list, [cv.string]),
                }
            ),
            "remove_members": vol.Schema(
                {
                    vol.Required("group_id"): cv.string,
                    vol.Required("user_ids"): vol.All(cv.ensure_list, [cv.string]),
                }
            ),
            "bind_element": vol.Schema(
                {
                    vol.Required("dashboard_url_path"): cv.string,
                    vol.Required("include"): vol.All(cv.ensure_list, [cv.string]),
                    vol.Optional("exclude", default=[]): vol.All(
                        cv.ensure_list, [cv.string]
                    ),
                    vol.Required("locator"): dict,
                    vol.Optional("merge_mode"): vol.In(list(MERGE_MODES)),
                    vol.Optional("fingerprint"): cv.string,
                    vol.Optional("label"): cv.string,
                    vol.Optional("breadcrumb"): cv.string,
                }
            ),
            "unbind_element": vol.Schema({vol.Required("binding_id"): cv.string}),
            "sync": vol.Schema(
                {
                    vol.Optional("dashboard"): cv.string,
                    vol.Optional("dry_run"): cv.boolean,
                }
            ),
            "debug_dashboard": vol.Schema(
                {
                    vol.Optional("dashboard"): cv.string,
                }
            ),
            "is_member": vol.Schema(
                {
                    vol.Required("group_id"): cv.string,
                    vol.Required("user_id"): cv.string,
                }
            ),
        }

        handlers = {
            "create_group": create_group,
            "update_group": update_group,
            "delete_group": delete_group,
            "set_members": set_members,
            "add_members": add_members,
            "remove_members": remove_members,
            "bind_element": bind_element,
            "unbind_element": unbind_element,
            "sync": sync_now,
        }
        for name, handler in handlers.items():
            self.hass.services.async_register(
                DOMAIN, name, handler, schema=schemas[name]
            )
        self.hass.services.async_register(
            DOMAIN,
            "is_member",
            is_member_svc,
            schema=schemas["is_member"],
            supports_response=SupportsResponse.ONLY,
        )
        self.hass.services.async_register(
            DOMAIN,
            "debug_dashboard",
            debug_dashboard,
            schema=schemas["debug_dashboard"],
            supports_response=SupportsResponse.ONLY,
        )
        self._services_registered = True
        _LOGGER.debug("Registered %s services", NAME)

    def unregister_services_if_last(self) -> None:
        remaining = [
            e
            for e in self.hass.config_entries.async_entries(DOMAIN)
        ]
        if remaining:
            return
        for name in (
            "create_group",
            "update_group",
            "delete_group",
            "set_members",
            "add_members",
            "remove_members",
            "bind_element",
            "unbind_element",
            "sync",
            "is_member",
            "debug_dashboard",
        ):
            if self.hass.services.has_service(DOMAIN, name):
                self.hass.services.async_remove(DOMAIN, name)
