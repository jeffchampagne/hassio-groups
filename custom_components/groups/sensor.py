"""Group membership sensors for Viz Groups."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_GROUP_ID, ATTR_MEMBER_NAMES, ATTR_MEMBERS, DOMAIN
from .models import Group


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up membership sensors from the runtime."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    runtime.sensor_add_entities = async_add_entities
    entities = [
        GroupMembershipSensor(runtime, group) for group in runtime.store.groups.values()
    ]
    if entities:
        async_add_entities(entities)
    runtime.sensors = {e.group_id: e for e in entities}


class GroupMembershipSensor(SensorEntity):
    """Expose member count + members attribute for automations."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:account-group"

    def __init__(self, runtime: Any, group: Group) -> None:
        self._runtime = runtime
        self._group = group
        self._attr_unique_id = f"{DOMAIN}_{group.id}"
        self._attr_name = group.name
        self._attr_native_value = len(group.member_user_ids)

    @property
    def group_id(self) -> str:
        return self._group.id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        names = self._runtime.display_names_for(self._group.member_user_ids)
        return {
            ATTR_GROUP_ID: self._group.id,
            ATTR_MEMBERS: list(self._group.member_user_ids),
            ATTR_MEMBER_NAMES: names,
            "description": self._group.description,
            "icon": self._group.icon,
        }

    @callback
    def apply_group(self, group: Group) -> None:
        self._group = group
        self._attr_name = group.name
        self._attr_native_value = len(group.member_user_ids)
        self._attr_icon = group.icon or "mdi:account-group"
        self.async_write_ha_state()
