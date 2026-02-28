from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DATA_PREFERENCES,
    DEFAULT_PITCH,
    DEFAULT_RATE,
    DEFAULT_VOLUME,
    DOMAIN,
    MAX_PITCH,
    MAX_RATE,
    MAX_VOLUME,
    MIN_PITCH,
    MIN_RATE,
    MIN_VOLUME,
    OPTION_PITCH,
    OPTION_RATE,
    OPTION_VOLUME,
)


def _update_signal(entry_id: str) -> str:
    return f"{DOMAIN}_{entry_id}_prefs_updated"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    shared_data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            AppleTTSNumberEntity(
                config_entry,
                shared_data,
                name="Rate",
                key=OPTION_RATE,
                default=DEFAULT_RATE,
                minimum=MIN_RATE,
                maximum=MAX_RATE,
                step=1,
                icon="mdi:speedometer",
            ),
            AppleTTSNumberEntity(
                config_entry,
                shared_data,
                name="Pitch",
                key=OPTION_PITCH,
                default=DEFAULT_PITCH,
                minimum=MIN_PITCH,
                maximum=MAX_PITCH,
                step=1,
                icon="mdi:tune-vertical",
            ),
            AppleTTSNumberEntity(
                config_entry,
                shared_data,
                name="Volume",
                key=OPTION_VOLUME,
                default=DEFAULT_VOLUME,
                minimum=MIN_VOLUME,
                maximum=MAX_VOLUME,
                step=1,
                icon="mdi:volume-high",
            ),
        ]
    )


class AppleTTSNumberEntity(NumberEntity):
    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        config_entry: ConfigEntry,
        shared_data: dict[str, Any],
        *,
        name: str,
        key: str,
        default: int,
        minimum: int,
        maximum: int,
        step: int,
        icon: str,
    ) -> None:
        self._entry_id = config_entry.entry_id
        self._data = shared_data
        self._key = key
        self._default = default
        self._attr_unique_id = f"{config_entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_native_min_value = float(minimum)
        self._attr_native_max_value = float(maximum)
        self._attr_native_step = float(step)
        self._attr_icon = icon

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                _update_signal(self._entry_id),
                self.async_write_ha_state,
            )
        )

    @property
    def native_value(self) -> float:
        return float(self._preferences.get(self._key, self._default))

    async def async_set_native_value(self, value: float) -> None:
        clipped = min(self.native_max_value, max(self.native_min_value, value))
        self._preferences[self._key] = int(round(clipped))
        async_dispatcher_send(self.hass, _update_signal(self._entry_id))

    @property
    def _preferences(self) -> dict[str, Any]:
        return self._data[DATA_PREFERENCES]
