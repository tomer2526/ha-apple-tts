from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_PORT = 5002
DEFAULT_LABEL = "com.appletts.server"
DEFAULT_PLIST = Path.home() / "Library/LaunchAgents/com.appletts.server.plist"


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _pids_on_port(port: int) -> list[int]:
    result = _run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"])
    if result.returncode not in (0, 1):
        print(f"failed running lsof: {result.stderr.strip()}", file=sys.stderr)
        return []
    return sorted({int(line) for line in result.stdout.splitlines() if line.strip().isdigit()})


def _unload_launchagent(label: str, plist_path: Path) -> None:
    listed = _run(["launchctl", "list", label])
    if listed.returncode == 0:
        if plist_path.exists():
            _run(["launchctl", "unload", str(plist_path)])
            print(f"unloaded launch agent: {label}")
        else:
            # fallback for cases where plist path differs
            _run(["launchctl", "remove", label])
            print(f"removed launch agent: {label}")


def _stop_pids(pids: list[int], force: bool) -> None:
    if not pids:
        return
    sig = signal.SIGKILL if force else signal.SIGTERM
    for pid in pids:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass
    if not force:
        time.sleep(0.8)


def main() -> int:
    port = int(os.getenv("APPLE_TTS_PORT", str(DEFAULT_PORT)))
    label = os.getenv("APPLE_TTS_LAUNCH_LABEL", DEFAULT_LABEL)
    plist_path = Path(os.getenv("APPLE_TTS_LAUNCH_PLIST", str(DEFAULT_PLIST)))

    _unload_launchagent(label, plist_path)

    pids = _pids_on_port(port)
    if not pids:
        print(f"no running TTS server on port {port}")
        return 0

    print(f"stopping pids on port {port}: {', '.join(map(str, pids))}")
    _stop_pids(pids, force=False)

    remaining = _pids_on_port(port)
    if remaining:
        print(f"forcing stop for pids: {', '.join(map(str, remaining))}")
        _stop_pids(remaining, force=True)

    final = _pids_on_port(port)
    if final:
        print(f"failed to stop all processes on port {port}: {final}", file=sys.stderr)
        return 1

    print(f"TTS server stopped on port {port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
