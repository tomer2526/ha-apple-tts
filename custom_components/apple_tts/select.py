from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DATA_PREFERENCES,
    DATA_VOICES_BY_LANGUAGE,
    DEFAULT_LANGUAGE,
    DEFAULT_VOICE,
    DOMAIN,
    OPTION_LANGUAGE,
    OPTION_VOICE,
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
            AppleTTSLanguageSelect(config_entry, shared_data),
            AppleTTSVoiceSelect(config_entry, shared_data),
        ]
    )


class AppleTTSSelectBase(SelectEntity):
    _attr_has_entity_name = True

    def __init__(self, config_entry: ConfigEntry, shared_data: dict[str, Any]) -> None:
        self._entry = config_entry
        self._data = shared_data

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                _update_signal(self._entry.entry_id),
                self.async_write_ha_state,
            )
        )

    @property
    def _preferences(self) -> dict[str, Any]:
        return self._data[DATA_PREFERENCES]

    @property
    def _voices_by_language(self) -> dict[str, list[str]]:
        return self._data[DATA_VOICES_BY_LANGUAGE]


class AppleTTSLanguageSelect(AppleTTSSelectBase):
    _attr_name = "Language"
    _attr_icon = "mdi:translate"

    def __init__(self, config_entry: ConfigEntry, shared_data: dict[str, Any]) -> None:
        super().__init__(config_entry, shared_data)
        self._attr_unique_id = f"{config_entry.entry_id}_language"

    @property
    def options(self) -> list[str]:
        return sorted(self._voices_by_language) or [DEFAULT_LANGUAGE]

    @property
    def current_option(self) -> str:
        current = self._preferences.get(OPTION_LANGUAGE, DEFAULT_LANGUAGE)
        if current in self.options:
            return current
        return self.options[0]

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            return
        self._preferences[OPTION_LANGUAGE] = option

        current_voice = self._preferences.get(OPTION_VOICE)
        allowed_voices = self._voices_by_language.get(option, [])
        if current_voice not in allowed_voices:
            self._preferences[OPTION_VOICE] = (
                allowed_voices[0] if allowed_voices else DEFAULT_VOICE
            )

        async_dispatcher_send(self.hass, _update_signal(self._entry.entry_id))


class AppleTTSVoiceSelect(AppleTTSSelectBase):
    _attr_name = "Voice"
    _attr_icon = "mdi:account-voice"

    def __init__(self, config_entry: ConfigEntry, shared_data: dict[str, Any]) -> None:
        super().__init__(config_entry, shared_data)
        self._attr_unique_id = f"{config_entry.entry_id}_voice"

    @property
    def options(self) -> list[str]:
        language = self._preferences.get(OPTION_LANGUAGE, DEFAULT_LANGUAGE)
        voices = self._voices_by_language.get(language, [])
        return voices or [DEFAULT_VOICE]

    @property
    def current_option(self) -> str:
        current = self._preferences.get(OPTION_VOICE, DEFAULT_VOICE)
        if current in self.options:
            return current
        return self.options[0]

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            return
        self._preferences[OPTION_VOICE] = option
        async_dispatcher_send(self.hass, _update_signal(self._entry.entry_id))
