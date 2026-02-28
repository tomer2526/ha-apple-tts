# Apple TTS for Home Assistant (Speech synthesis)

Custom Home Assistant TTS provider that uses a small macOS Flask server wrapping Apple `say` voices.

## What you get

- Home Assistant service support via `tts.speak`
- Works with any `media_player` that HA TTS supports
- Voice, rate, pitch, and volume control via `options`
- Language list from macOS voices (`/voices`)
- Server-side cache for repeated messages

## Project layout

- `custom_components/apple_tts/` - Home Assistant custom integration
- `macos tts server/` - Flask server that generates AIFF from `say`
- `custom_components/apple_tts/brand/` - local branding images for Home Assistant 2026.3+

## Step 1: Install and run the macOS server

Fast install + run (one command):

```bash
cd /tmp && rm -rf ha-apple-tts-main ha-apple-tts.zip && curl -L -o ha-apple-tts.zip https://github.com/tomer2526/ha-apple-tts/archive/refs/heads/main.zip && unzip -oq ha-apple-tts.zip && cd "ha-apple-tts-main/macos tts server" && chmod +x start_tts.sh install_launchagent.sh && ./start_tts.sh
```

The script creates a local `.venv`, installs `Flask`, and starts the service on `http://0.0.0.0:5002`.

Stop a running server:

```bash
python3 stop_tts_server.py
```

Restart server:

```bash
./restart_tts_server.sh
```

Quick checks:

```bash
curl "http://127.0.0.1:5002/health"
curl "http://127.0.0.1:5002/voices"
curl -o sample.aiff "http://127.0.0.1:5002/tts?text=Hello&voice=Samantha&rate=170"
```

### Optional autostart with LaunchAgent

Generic install (no manual path edits):

```bash
cd "macos tts server"
./install_launchagent.sh
```

Manual load/unload commands:

```bash
launchctl unload ~/Library/LaunchAgents/com.appletts.server.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.appletts.server.plist
launchctl list | rg appletts
```

Remove autostart:

```bash
cd "macos tts server"
./uninstall_launchagent.sh
```

## Step 2: Install integration via HACS

Install via HACS:

1. Open `HACS -> Integrations -> ⋮ -> Custom repositories`.
2. Add repository URL: `https://github.com/tomer2526/ha-apple-tts`
3. Category: `Integration`
4. Find `Apple TTS` in HACS and install it.
5. Restart Home Assistant.

Then add integration:

- `Settings -> Devices & Services -> Add Integration`
- Choose `Apple TTS`
- Enter Mac host and port (default `5002`)
- To update IP/port later: open the integration and click `Configure`

## 3) Use `tts.speak`

Example action:

```yaml
action:
  - service: tts.speak
    target:
      entity_id: tts.apple_tts
    data:
      media_player_entity_id: media_player.homepod
      message: "Hello World"
      cache: true
      options:
        voice: Samantha
        rate: 170
        pitch: 50
        volume: 100
```

You can reuse this in Scripts, Automations, and Developer Tools.

## 4) UI entities for defaults

The integration also creates helper entities you can control from the UI:

- `number.apple_tts_rate`
- `number.apple_tts_pitch`
- `number.apple_tts_volume`

There are no start/stop button entities in the integration.

When `tts.speak` is called without explicit `options`, these values are used as defaults.

Reset defaults (without button entities) using service:

```yaml
service: apple_tts.reset_defaults
data:
  target: all   # rate | pitch | volume | all
  # entry_id: "<optional-config-entry-id>"
```

## Notes

- This integration uses macOS `say` (Speech Synthesis), not Siri assistant voices.
- Why: Siri voices are not exposed as a stable local CLI API, while `say` is a supported system interface that works reliably for automation/server use.
- Result: voice quality and voice list come from `say -v ?`, not from Siri's assistant voice stack.
- To download more voices/languages on macOS:
  1. Open `System Settings -> Accessibility -> Spoken Content -> System Voice`.
  2. Click voice selection/management (`Manage Voices...` or download icon, depending on macOS version).
  3. Download the languages/voices you want.
  4. Verify in terminal with `say -v "?"`.
  5. Restart the Apple TTS server (and restart Home Assistant if needed) so the new voices appear in the integration.
- Integration defaults are `language: en_US` and `voice: Samantha`.
