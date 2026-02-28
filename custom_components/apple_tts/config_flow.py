from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN, CONF_HOST, CONF_PORT, DEFAULT_PORT


class AppleTTSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Apple TTS", data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        })
        return self.async_show_form(step_id="user", data_schema=schema)
