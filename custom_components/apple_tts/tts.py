from __future__ import annotations

import logging
from typing import Any

import requests
from homeassistant.components.tts import Provider
from homeassistant.core import HomeAssistant

from .const import (
    DEFAULT_LANGUAGE,
    DEFAULT_RATE,
    DEFAULT_VOICE,
    DOMAIN,
    HTTP_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


async def async_get_engine(
    hass: HomeAssistant, config: dict[str, Any], discovery_info: Any | None = None
) -> "AppleTTSEngine":
    entry_id = config.get("entry_id")
    if entry_id and entry_id in hass.data[DOMAIN]:
        entry_data = hass.data[DOMAIN][entry_id]
    else:
        entry_data = config
    return AppleTTSEngine(entry_data)


class AppleTTSEngine(Provider):
    """Apple TTS engine compatible with Home Assistant tts.speak."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.host: str = config["host"]
        self.port: int = config["port"]
        self.name = "AppleTTS"
        self._voices_cache: list[dict[str, str]] = []

    @property
    def default_language(self) -> str:
        return DEFAULT_LANGUAGE

    @property
    def supported_languages(self) -> list[str]:
        voices = self._fetch_voices()
        if not voices:
            return [DEFAULT_LANGUAGE]
        return sorted({voice["language"] for voice in voices if voice.get("language")})

    @property
    def supported_options(self) -> list[str]:
        return ["voice", "rate"]

    @property
    def default_options(self) -> dict[str, Any]:
        return {"voice": DEFAULT_VOICE, "rate": DEFAULT_RATE}

    def get_tts_audio(
        self, message: str, language: str, options: dict[str, Any] | None = None
    ) -> tuple[str, bytes] | None:
        options = options or {}
        voice = str(options.get("voice") or self._default_voice_for_language(language))
        rate = str(options.get("rate") or DEFAULT_RATE)
        use_cache = str(options.get("cache", True)).lower()

        try:
            response = requests.get(
                f"http://{self.host}:{self.port}/tts",
                params={
                    "text": message,
                    "voice": voice,
                    "rate": rate,
                    "language": language or DEFAULT_LANGUAGE,
                    "cache": use_cache,
                },
                timeout=HTTP_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as err:
            _LOGGER.error("Apple TTS request failed: %s", err)
            return None

        return "aiff", response.content

    def _default_voice_for_language(self, language: str) -> str:
        voices = self._fetch_voices()
        normalized = (language or DEFAULT_LANGUAGE).replace("-", "_")
        for voice in voices:
            if voice["language"] == normalized:
                return voice["voice"]
        return DEFAULT_VOICE

    def _fetch_voices(self) -> list[dict[str, str]]:
        try:
            response = requests.get(
                f"http://{self.host}:{self.port}/voices",
                timeout=HTTP_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                self._voices_cache = [
                    item
                    for item in data
                    if isinstance(item, dict)
                    and isinstance(item.get("voice"), str)
                    and isinstance(item.get("language"), str)
                ]
        except requests.RequestException as err:
            _LOGGER.warning("Failed loading Apple TTS voices: %s", err)
        except ValueError as err:
            _LOGGER.warning("Invalid JSON from Apple TTS voices endpoint: %s", err)

        return self._voices_cache
