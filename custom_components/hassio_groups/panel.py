"""HA Groups admin panel registration + websocket API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_AUTO_SYNC,
    DEFAULT_AUTO_SYNC,
    DOMAIN,
    MERGE_ENSURE_USER_BRANCH,
    MERGE_MODES,
    NAME,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_MODULE_URL,
    PANEL_PATH,
)
from .models import GroupExpression, Locator, new_binding, new_group, utcnow_iso
from .sync import build_dashboard_preview_tree, list_visibility_nodes


class _NoRuntime(RuntimeError):
    """Raised when HA Groups has no active runtime."""


async def async_register_panel(hass: HomeAssistant) -> None:
    """Serve the Lit panel module and add the sidebar entry once."""
    bucket = hass.data.setdefault(DOMAIN, {})
    if bucket.get("panel"):
        return
    module = Path(__file__).parent / "frontend" / "panel.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_MODULE_URL, str(module), False)]
    )
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title=NAME,
        sidebar_icon=PANEL_ICON,
        module_url=PANEL_MODULE_URL,
        require_admin=True,
        embed_iframe=False,
        config={"domain": DOMAIN},
    )
    bucket["panel"] = True


def async_register_websocket(hass: HomeAssistant) -> None:
    """Register admin-only websocket commands for the panel.

    Always (re)register so file updates on disk are picked up after config-entry
    reload without requiring a full Core restart. HA keeps a command dict keyed
    by ``type``; registering again replaces the handler.
    """
    bucket = hass.data.setdefault(DOMAIN, {})
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_list_users)
    websocket_api.async_register_command(hass, ws_save_group)
    websocket_api.async_register_command(hass, ws_delete_group)
    websocket_api.async_register_command(hass, ws_save_binding)
    websocket_api.async_register_command(hass, ws_delete_binding)
    websocket_api.async_register_command(hass, ws_sync)
    websocket_api.async_register_command(hass, ws_dashboard_nodes)
    websocket_api.async_register_command(hass, ws_update_options)
    bucket["websocket"] = True


def _runtime(hass: HomeAssistant) -> Any:
    bucket = hass.data.get(DOMAIN) or {}
    for key, value in bucket.items():
        if key in ("panel", "websocket"):
            continue
        if hasattr(value, "store"):
            return value
    raise _NoRuntime()


def panel_snapshot(hass: HomeAssistant) -> dict[str, Any]:
    """Build panel payload with friendly names primary."""
    try:
        runtime = _runtime(hass)
    except _NoRuntime:
        return {
            "groups": [],
            "bindings": [],
            "users": [],
            "sync": {},
            "warning": "HA Groups is not set up yet.",
        }

    users = runtime.list_users_for_panel()
    groups = []
    for group in runtime.store.groups.values():
        member_rows = []
        for uid in group.member_user_ids:
            info = next((u for u in users if u["id"] == uid), None)
            member_rows.append(
                {
                    "id": uid,
                    "name": (info or {}).get("name") or uid,
                    "is_person": bool((info or {}).get("is_person")),
                }
            )
        groups.append(
            {
                **group.to_dict(),
                "members": member_rows,
                "member_count": len(group.member_user_ids),
            }
        )
    groups.sort(key=lambda g: g["name"].casefold())

    bindings = [b.to_dict() for b in runtime.store.bindings.values()]
    bindings.sort(
        key=lambda b: (b.get("dashboard_url_path") or "", b.get("label") or b["id"])
    )

    dashboards: list[dict[str, Any]] = []
    try:
        dashboards = runtime.sync_engine.list_dashboards()
    except Exception:  # noqa: BLE001
        dashboards = [{"url_path": "lovelace", "title": "Overview", "mode": "storage"}]

    return {
        "groups": groups,
        "bindings": bindings,
        "users": users,
        "dashboards": dashboards,
        "sync": runtime.store.sync_meta.to_dict(),
        "options": dict(runtime.entry.options) if runtime.entry else {},
    }


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_subscribe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Push an initial snapshot to the panel."""

    @callback
    def _noop() -> None:
        return None

    connection.subscriptions[msg["id"]] = _noop
    connection.send_result(msg["id"])
    connection.send_message(
        websocket_api.event_message(
            msg["id"], {"event": "snapshot", **panel_snapshot(hass)}
        )
    )


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list_users"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_list_users(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    connection.send_result(msg["id"], panel_snapshot(hass).get("users", []))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/save_group",
        vol.Required("name"): str,
        vol.Optional("group_id"): str,
        vol.Optional("previous_group_id"): str,
        vol.Optional("description"): str,
        vol.Optional("icon"): str,
        vol.Optional("member_user_ids"): [str],
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_save_group(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    runtime = _runtime(hass)
    group_id = (msg.get("group_id") or "").strip() or None
    previous_id = (msg.get("previous_group_id") or "").strip() or None
    # Rename when editing an existing group to a new id.
    if previous_id and group_id and previous_id != group_id:
        try:
            existing = await runtime.store.rename_group(previous_id, group_id)
        except ValueError as err:
            connection.send_error(msg["id"], "rename_failed", str(err))
            return
        existing.name = msg["name"].strip()
        existing.description = (msg.get("description") or "").strip()
        existing.icon = (
            msg.get("icon") or existing.icon or "mdi:account-group"
        ).strip()
        if "member_user_ids" in msg:
            existing.member_user_ids = list(msg.get("member_user_ids") or [])
        existing.updated = utcnow_iso()
        await runtime.store.upsert_group(existing)
    else:
        lookup_id = previous_id or group_id
        existing = runtime.store.get_group(lookup_id) if lookup_id else None
        if existing:
            existing.name = msg["name"].strip()
            existing.description = (msg.get("description") or "").strip()
            existing.icon = (
                msg.get("icon") or existing.icon or "mdi:account-group"
            ).strip()
            if "member_user_ids" in msg:
                existing.member_user_ids = list(msg.get("member_user_ids") or [])
            existing.updated = utcnow_iso()
            await runtime.store.upsert_group(existing)
        else:
            group = new_group(
                name=msg["name"].strip(),
                group_id=group_id,
                description=(msg.get("description") or "").strip(),
                icon=(msg.get("icon") or "mdi:account-group").strip(),
                member_user_ids=list(msg.get("member_user_ids") or []),
            )
            if runtime.store.get_group(group.id):
                connection.send_error(
                    msg["id"], "exists", f"Group {group.id} already exists"
                )
                return
            await runtime.store.upsert_group(group)
    await runtime.async_refresh_sensors()
    await runtime.async_maybe_autosync()
    connection.send_result(msg["id"], panel_snapshot(hass))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/delete_group",
        vol.Required("group_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_delete_group(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    runtime = _runtime(hass)
    await runtime.store.delete_group(msg["group_id"])
    await runtime.async_refresh_sensors()
    await runtime.async_maybe_autosync()
    connection.send_result(msg["id"], panel_snapshot(hass))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/save_binding",
        vol.Optional("binding_id"): str,
        vol.Required("dashboard_url_path"): str,
        vol.Required("include"): [str],
        vol.Optional("exclude"): [str],
        vol.Required("locator"): dict,
        vol.Optional("merge_mode"): vol.In(list(MERGE_MODES)),
        vol.Optional("fingerprint"): str,
        vol.Optional("label"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_save_binding(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    runtime = _runtime(hass)
    include = list(msg.get("include") or [])
    if not include:
        connection.send_error(
            msg["id"], "include_required", "At least one include group is required"
        )
        return
    binding_id = (msg.get("binding_id") or "").strip() or None
    existing = runtime.store.get_binding(binding_id) if binding_id else None
    expression = GroupExpression(
        include=include, exclude=list(msg.get("exclude") or [])
    )
    locator = Locator.from_dict(msg["locator"])
    if existing:
        existing.expression = expression
        existing.dashboard_url_path = msg["dashboard_url_path"]
        existing.locator = locator
        existing.merge_mode = msg.get("merge_mode") or existing.merge_mode
        if "fingerprint" in msg:
            existing.fingerprint = msg.get("fingerprint") or ""
        if "label" in msg:
            existing.label = msg.get("label") or ""
        existing.updated = utcnow_iso()
        existing.stale = False
        await runtime.store.upsert_binding(existing)
    else:
        binding = new_binding(
            expression=expression,
            dashboard_url_path=msg["dashboard_url_path"],
            locator=locator,
            merge_mode=msg.get("merge_mode") or MERGE_ENSURE_USER_BRANCH,
            fingerprint=msg.get("fingerprint") or "",
            label=msg.get("label") or "",
            binding_id=binding_id,
        )
        await runtime.store.upsert_binding(binding)
    await runtime.async_maybe_autosync()
    connection.send_result(msg["id"], panel_snapshot(hass))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/delete_binding",
        vol.Required("binding_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_delete_binding(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    runtime = _runtime(hass)
    await runtime.store.delete_binding(msg["binding_id"])
    connection.send_result(msg["id"], panel_snapshot(hass))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/sync",
        vol.Optional("dashboard"): str,
        vol.Optional("dry_run"): cv.boolean,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_sync(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    runtime = _runtime(hass)
    summary = await runtime.sync_engine.async_sync(
        dashboard=msg.get("dashboard"),
        dry_run=msg.get("dry_run"),
    )
    snap = panel_snapshot(hass)
    snap["last_sync_result"] = summary
    connection.send_result(msg["id"], snap)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/dashboard_nodes",
        vol.Required("dashboard_url_path"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_dashboard_nodes(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    runtime = _runtime(hass)
    path = msg["dashboard_url_path"]
    url_key: str | None = None if path in ("lovelace", "default") else path
    try:
        config = await runtime.sync_engine.async_get_lovelace_config(url_key)
    except Exception as err:  # noqa: BLE001
        connection.send_error(msg["id"], "dashboard_error", str(err))
        return
    connection.send_result(
        msg["id"],
        {
            "nodes": list_visibility_nodes(config),
            "tree": build_dashboard_preview_tree(config),
            "dashboard_url_path": path,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/update_options",
        vol.Optional("auto_sync"): cv.boolean,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_update_options(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Update config-entry options from the panel (e.g. auto_sync)."""
    runtime = _runtime(hass)
    entry = runtime.entry
    if entry is None:
        connection.send_error(msg["id"], "no_entry", "HA Groups has no config entry")
        return
    options = dict(entry.options)
    if "auto_sync" in msg:
        options[CONF_AUTO_SYNC] = bool(msg["auto_sync"])
    hass.config_entries.async_update_entry(entry, options=options)
    runtime.entry = entry
    runtime.sync_engine.options = dict(options)
    connection.send_result(msg["id"], panel_snapshot(hass))
