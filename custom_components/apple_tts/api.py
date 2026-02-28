from __future__ import annotations

import re

import requests

from .const import HTTP_TIMEOUT

LANGUAGE_RE = re.compile(r"^[a-z]{2,3}_[A-Z0-9]{2,8}$")


def normalize_language(language: str | None) -> str | None:
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


def fetch_voices_by_language(host: str, port: int) -> dict[str, list[str]]:
    try:
        response = requests.get(f"http://{host}:{port}/voices", timeout=HTTP_TIMEOUT)
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

        normalized_language = normalize_language(language)
        if not normalized_language:
            continue
        if not LANGUAGE_RE.fullmatch(normalized_language):
            continue
        voices_by_language.setdefault(normalized_language, set()).add(voice_name)

    return {
        language: sorted(voices)
        for language, voices in voices_by_language.items()
    }
