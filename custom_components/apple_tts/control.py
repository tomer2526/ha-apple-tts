from __future__ import annotations

import requests
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_HOST, CONF_PORT


async def async_shutdown_server(hass: HomeAssistant, entry_data: dict) -> None:
    host = entry_data[CONF_HOST]
    port = entry_data[CONF_PORT]

    def _send_shutdown() -> None:
        response = requests.post(
            f"http://{host}:{port}/shutdown",
            timeout=5,
        )
        response.raise_for_status()

    try:
        await hass.async_add_executor_job(_send_shutdown)
    except requests.RequestException as err:
        raise HomeAssistantError(f"Failed to shut down Apple TTS server: {err}") from err


async def async_restart_server(hass: HomeAssistant, entry_data: dict) -> None:
    host = entry_data[CONF_HOST]
    port = entry_data[CONF_PORT]

    def _send_restart() -> None:
        response = requests.post(
            f"http://{host}:{port}/restart",
            timeout=5,
        )
        response.raise_for_status()

    try:
        await hass.async_add_executor_job(_send_restart)
    except requests.RequestException as err:
        raise HomeAssistantError(f"Failed to restart Apple TTS server: {err}") from err
