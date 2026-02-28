from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests
from homeassistant.components.tts import Provider, TextToSpeechEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_RATE, DEFAULT_VOICE, DOMAIN

REQUEST_TIMEOUT = 15


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> bool:
    """Set up Apple TTS entity from config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([AppleTTSEntity(config_entry, data["host"], data["port"])])
    return True


async def async_get_engine(
    hass: HomeAssistant,
    config: dict[str, Any],
    discovery_info: Any | None = None,
) -> "AppleTTSEngine":
    """Legacy provider path kept for compatibility."""
    entry_id = config.get("entry_id")
    domain_data = hass.data.get(DOMAIN, {})

    if entry_id and isinstance(domain_data, dict) and entry_id in domain_data:
        engine_config = domain_data[entry_id]
    elif isinstance(config, dict) and "host" in config and "port" in config:
        engine_config = config
    else:
        engine_config = {}

    return AppleTTSEngine(engine_config)


class AppleTTSEntity(TextToSpeechEntity):
    """Apple TTS entity for Home Assistant tts.speak."""

    _attr_name = "Apple TTS"

    def __init__(self, config_entry: ConfigEntry, host: str, port: int) -> None:
        self._attr_unique_id = config_entry.entry_id
        self._host = host
        self._port = port
        self._supported_languages = _fetch_supported_languages(host, port)

    @property
    def default_language(self) -> str:
        return "he_IL"

    @property
    def supported_languages(self) -> list[str]:
        return self._supported_languages

    @property
    def supported_options(self) -> list[str]:
        return ["voice", "rate"]

    def get_tts_audio(
        self,
        message: str,
        language: str,
        options: dict[str, Any] | None = None,
    ) -> tuple[str, bytes] | None:
        return _get_tts_audio(self._host, self._port, message, language, options)


class AppleTTSEngine(Provider):
    """Provider wrapper for compatibility with older HA paths."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.host = config.get("host")
        self.port = config.get("port")
        self.name = "AppleTTS"

    @property
    def default_language(self) -> str:
        return "he_IL"

    @property
    def supported_languages(self) -> list[str]:
        if not self.host or not self.port:
            return ["he_IL"]
        return _fetch_supported_languages(self.host, self.port)

    @property
    def supported_options(self) -> list[str]:
        return ["voice", "rate"]

    def get_tts_audio(
        self, message: str, language: str, options: dict[str, Any] | None = None
    ) -> tuple[str, bytes] | None:
        if not self.host or not self.port:
            return None
        return _get_tts_audio(self.host, self.port, message, language, options)


def _fetch_supported_languages(host: str, port: int) -> list[str]:
    try:
        response = requests.get(f"http://{host}:{port}/voices", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        voices = response.json()
        languages = sorted(
            {
                voice["language"].replace("-", "_")
                for voice in voices
                if isinstance(voice, dict) and isinstance(voice.get("language"), str)
            }
        )
        return languages or ["he_IL"]
    except Exception:
        return ["he_IL"]


def _get_tts_audio(
    host: str,
    port: int,
    message: str,
    language: str,
    options: dict[str, Any] | None,
) -> tuple[str, bytes] | None:
    options = options or {}
    voice = options.get("voice", DEFAULT_VOICE)
    rate = options.get("rate", DEFAULT_RATE)
    params = urlencode(
        {"text": message, "voice": voice, "rate": rate, "language": language},
        doseq=False,
        safe="",
    )

    try:
        response = requests.get(
            f"http://{host}:{port}/tts?{params}",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    return "aiff", response.content
