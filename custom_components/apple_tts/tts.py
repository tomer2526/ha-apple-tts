import requests
from homeassistant.components.tts import Provider
from .const import DOMAIN, DEFAULT_VOICE, DEFAULT_RATE

async def async_get_engine(hass, config, discovery_info=None):
    return AppleTTSEngine(hass.data[DOMAIN])

class AppleTTSEngine(Provider):
    """Apple TTS engine compatible with HA tts.speak."""

    def __init__(self, config):
        self.host = config["host"]
        self.port = config["port"]
        self.name = "AppleTTS"

    @property
    def default_language(self):
        return "he_IL"

    @property
    def supported_languages(self):
        try:
            r = requests.get(f"http://{self.host}:{self.port}/voices")
            return list(set(v["language"] for v in r.json()))
        except:
            return ["he_IL"]

    def get_tts_audio(self, message, language, options=None):
        """Return audio bytes and format for HA TTS."""
        voice = options.get("voice", DEFAULT_VOICE)
        rate = options.get("rate", DEFAULT_RATE)
        url = f"http://{self.host}:{self.port}/tts?text={message}&voice={voice}&rate={rate}"
        r = requests.get(url)
        return "aiff", r.content
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Apple TTS from a config entry."""
    return True