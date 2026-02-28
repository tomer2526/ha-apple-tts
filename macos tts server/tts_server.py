from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_file

APP_HOST = os.getenv("APPLE_TTS_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APPLE_TTS_PORT", "5002"))
CACHE_DIR = Path(os.getenv("APPLE_TTS_CACHE_DIR", "/tmp/apple_tts_cache"))
DEFAULT_VOICE = os.getenv("APPLE_TTS_DEFAULT_VOICE", "Samantha")
DEFAULT_RATE = int(os.getenv("APPLE_TTS_DEFAULT_RATE", "170"))
DEFAULT_PITCH = int(os.getenv("APPLE_TTS_DEFAULT_PITCH", "50"))
DEFAULT_VOLUME = int(os.getenv("APPLE_TTS_DEFAULT_VOLUME", "100"))
MAX_TEXT_LENGTH = int(os.getenv("APPLE_TTS_MAX_TEXT_LENGTH", "1200"))

app = Flask(__name__)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_language(raw_language: str) -> str | None:
    token = raw_language.strip().replace("-", "_")
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


def _list_voices() -> list[dict[str, str]]:
    result = subprocess.run(
        ["say", "-v", "?"],
        capture_output=True,
        text=True,
        check=True,
    )
    voices: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        raw = line.strip()
        if not raw:
            continue

        # Keep only metadata segment: "<voice><spaces><lang>".
        meta = raw.split("#", 1)[0].rstrip()
        parts = re.split(r"\s{2,}", meta)
        if len(parts) < 2:
            continue

        voice = parts[0].strip()
        language = _normalize_language(parts[1])
        if voice and language:
            voices.append({"voice": voice, "language": language})
    return voices


def _voice_exists(voice: str) -> bool:
    return any(v["voice"] == voice for v in _list_voices())


def _cache_key(text: str, voice: str, rate: str, language: str) -> str:
    payload = f"{text}|{voice}|{rate}|{language}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_int_option(
    raw_value: str | None,
    *,
    default: int,
    minimum: int,
    maximum: int,
    name: str,
) -> int:
    if raw_value is None or raw_value == "":
        return default

    try:
        value = int(raw_value)
    except ValueError as err:
        raise ValueError(f"Invalid {name}") from err

    if value < minimum or value > maximum:
        raise ValueError(f"{name} out of range ({minimum}-{maximum})")
    return value


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


@app.get("/voices")
def voices():
    try:
        return jsonify(_list_voices())
    except subprocess.CalledProcessError as err:
        abort(500, description=f"Failed listing voices: {err}")


@app.get("/tts")
def tts():
    text = request.args.get("text", "").strip()
    voice = request.args.get("voice", DEFAULT_VOICE).strip()
    rate = request.args.get("rate", str(DEFAULT_RATE)).strip()
    language = request.args.get("language", "").strip()
    raw_pitch = request.args.get("pitch")
    raw_volume = request.args.get("volume")
    use_cache = request.args.get("cache", "true").lower() != "false"

    if not text:
        abort(400, description="Missing text")
    if len(text) > MAX_TEXT_LENGTH:
        abort(400, description=f"text too long (max {MAX_TEXT_LENGTH})")
    if not rate.isdigit():
        abort(400, description="Invalid rate")
    if not _voice_exists(voice):
        abort(400, description=f"Unknown voice: {voice}")

    try:
        pitch = _parse_int_option(
            raw_pitch,
            default=DEFAULT_PITCH,
            minimum=0,
            maximum=99,
            name="pitch",
        )
        volume = _parse_int_option(
            raw_volume,
            default=DEFAULT_VOLUME,
            minimum=0,
            maximum=100,
            name="volume",
        )
    except ValueError as err:
        abort(400, description=str(err))

    key = _cache_key(
        text,
        voice,
        rate,
        f"{language}|p:{pitch}|v:{volume}",
    )
    cache_path = CACHE_DIR / f"{key}.aiff"
    if use_cache and cache_path.exists():
        return send_file(cache_path, mimetype="audio/aiff")

    with tempfile.TemporaryDirectory(prefix="apple_tts_") as temp_dir:
        temp_path = Path(temp_dir) / "speech.aiff"
        speech_text = f"[[volm {volume / 100:.2f}]] [[pbas {pitch}]] {text}"
        try:
            subprocess.run(
                ["say", "-v", voice, "-r", rate, "-o", str(temp_path), speech_text],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as err:
            abort(500, description=f"say failed: {err.stderr.strip() or err}")

        if use_cache:
            temp_path.replace(cache_path)
            return send_file(cache_path, mimetype="audio/aiff")

        return Response(temp_path.read_bytes(), mimetype="audio/aiff")


if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT)
