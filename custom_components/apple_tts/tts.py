from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import requests
from homeassistant.components.tts import Provider
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_RATE, DEFAULT_VOICE, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> bool:
    """Set up Apple TTS from a config entry."""
    return True


async def async_get_engine(
    hass: HomeAssistant, config: dict[str, Any], discovery_info: Any | None = None
) -> "AppleTTSEngine":
    entry_id = config.get("entry_id")
    domain_data = hass.data.get(DOMAIN, {})

    if entry_id and isinstance(domain_data, dict) and entry_id in domain_data:
        engine_config = domain_data[entry_id]
    elif isinstance(domain_data, dict) and "host" in domain_data and "port" in domain_data:
        # Backward compatibility for older storage shape: hass.data[DOMAIN] = entry.data
        engine_config = domain_data
    elif isinstance(domain_data, dict):
        engine_config = next(
            (
                value
                for value in domain_data.values()
                if isinstance(value, dict) and "host" in value and "port" in value
            ),
            config,
        )
    else:
        engine_config = config
    return AppleTTSEngine(engine_config)


class AppleTTSEngine(Provider):
    """Apple TTS engine compatible with HA tts.speak."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.host = config["host"]
        self.port = config["port"]
        self.name = "AppleTTS"

    @property
    def default_language(self) -> str:
        return "he_IL"

    @property
    def supported_languages(self) -> list[str]:
        try:
            response = requests.get(
                f"http://{self.host}:{self.port}/voices",
                timeout=10,
            )
            response.raise_for_status()
            voices = response.json()
            return sorted(
                {v["language"] for v in voices if isinstance(v, dict) and "language" in v}
            )
        except Exception:
            return ["he_IL"]

    @property
    def supported_options(self) -> list[str]:
        return ["voice", "rate"]

    def get_tts_audio(
        self, message: str, language: str, options: dict[str, Any] | None = None
    ) -> tuple[str, bytes] | None:
        options = options or {}
        voice = options.get("voice", DEFAULT_VOICE)
        rate = options.get("rate", DEFAULT_RATE)
        params = urlencode(
            {"text": message, "voice": voice, "rate": rate, "language": language},
            doseq=False,
            safe="",
        )
        url = f"http://{self.host}:{self.port}/tts?{params}"

        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
        except requests.RequestException:
            return None

        return "aiff", response.content
