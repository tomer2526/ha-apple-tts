# Apple TTS for Home Assistant (macOS `say`)

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

## Quick install from GitHub

Repository:

- `https://github.com/tomer2526/ha-apple-tts/tree/main`

Home Assistant (installs `custom_components/apple_tts` into `/config`):

```bash
cd /tmp
curl -fsSL -o install_ha_from_git.sh https://raw.githubusercontent.com/tomer2526/ha-apple-tts/main/install_ha_from_git.sh
chmod +x install_ha_from_git.sh
./install_ha_from_git.sh /config
```

macOS server (clones/updates to `~/ha-apple-tts` and enables autostart):

```bash
cd /tmp
curl -fsSL -o install_macos_server_from_git.sh https://raw.githubusercontent.com/tomer2526/ha-apple-tts/main/install_macos_server_from_git.sh
chmod +x install_macos_server_from_git.sh
./install_macos_server_from_git.sh
```

## 1) Run the macOS TTS server

From this repository on your Mac:

```bash
cd "macos tts server"
./start_tts.sh
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

## 2) Install the Home Assistant custom component

Copy `custom_components/apple_tts` into your Home Assistant config:

```text
/config/custom_components/apple_tts/
```

Restart Home Assistant, then add integration:

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
      media_player_entity_id: media_player.homepod_tvmr
      message: "Hello Tomer"
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
- `button.apple_tts_shutdown_server`
- `button.apple_tts_restart_server`

When `tts.speak` is called without explicit `options`, these values are used as defaults.

Reset defaults (without button entities) using service:

```yaml
service: apple_tts.reset_defaults
data:
  target: all   # rate | pitch | volume | all
  # entry_id: "<optional-config-entry-id>"
```

Shut down the macOS TTS server from Home Assistant:

```yaml
service: apple_tts.shutdown_server
data:
  # entry_id: "<optional-config-entry-id>"
```

You can also press the `button.apple_tts_shutdown_server` entity from the UI.

Restart the macOS TTS server from Home Assistant:

```yaml
service: apple_tts.restart_server
data:
  # entry_id: "<optional-config-entry-id>"
```

You can also press the `button.apple_tts_restart_server` entity from the UI.

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
