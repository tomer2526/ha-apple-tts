from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import fetch_voices_by_language
from .const import (
    CONF_HOST,
    CONF_PORT,
    DATA_PREFERENCES,
    DATA_VOICES_BY_LANGUAGE,
    DEFAULT_LANGUAGE,
    DEFAULT_PITCH,
    DEFAULT_RATE,
    DEFAULT_VOLUME,
    DEFAULT_VOICE,
    DOMAIN,
    OPTION_LANGUAGE,
    OPTION_PITCH,
    OPTION_RATE,
    OPTION_VOLUME,
    OPTION_VOICE,
)

PLATFORMS = ["tts", "select", "number"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    voices_by_language = await hass.async_add_executor_job(
        fetch_voices_by_language,
        host,
        port,
    )

    language = DEFAULT_LANGUAGE
    if voices_by_language and language not in voices_by_language:
        language = sorted(voices_by_language)[0]

    voice_options = voices_by_language.get(language, [])
    voice = DEFAULT_VOICE
    if voice_options and voice not in voice_options:
        voice = voice_options[0]

    hass.data[DOMAIN][entry.entry_id] = {
        CONF_HOST: host,
        CONF_PORT: port,
        DATA_VOICES_BY_LANGUAGE: voices_by_language,
        DATA_PREFERENCES: {
            OPTION_LANGUAGE: language,
            OPTION_VOICE: voice,
            OPTION_RATE: DEFAULT_RATE,
            OPTION_PITCH: DEFAULT_PITCH,
            OPTION_VOLUME: DEFAULT_VOLUME,
        },
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
