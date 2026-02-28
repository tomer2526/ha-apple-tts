from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .api import fetch_voices_by_language
from .control import async_shutdown_server, async_start_server
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
    SERVICE_RESET,
    SERVICE_START,
    SERVICE_SHUTDOWN,
)

PLATFORMS = ["tts", "number", "button"]

RESET_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): str,
        vol.Optional("target", default="all"): vol.In(
            [OPTION_RATE, OPTION_PITCH, OPTION_VOLUME, "all"]
        ),
    }
)
SHUTDOWN_SCHEMA = vol.Schema({vol.Optional("entry_id"): str})
START_SCHEMA = vol.Schema({vol.Optional("entry_id"): str})


def _update_signal(entry_id: str) -> str:
    return f"{DOMAIN}_{entry_id}_prefs_updated"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    async def _handle_reset(call) -> None:
        domain_data = hass.data.get(DOMAIN, {})
        if not isinstance(domain_data, dict) or not domain_data:
            return

        entry_id = call.data.get("entry_id")
        if entry_id and entry_id in domain_data:
            entries = [domain_data[entry_id]]
        else:
            entries = list(domain_data.values())

        target = call.data.get("target", "all")
        for item in entries:
            changed = False
            prefs = item[DATA_PREFERENCES]
            if target in (OPTION_RATE, "all"):
                prefs[OPTION_RATE] = DEFAULT_RATE
                changed = True
            if target in (OPTION_PITCH, "all"):
                prefs[OPTION_PITCH] = DEFAULT_PITCH
                changed = True
            if target in (OPTION_VOLUME, "all"):
                prefs[OPTION_VOLUME] = DEFAULT_VOLUME
                changed = True
            if changed:
                async_dispatcher_send(hass, _update_signal(item["entry_id"]))

    async def _handle_shutdown(call) -> None:
        domain_data = hass.data.get(DOMAIN, {})
        if not isinstance(domain_data, dict) or not domain_data:
            raise HomeAssistantError("Apple TTS is not configured")

        entry_id = call.data.get("entry_id")
        if entry_id and entry_id in domain_data:
            target = domain_data[entry_id]
        else:
            target = next(iter(domain_data.values()))

        await async_shutdown_server(hass, target)

    async def _handle_start(call) -> None:
        domain_data = hass.data.get(DOMAIN, {})
        if not isinstance(domain_data, dict) or not domain_data:
            raise HomeAssistantError("Apple TTS is not configured")

        entry_id = call.data.get("entry_id")
        if entry_id and entry_id in domain_data:
            target = domain_data[entry_id]
        else:
            target = next(iter(domain_data.values()))

        await async_start_server(hass, target)

    if not hass.services.has_service(DOMAIN, SERVICE_RESET):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RESET,
            _handle_reset,
            schema=RESET_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SHUTDOWN):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SHUTDOWN,
            _handle_shutdown,
            schema=SHUTDOWN_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_START):
        hass.services.async_register(
            DOMAIN,
            SERVICE_START,
            _handle_start,
            schema=START_SCHEMA,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    host = entry.options.get(CONF_HOST, entry.data[CONF_HOST])
    port = entry.options.get(CONF_PORT, entry.data[CONF_PORT])
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
        "entry_id": entry.entry_id,
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
        if not hass.data[DOMAIN] and hass.services.has_service(DOMAIN, SERVICE_RESET):
            hass.services.async_remove(DOMAIN, SERVICE_RESET)
        if not hass.data[DOMAIN] and hass.services.has_service(DOMAIN, SERVICE_SHUTDOWN):
            hass.services.async_remove(DOMAIN, SERVICE_SHUTDOWN)
        if not hass.data[DOMAIN] and hass.services.has_service(DOMAIN, SERVICE_START):
            hass.services.async_remove(DOMAIN, SERVICE_START)
    return unload_ok
