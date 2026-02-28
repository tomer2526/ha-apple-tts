from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .control import async_shutdown_server
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([AppleTTSShutdownButton(config_entry)])


class AppleTTSShutdownButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Shutdown Server"
    _attr_icon = "mdi:server-off"

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry_id = config_entry.entry_id
        self._attr_unique_id = f"{config_entry.entry_id}_shutdown_server"

    async def async_press(self) -> None:
        entry_data = self.hass.data[DOMAIN][self._entry_id]
        await async_shutdown_server(self.hass, entry_data)
