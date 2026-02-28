import requests

from homeassistant.components.tts import Provider

from .const import DOMAIN, DEFAULT_RATE, DEFAULT_VOICE


async def async_get_engine(hass, config, discovery_info=None):

    data = hass.data[DOMAIN]

    return AppleTTSEngine(data)


class AppleTTSEngine(Provider):

    def __init__(self, config):

        self.host = config["host"]

        self.port = config["port"]

        self.name = "AppleTTS"


        self.voices = self.load_voices()


    def load_voices(self):

        try:

            r = requests.get(

                f"http://{self.host}:{self.port}/voices"

            )

            return r.json()

        except:

            return []


    @property
    def supported_languages(self):

        return list(set(

            v["language"]

            for v in self.voices

        ))


    def get_tts_audio(self, message, language, options=None):

        voice = options.get(

            "voice",

            DEFAULT_VOICE

        )

        rate = options.get(

            "rate",

            DEFAULT_RATE

        )

        url = (

            f"http://{self.host}:{self.port}/tts"

            f"?text={message}"

            f"&voice={voice}"

            f"&rate={rate}"

        )

        r = requests.get(url)

        return ("aiff", r.content)