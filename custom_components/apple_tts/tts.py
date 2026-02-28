from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

import requests
from homeassistant.components.tts import Provider, TextToSpeechEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_RATE, DEFAULT_VOICE, DOMAIN

REQUEST_TIMEOUT = 15
LANGUAGE_RE = re.compile(r"^[a-z]{2,3}_[A-Z0-9]{2,8}$")

from homeassistant.components.tts import Voice


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> bool:
    """Set up Apple TTS entity from config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    voices_by_language = await hass.async_add_executor_job(
        _fetch_voices_by_language,
        data["host"],
        data["port"],
    )
    async_add_entities(
        [
            AppleTTSEntity(
                config_entry,
                data["host"],
                data["port"],
                voices_by_language,
            )
        ]
    )
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

    def __init__(
        self,
        config_entry: ConfigEntry,
        host: str,
        port: int,
        voices_by_language: dict[str, list[str]],
    ) -> None:
        self._attr_unique_id = config_entry.entry_id
        self._host = host
        self._port = port
        self._voices_by_language = voices_by_language
        self._supported_languages = sorted(voices_by_language) or ["he_IL"]

    @property
    def default_language(self) -> str:
        return "he_IL"

    @property
    def supported_languages(self) -> list[str]:
        return self._supported_languages

    @property
    def supported_options(self) -> list[str]:
        return ["voice", "rate", "pitch", "volume"]

    @callback
    def async_get_supported_voices(self, language: str) -> list[Voice] | None:
        normalized = _normalize_language(language) or "he_IL"
        names = self._voices_by_language.get(normalized, [])
        if not names:
            return None
        return [_make_voice(name) for name in names]

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
        voices_by_language = _fetch_voices_by_language(self.host, self.port)
        return sorted(voices_by_language) or ["he_IL"]

    @property
    def supported_options(self) -> list[str]:
        return ["voice", "rate", "pitch", "volume"]

    def get_tts_audio(
        self, message: str, language: str, options: dict[str, Any] | None = None
    ) -> tuple[str, bytes] | None:
        if not self.host or not self.port:
            return None
        return _get_tts_audio(self.host, self.port, message, language, options)


def _fetch_supported_languages(host: str, port: int) -> list[str]:
    return sorted(_fetch_voices_by_language(host, port)) or ["he_IL"]


def _fetch_voices_by_language(host: str, port: int) -> dict[str, list[str]]:
    try:
        response = requests.get(f"http://{host}:{port}/voices", timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        raw_voices = response.json()
    except Exception:
        return {}

    voices_by_language: dict[str, set[str]] = {}
    for item in raw_voices:
        if not isinstance(item, dict):
            continue

        voice_name = item.get("voice")
        language = item.get("language")
        if not isinstance(voice_name, str) or not isinstance(language, str):
            continue

        normalized_language = _normalize_language(language)
        if not normalized_language:
            continue
        if not LANGUAGE_RE.fullmatch(normalized_language):
            continue
        voices_by_language.setdefault(normalized_language, set()).add(voice_name)

    return {
        language: sorted(voices)
        for language, voices in voices_by_language.items()
    }


def _get_tts_audio(
    host: str,
    port: int,
    message: str,
    language: str,
    options: dict[str, Any] | None,
) -> tuple[str, bytes] | None:
    options = options or {}
    voice = options.get("voice")
    if not voice:
        voices_by_language = _fetch_voices_by_language(host, port)
        normalized_language = _normalize_language(language) or "he_IL"
        language_voices = voices_by_language.get(normalized_language, [])
        voice = language_voices[0] if language_voices else DEFAULT_VOICE
    rate = options.get("rate", DEFAULT_RATE)
    pitch = options.get("pitch")
    volume = options.get("volume")
    query_params: dict[str, Any] = {
        "text": message,
        "voice": voice,
        "rate": rate,
        "language": language,
    }
    if pitch is not None:
        query_params["pitch"] = pitch
    if volume is not None:
        query_params["volume"] = volume

    params = urlencode(query_params, doseq=False, safe="")

    try:
        response = requests.get(
            f"http://{host}:{port}/tts?{params}",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    return "aiff", response.content


def _normalize_language(language: str | None) -> str | None:
    if not language:
        return None

    token = language.strip().replace("-", "_")
    if "_" not in token:
        return None
    parts = token.split("_")
    if len(parts) != 2:
        return None

    language_code, region_code = parts
    if not language_code.isalpha() or len(language_code) not in (2, 3):
        return None
    if not region_code.isalnum() or not (2 <= len(region_code) <= 8):
        return None

    return f"{language_code.lower()}_{region_code.upper()}"


def _make_voice(voice_name: str) -> Any:
    return Voice(voice_name, voice_name)
