from homeassistant.config_entries import ConfigEntry
DOMAIN = "apple_tts"

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN] = entry.data
    await hass.config_entries.async_forward_entry_setups(entry, ["tts"])
    return True