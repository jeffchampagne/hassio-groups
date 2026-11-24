"""Viz Groups admin panel registration + websocket API."""

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
from .membership import MEMBER_TYPE_GROUP, MEMBER_TYPE_USER, flatten_group_users
from .models import GroupExpression, Locator, new_binding, new_group, utcnow_iso
from .sync import (
    audit_dashboard_user_visibility,
    build_dashboard_preview_tree,
    list_visibility_nodes,
)


def _patch_binding_breadcrumb_serialization() -> None:
    """Ensure Binding.to_dict always emits breadcrumb (config-entry soft reload)."""
    from . import models

    binding_cls = models.Binding
    if getattr(binding_cls, "_vg_breadcrumb_to_dict", False):
        return
    original = binding_cls.to_dict

    def to_dict(self: Any) -> dict[str, Any]:
        data = original(self)
        data["breadcrumb"] = str(
            getattr(self, "breadcrumb", None) or data.get("breadcrumb") or ""
        )
        return data

    binding_cls.to_dict = to_dict  # type: ignore[method-assign]
    binding_cls._vg_breadcrumb_to_dict = True


_patch_binding_breadcrumb_serialization()


class _NoRuntime(RuntimeError):
    """Raised when Viz Groups has no active runtime."""


async def async_register_panel(hass: HomeAssistant) -> None:
    """Serve the Lit panel module and add the sidebar entry once."""
    import logging

    _log = logging.getLogger(__name__)
    bucket = hass.data.setdefault(DOMAIN, {})
    module = Path(__file__).parent / "frontend" / "panel.js"
    static_url = PANEL_MODULE_URL.split("?", 1)[0]
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(static_url, str(module), False)]
        )
    except Exception as err:  # noqa: BLE001
        # Path may already be registered after a soft reload.
        _log.debug("Viz Groups static path register skipped: %s", err)
    if bucket.get("panel"):
        bucket["panel_module_url"] = PANEL_MODULE_URL
        return
    try:
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
    except Exception as err:  # noqa: BLE001
        _log.warning("Viz Groups panel register: %s", err)
        # Still mark registered so setup_entry can proceed.
    bucket["panel"] = True
    bucket["panel_module_url"] = PANEL_MODULE_URL


def async_register_websocket(hass: HomeAssistant) -> None:
    """Register admin-only websocket commands for the panel.

    Callers should importlib.reload this module (and sync) before invoking so
    disk updates are picked up. Re-register replaces handlers by command type.
    """
    _patch_binding_breadcrumb_serialization()
    bucket = hass.data.setdefault(DOMAIN, {})
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_list_users)
    websocket_api.async_register_command(hass, ws_save_group)
    websocket_api.async_register_command(hass, ws_delete_group)
    websocket_api.async_register_command(hass, ws_save_binding)
    websocket_api.async_register_command(hass, ws_delete_binding)
    websocket_api.async_register_command(hass, ws_sync)
    websocket_api.async_register_command(hass, ws_dashboard_nodes)
    websocket_api.async_register_command(hass, ws_visibility_audit)
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


def _disk_binding_breadcrumbs(hass: HomeAssistant) -> dict[str, str]:
    """Read breadcrumb strings from on-disk store (survives soft-reload class skew)."""
    import json

    try:
        raw = Path(hass.config.path(f".storage/{DOMAIN}")).read_text(encoding="utf-8")
        data = json.loads(raw)
        out: dict[str, str] = {}
        for item in (data.get("data") or data).get("bindings") or []:
            bid = item.get("id")
            crumb = str(item.get("breadcrumb") or "").strip()
            if bid and crumb:
                out[str(bid)] = crumb
        return out
    except Exception:  # noqa: BLE001
        return {}


def _looks_like_entity_id(text: str) -> bool:
    """True for ``domain.object_id`` style ids (no spaces)."""
    raw = (text or "").strip()
    if not raw or " " in raw or raw.count(".") != 1:
        return False
    domain, object_id = raw.split(".", 1)
    if not domain or not object_id:
        return False
    return domain.replace("_", "").isalnum() and all(
        ch.isalnum() or ch == "_" for ch in object_id
    )


def _entity_friendly_name(hass: HomeAssistant, entity_id: str) -> str | None:
    """Return HA friendly_name for an entity_id when available."""
    state = hass.states.get(entity_id)
    if state is not None:
        name = state.attributes.get("friendly_name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    try:
        from homeassistant.helpers import entity_registry as er

        reg = er.async_get(hass)
        entry = reg.async_get(entity_id)
        if entry is not None:
            for candidate in (entry.name, entry.original_name):
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
    except Exception:  # noqa: BLE001
        pass
    return None


def _resolve_display_text(hass: HomeAssistant, text: str) -> str:
    """Prefer friendly names when ``text`` (or breadcrumb segments) are entity ids."""
    raw = (text or "").strip()
    if not raw:
        return raw
    if " › " in raw:
        parts = [
            _resolve_display_text(hass, part) for part in raw.split(" › ")
        ]
        return " › ".join(parts)
    if _looks_like_entity_id(raw):
        friendly = _entity_friendly_name(hass, raw)
        if friendly:
            return friendly
    return raw


def _enrich_label_fields(hass: HomeAssistant, payload: dict[str, Any]) -> dict[str, Any]:
    """Resolve entity-id labels/breadcrumbs in a node/audit/binding dict."""
    if not isinstance(payload, dict):
        return payload
    for key in ("label", "breadcrumb", "snippet", "binding_label"):
        if key in payload and isinstance(payload[key], str) and payload[key]:
            payload[key] = _resolve_display_text(hass, payload[key])
    return payload


def _binding_to_dict(
    binding: Any,
    disk_crumbs: dict[str, str] | None = None,
    hass: HomeAssistant | None = None,
) -> dict[str, Any]:
    """Serialize a binding, always including breadcrumb (soft-reload safe)."""
    data = binding.to_dict()
    crumb = str(
        getattr(binding, "breadcrumb", None) or data.get("breadcrumb") or ""
    ).strip()
    if not crumb and disk_crumbs:
        crumb = disk_crumbs.get(str(data.get("id") or getattr(binding, "id", "")), "")
    label = str(getattr(binding, "label", None) or data.get("label") or "").strip()
    if hass is not None:
        label = _resolve_display_text(hass, label)
        crumb = _resolve_display_text(hass, crumb)
    data["label"] = label
    data["breadcrumb"] = crumb
    if crumb:
        try:
            binding.breadcrumb = crumb
        except Exception:  # noqa: BLE001
            pass
    if label and hass is not None:
        try:
            # Persist friendly name when the stored label was a raw entity_id.
            if _looks_like_entity_id(str(getattr(binding, "label", "") or "")):
                binding.label = label
        except Exception:  # noqa: BLE001
            pass
    return data


async def _async_backfill_binding_breadcrumbs(runtime: Any) -> bool:
    """Fill binding.breadcrumb from Lovelace node paths; return True if saved."""
    from .sync import list_visibility_nodes, locators_match

    by_dash: dict[str, list[Any]] = {}
    for binding in runtime.store.bindings.values():
        path = binding.dashboard_url_path or "lovelace"
        by_dash.setdefault(path, []).append(binding)

    changed = False
    hass = runtime.hass

    # Always resolve entity-id labels / breadcrumb segments to friendly names.
    for binding in runtime.store.bindings.values():
        current_label = str(getattr(binding, "label", "") or "")
        resolved_label = _resolve_display_text(hass, current_label)
        if resolved_label and resolved_label != current_label:
            binding.label = resolved_label
            changed = True
        current_crumb = str(getattr(binding, "breadcrumb", "") or "")
        resolved_crumb = _resolve_display_text(hass, current_crumb)
        if resolved_crumb and resolved_crumb != current_crumb:
            binding.breadcrumb = resolved_crumb
            changed = True

    for path, bindings in by_dash.items():
        url_key: str | None = None if path in ("lovelace", "default") else path
        try:
            config = await runtime.sync_engine.async_get_lovelace_config(url_key)
        except Exception:  # noqa: BLE001
            continue
        nodes = list_visibility_nodes(config)
        for binding in bindings:
            for node in nodes:
                if not locators_match(binding.locator, node.get("locator")):
                    continue
                crumb = _resolve_display_text(
                    hass, str(node.get("breadcrumb") or "")
                )
                if crumb and getattr(binding, "breadcrumb", "") != crumb:
                    binding.breadcrumb = crumb
                    changed = True
                node_label = _resolve_display_text(
                    hass, str(node.get("label") or "")
                )
                current_label = str(getattr(binding, "label", "") or "")
                if node_label and (
                    not current_label
                    or _looks_like_entity_id(current_label)
                    or current_label == str(node.get("label") or "")
                ):
                    if current_label != node_label:
                        binding.label = node_label
                        changed = True
                break
    if changed:
        await runtime.store.async_save()
    return changed



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
            "warning": "Viz Groups is not set up yet.",
        }

    users = runtime.list_users_for_panel()
    users_by_id = {u["id"]: u for u in users}
    groups_by_id = {g.id: g for g in runtime.store.groups.values()}
    members_tree = runtime.store.members_tree()
    effective_by_group = runtime.store.members_by_group()
    groups = []
    for group in runtime.store.groups.values():
        member_rows = []
        nested_group_rows = []
        for member in group.members:
            if member.type == MEMBER_TYPE_USER:
                info = users_by_id.get(member.id)
                member_rows.append(
                    {
                        "type": MEMBER_TYPE_USER,
                        "id": member.id,
                        "name": (info or {}).get("name") or member.id,
                        "is_person": bool((info or {}).get("is_person")),
                    }
                )
            elif member.type == MEMBER_TYPE_GROUP:
                nested = groups_by_id.get(member.id)
                nested_group_rows.append(
                    {
                        "type": MEMBER_TYPE_GROUP,
                        "id": member.id,
                        "name": (nested.name if nested else None) or member.id,
                        "icon": (nested.icon if nested else None) or "mdi:account-group",
                        "missing": nested is None,
                    }
                )
                # Expand one level for editor UI (users + further nested groups).
                child_members = []
                if nested is not None:
                    for child in nested.members:
                        if child.type == MEMBER_TYPE_USER:
                            info = users_by_id.get(child.id)
                            child_members.append(
                                {
                                    "type": MEMBER_TYPE_USER,
                                    "id": child.id,
                                    "name": (info or {}).get("name") or child.id,
                                }
                            )
                        elif child.type == MEMBER_TYPE_GROUP:
                            cg = groups_by_id.get(child.id)
                            child_members.append(
                                {
                                    "type": MEMBER_TYPE_GROUP,
                                    "id": child.id,
                                    "name": (cg.name if cg else None) or child.id,
                                    "icon": (cg.icon if cg else None)
                                    or "mdi:account-group",
                                    "missing": cg is None,
                                }
                            )
                nested_group_rows[-1]["members"] = child_members
                nested_group_rows[-1]["effective_user_count"] = len(
                    flatten_group_users(member.id, members_tree)
                )
        effective_users = effective_by_group.get(group.id, [])
        groups.append(
            {
                **group.to_dict(),
                # Typed rows for UI (users + nested groups, direct membership).
                "members": member_rows + nested_group_rows,
                "member_count": len(group.members),
                "effective_user_ids": effective_users,
                "effective_user_count": len(effective_users),
                "nested_groups": nested_group_rows,
            }
        )
    groups.sort(key=lambda g: g["name"].casefold())

    disk_crumbs = _disk_binding_breadcrumbs(hass)
    bindings = [
        _binding_to_dict(b, disk_crumbs, hass) for b in runtime.store.bindings.values()
    ]
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
    try:
        await _async_backfill_binding_breadcrumbs(_runtime(hass))
    except Exception:  # noqa: BLE001
        pass
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
    try:
        runtime = _runtime(hass)
    except _NoRuntime:
        connection.send_result(msg["id"], [])
        return
    connection.send_result(msg["id"], runtime.list_users_for_panel())


def _apply_ws_members(runtime: Any, group: Any, msg: dict[str, Any]) -> None:
    """Apply members / legacy member_* fields from a websocket save payload."""
    if not any(k in msg for k in ("members", "member_user_ids", "member_group_ids")):
        return
    runtime.store.apply_members_payload(
        group,
        members=msg.get("members") if "members" in msg else None,
        member_user_ids=msg.get("member_user_ids") if "member_user_ids" in msg else None,
        member_group_ids=msg.get("member_group_ids")
        if "member_group_ids" in msg
        else None,
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/save_group",
        vol.Required("name"): str,
        vol.Optional("group_id"): str,
        vol.Optional("previous_group_id"): str,
        vol.Optional("description"): str,
        vol.Optional("icon"): str,
        vol.Optional("member_user_ids"): [str],
        vol.Optional("member_group_ids"): [str],
        vol.Optional("members"): [dict],
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
        _apply_ws_members(runtime, existing, msg)
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
            _apply_ws_members(runtime, existing, msg)
            existing.updated = utcnow_iso()
            await runtime.store.upsert_group(existing)
        else:
            group = new_group(
                name=msg["name"].strip(),
                group_id=group_id,
                description=(msg.get("description") or "").strip(),
                icon=(msg.get("icon") or "mdi:account-group").strip(),
                members=msg.get("members"),
                member_user_ids=list(msg.get("member_user_ids") or []),
                member_group_ids=list(msg.get("member_group_ids") or []),
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
        vol.Optional("breadcrumb"): str,
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
        if "breadcrumb" in msg:
            existing.breadcrumb = msg.get("breadcrumb") or ""
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
            breadcrumb=msg.get("breadcrumb") or "",
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
    try:
        await _async_backfill_binding_breadcrumbs(runtime)
    except Exception:  # noqa: BLE001
        pass
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
    nodes = list_visibility_nodes(config)
    tree = build_dashboard_preview_tree(config)

    def _walk_tree(items: list[Any]) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            _enrich_label_fields(hass, item)
            for key in ("cards", "sections", "children"):
                kids = item.get(key)
                if isinstance(kids, list):
                    _walk_tree(kids)

    for node in nodes:
        _enrich_label_fields(hass, node)
    _walk_tree(tree)
    connection.send_result(
        msg["id"],
        {
            "nodes": nodes,
            "tree": tree,
            "dashboard_url_path": path,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/visibility_audit",
        vol.Required("dashboard_url_path"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_visibility_audit(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Scan a dashboard for condition:user visibility vs Viz Groups bindings."""
    runtime = _runtime(hass)
    path = msg["dashboard_url_path"]
    url_key: str | None = None if path in ("lovelace", "default") else path
    try:
        config = await runtime.sync_engine.async_get_lovelace_config(url_key)
    except Exception as err:  # noqa: BLE001
        connection.send_error(msg["id"], "dashboard_error", str(err))
        return
    report = audit_dashboard_user_visibility(
        config,
        dashboard_url_path=path,
        bindings=list(runtime.store.bindings.values()),
    )
    for row in report.get("elements") or []:
        if isinstance(row, dict):
            _enrich_label_fields(hass, row)
    connection.send_result(msg["id"], report)


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
        connection.send_error(msg["id"], "no_entry", "Viz Groups has no config entry")
        return
    options = dict(entry.options)
    if "auto_sync" in msg:
        options[CONF_AUTO_SYNC] = bool(msg["auto_sync"])
    hass.config_entries.async_update_entry(entry, options=options)
    runtime.entry = entry
    runtime.sync_engine.options = dict(options)
    connection.send_result(msg["id"], panel_snapshot(hass))
