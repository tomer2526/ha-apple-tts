from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests
from homeassistant.components.tts import Provider, TextToSpeechEntity, Voice
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import fetch_voices_by_language, normalize_language
from .const import (
    CONF_HOST,
    CONF_PORT,
    DATA_PREFERENCES,
    DATA_VOICES_BY_LANGUAGE,
    DEFAULT_LANGUAGE,
    DEFAULT_PITCH,
    DEFAULT_RATE,
    DEFAULT_VOICE,
    DOMAIN,
    HTTP_TIMEOUT,
    OPTION_LANGUAGE,
    OPTION_PITCH,
    OPTION_RATE,
    OPTION_VOLUME,
    OPTION_VOICE,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> bool:
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([AppleTTSEntity(config_entry, data)])
    return True


async def async_get_engine(
    hass: HomeAssistant,
    config: dict[str, Any],
    discovery_info: Any | None = None,
) -> "AppleTTSEngine":
    entry_id = config.get("entry_id")
    domain_data = hass.data.get(DOMAIN, {})

    if entry_id and isinstance(domain_data, dict) and entry_id in domain_data:
        engine_config = domain_data[entry_id]
    else:
        engine_config = config

    return AppleTTSEngine(engine_config)


class AppleTTSEntity(TextToSpeechEntity):
    _attr_name = "Apple TTS"

    def __init__(self, config_entry: ConfigEntry, shared_data: dict[str, Any]) -> None:
        self._attr_unique_id = config_entry.entry_id
        self._data = shared_data

    @property
    def default_language(self) -> str:
        return self._preferences.get(OPTION_LANGUAGE, DEFAULT_LANGUAGE)

    @property
    def supported_languages(self) -> list[str]:
        voices_by_language = self._voices_by_language
        return sorted(voices_by_language) or [DEFAULT_LANGUAGE]

    @property
    def supported_options(self) -> list[str]:
        return [OPTION_VOICE, OPTION_RATE, OPTION_PITCH, OPTION_VOLUME]

    @property
    def default_options(self) -> dict[str, Any]:
        return {
            OPTION_VOICE: self._preferences.get(OPTION_VOICE, DEFAULT_VOICE),
            OPTION_RATE: self._preferences.get(OPTION_RATE, DEFAULT_RATE),
            OPTION_PITCH: self._preferences.get(OPTION_PITCH, DEFAULT_PITCH),
            OPTION_VOLUME: self._preferences.get(OPTION_VOLUME),
        }

    @callback
    def async_get_supported_voices(self, language: str) -> list[Voice] | None:
        normalized = normalize_language(language) or self.default_language
        names = self._voices_by_language.get(normalized, [])
        if not names:
            return None
        return [Voice(name, name) for name in names]

    def get_tts_audio(
        self,
        message: str,
        language: str,
        options: dict[str, Any] | None = None,
    ) -> tuple[str, bytes] | None:
        return _get_tts_audio(self._data, message, language, options)

    @property
    def _preferences(self) -> dict[str, Any]:
        return self._data[DATA_PREFERENCES]

    @property
    def _voices_by_language(self) -> dict[str, list[str]]:
        return self._data[DATA_VOICES_BY_LANGUAGE]


class AppleTTSEngine(Provider):
    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self.name = "AppleTTS"

    @property
    def default_language(self) -> str:
        prefs = self._config.get(DATA_PREFERENCES, {})
        return prefs.get(OPTION_LANGUAGE, DEFAULT_LANGUAGE)

    @property
    def supported_languages(self) -> list[str]:
        voices_by_language = self._config.get(DATA_VOICES_BY_LANGUAGE)
        if not isinstance(voices_by_language, dict):
            host = self._config.get(CONF_HOST)
            port = self._config.get(CONF_PORT)
            if host and port:
                voices_by_language = fetch_voices_by_language(host, port)
            else:
                voices_by_language = {}
        return sorted(voices_by_language) or [DEFAULT_LANGUAGE]

    @property
    def supported_options(self) -> list[str]:
        return [OPTION_VOICE, OPTION_RATE, OPTION_PITCH, OPTION_VOLUME]

    @property
    def default_options(self) -> dict[str, Any]:
        prefs = self._config.get(DATA_PREFERENCES, {})
        return {
            OPTION_VOICE: prefs.get(OPTION_VOICE, DEFAULT_VOICE),
            OPTION_RATE: prefs.get(OPTION_RATE, DEFAULT_RATE),
            OPTION_PITCH: prefs.get(OPTION_PITCH, DEFAULT_PITCH),
            OPTION_VOLUME: prefs.get(OPTION_VOLUME),
        }

    def get_tts_audio(
        self, message: str, language: str, options: dict[str, Any] | None = None
    ) -> tuple[str, bytes] | None:
        return _get_tts_audio(self._config, message, language, options)


def _get_tts_audio(
    shared_data: dict[str, Any],
    message: str,
    language: str,
    options: dict[str, Any] | None,
) -> tuple[str, bytes] | None:
    options = options or {}
    preferences = shared_data.get(DATA_PREFERENCES, {})
    voices_by_language = shared_data.get(DATA_VOICES_BY_LANGUAGE, {})

    host = shared_data.get(CONF_HOST)
    port = shared_data.get(CONF_PORT)
    if not host or not port:
        return None

    selected_language = normalize_language(language) or preferences.get(
        OPTION_LANGUAGE, DEFAULT_LANGUAGE
    )
    voice = options.get(OPTION_VOICE) or preferences.get(OPTION_VOICE)
    if not voice:
        language_voices = voices_by_language.get(selected_language, [])
        voice = language_voices[0] if language_voices else DEFAULT_VOICE

    rate = options.get(OPTION_RATE, preferences.get(OPTION_RATE, DEFAULT_RATE))
    pitch = options.get(OPTION_PITCH, preferences.get(OPTION_PITCH, DEFAULT_PITCH))
    volume = options.get(OPTION_VOLUME, preferences.get(OPTION_VOLUME))

    query_params: dict[str, Any] = {
        "text": message,
        "voice": voice,
        "rate": rate,
        "language": selected_language,
    }
    if pitch is not None:
        query_params["pitch"] = pitch
    if volume is not None:
        query_params["volume"] = volume

    params = urlencode(query_params, doseq=False, safe="")

    try:
        response = requests.get(
            f"http://{host}:{port}/tts?{params}",
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    content_type = response.headers.get("Content-Type", "").lower()
    audio_format = "wav" if "audio/wav" in content_type else "aiff"
    return audio_format, response.content
