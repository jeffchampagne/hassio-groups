"""Voluptuous schemas shared by websocket + service registration.

Kept free of Home Assistant imports so unit tests can load this module with
only ``voluptuous`` installed.
"""

from __future__ import annotations

import voluptuous as vol

from .membership import MEMBER_TYPES

# Allow extra keys (name/icon) so enriched snapshot rows still validate if
# a client echoes them back; type + id are the only required fields.
MEMBER_REF_SCHEMA = vol.Schema(
    {
        vol.Required("type"): vol.In(list(MEMBER_TYPES)),
        vol.Required("id"): vol.All(str, vol.Length(min=1)),
    },
    extra=vol.ALLOW_EXTRA,
)

# Legacy bare user-id strings remain accepted alongside typed refs.
MEMBER_ITEM_SCHEMA = vol.Any(
    MEMBER_REF_SCHEMA,
    vol.All(str, vol.Length(min=1)),
)

MEMBERS_LIST = vol.All(list, [MEMBER_ITEM_SCHEMA])
STRING_LIST = vol.All(list, [str])


def ws_save_group_schema(domain: str) -> dict:
    """Websocket command dict for ``{domain}/save_group`` (typed members)."""
    return {
        vol.Required("type"): f"{domain}/save_group",
        vol.Required("name"): str,
        vol.Optional("group_id"): str,
        vol.Optional("previous_group_id"): str,
        vol.Optional("description"): str,
        vol.Optional("icon"): str,
        vol.Optional("member_user_ids"): STRING_LIST,
        vol.Optional("member_group_ids"): STRING_LIST,
        vol.Optional("members"): MEMBERS_LIST,
    }
