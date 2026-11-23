"""Config flow for HA Groups."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_AUTO_SYNC,
    CONF_DASHBOARDS,
    CONF_DRY_RUN,
    CONF_NORMALIZE_DUPLICATES,
    DEFAULT_AUTO_SYNC,
    DEFAULT_DRY_RUN,
    DEFAULT_NORMALIZE_DUPLICATES,
    DOMAIN,
    NAME,
)


async def _async_existing(hass: HomeAssistant) -> bool:
    return bool(hass.config_entries.async_entries(DOMAIN))


class HassioGroupsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA Groups (single instance)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if await _async_existing(self.hass):
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            return self.async_create_entry(
                title=NAME,
                data={},
                options={
                    CONF_AUTO_SYNC: bool(user_input.get(CONF_AUTO_SYNC, DEFAULT_AUTO_SYNC)),
                    CONF_DRY_RUN: bool(user_input.get(CONF_DRY_RUN, DEFAULT_DRY_RUN)),
                    CONF_NORMALIZE_DUPLICATES: bool(
                        user_input.get(
                            CONF_NORMALIZE_DUPLICATES, DEFAULT_NORMALIZE_DUPLICATES
                        )
                    ),
                    CONF_DASHBOARDS: list(user_input.get(CONF_DASHBOARDS) or []),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_AUTO_SYNC, default=DEFAULT_AUTO_SYNC): cv.boolean,
                    vol.Optional(CONF_DRY_RUN, default=DEFAULT_DRY_RUN): cv.boolean,
                    vol.Optional(
                        CONF_NORMALIZE_DUPLICATES, default=DEFAULT_NORMALIZE_DUPLICATES
                    ): cv.boolean,
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return HassioGroupsOptionsFlow(config_entry)


class HassioGroupsOptionsFlow(config_entries.OptionsFlow):
    """Options: auto-sync, dry-run, dashboard allowlist."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            dashboards_raw = user_input.get(CONF_DASHBOARDS) or ""
            if isinstance(dashboards_raw, str):
                dashboards = [d.strip() for d in dashboards_raw.split(",") if d.strip()]
            else:
                dashboards = list(dashboards_raw)
            return self.async_create_entry(
                title="",
                data={
                    CONF_AUTO_SYNC: bool(user_input.get(CONF_AUTO_SYNC, DEFAULT_AUTO_SYNC)),
                    CONF_DRY_RUN: bool(user_input.get(CONF_DRY_RUN, DEFAULT_DRY_RUN)),
                    CONF_NORMALIZE_DUPLICATES: bool(
                        user_input.get(
                            CONF_NORMALIZE_DUPLICATES, DEFAULT_NORMALIZE_DUPLICATES
                        )
                    ),
                    CONF_DASHBOARDS: dashboards,
                },
            )

        opts = self._entry.options
        current_dashboards = ", ".join(opts.get(CONF_DASHBOARDS) or [])
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_AUTO_SYNC,
                        default=opts.get(CONF_AUTO_SYNC, DEFAULT_AUTO_SYNC),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_DRY_RUN, default=opts.get(CONF_DRY_RUN, DEFAULT_DRY_RUN)
                    ): cv.boolean,
                    vol.Optional(
                        CONF_NORMALIZE_DUPLICATES,
                        default=opts.get(
                            CONF_NORMALIZE_DUPLICATES, DEFAULT_NORMALIZE_DUPLICATES
                        ),
                    ): cv.boolean,
                    vol.Optional(CONF_DASHBOARDS, default=current_dashboards): str,
                }
            ),
        )
