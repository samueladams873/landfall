"""Helpers for running read-only PowerShell queries without flashing a console."""
from __future__ import annotations

import json
import subprocess
import sys


def run_powershell_json(script: str, timeout: int = 60) -> list[dict]:
    """Run a PowerShell snippet that ends in ConvertTo-Json; return a list of dicts.

    Returns [] on any failure so one broken query never stops the whole scan.
    """
    if sys.platform != "win32":
        return []
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-Command", f"[Console]::OutputEncoding=[Text.Encoding]::UTF8; {script}"],
            capture_output=True, stdin=subprocess.DEVNULL, timeout=timeout,
            creationflags=flags,
        )
        text = proc.stdout.decode("utf-8", errors="replace").strip()
        if not text:
            return []
        data = json.loads(text)
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
    if isinstance(data, dict):
        return [data]
    return [d for d in data if isinstance(d, dict)]
