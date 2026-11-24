"""Regression: save_group voluptuous schema accepts typed members."""

from __future__ import annotations

import voluptuous as vol

from vizgroups.const import DOMAIN
from vizgroups.schemas import (
    MEMBER_ITEM_SCHEMA,
    MEMBER_REF_SCHEMA,
    MEMBERS_LIST,
    ws_save_group_schema,
)


def _validate_ws(payload: dict):
    """Validate like HA websocket_api (PREVENT_EXTRA on the command dict)."""
    schema = vol.Schema(
        {
            vol.Required("id"): int,
            **ws_save_group_schema(DOMAIN),
        },
        extra=vol.PREVENT_EXTRA,
    )
    return schema(payload)


def test_save_group_schema_accepts_typed_user_and_group_members() -> None:
    """UI nested-groups payload must not raise 'extra keys not allowed @ members'."""
    result = _validate_ws(
        {
            "id": 1,
            "type": f"{DOMAIN}/save_group",
            "name": "Leaders",
            "group_id": "leaders",
            "previous_group_id": "leaders",
            "description": "",
            "icon": "mdi:account-group",
            "members": [
                {"type": "user", "id": "abc-user-1"},
                {"type": "user", "id": "abc-user-2"},
                {"type": "group", "id": "24-7-building-access"},
            ],
        }
    )
    assert result["members"][2]["type"] == "group"
    assert result["members"][2]["id"] == "24-7-building-access"


def test_save_group_schema_rejects_members_when_key_omitted_from_schema() -> None:
    """Document the live bug: legacy schema without members rejects the key."""
    legacy = vol.Schema(
        {
            vol.Required("id"): int,
            vol.Required("type"): f"{DOMAIN}/save_group",
            vol.Required("name"): str,
            vol.Optional("group_id"): str,
            vol.Optional("member_user_ids"): [str],
        },
        extra=vol.PREVENT_EXTRA,
    )
    try:
        legacy(
            {
                "id": 1,
                "type": f"{DOMAIN}/save_group",
                "name": "Leaders",
                "members": [{"type": "group", "id": "24-7-building-access"}],
            }
        )
        raise AssertionError("expected vol.Invalid")
    except vol.Invalid as err:
        assert "members" in str(err)


def test_save_group_schema_keeps_legacy_member_fields() -> None:
    result = _validate_ws(
        {
            "id": 2,
            "type": f"{DOMAIN}/save_group",
            "name": "Teachers",
            "member_user_ids": ["u1", "u2"],
            "member_group_ids": ["staff"],
        }
    )
    assert result["member_user_ids"] == ["u1", "u2"]
    assert result["member_group_ids"] == ["staff"]


def test_member_ref_allows_enriched_extra_keys() -> None:
    parsed = MEMBER_REF_SCHEMA(
        {"type": "group", "id": "staff", "name": "Staff", "icon": "mdi:school"}
    )
    assert parsed["id"] == "staff"
    assert parsed["name"] == "Staff"


def test_members_list_accepts_legacy_bare_user_ids() -> None:
    assert MEMBERS_LIST(["u1", {"type": "group", "id": "g1"}]) == [
        "u1",
        {"type": "group", "id": "g1"},
    ]


def test_member_item_rejects_unknown_type() -> None:
    try:
        MEMBER_ITEM_SCHEMA({"type": "robot", "id": "x"})
        raise AssertionError("expected vol.Invalid")
    except vol.Invalid:
        pass
