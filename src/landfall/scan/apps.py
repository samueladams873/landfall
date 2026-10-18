"""List installed Windows apps. Read-only: only opens registry keys for reading."""
from __future__ import annotations

import re
import sys

from landfall.scan.winutil import run_powershell_json

UNINSTALL_KEYS = [
    ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]

# Entries that are plumbing, not apps a person chose to install.
NOISE = re.compile(
    r"(visual c\+\+|redistributable|\.net (framework|runtime|desktop runtime)|"
    r"windows sdk|update for|security update|hotfix|kb\d{6,}|driver|"
    r"microsoft edge (update|webview)|webview2|"
    r"microsoft update health|windows pc health|"
    r"guest additions|vcredist|directx|runtime$)",
    re.IGNORECASE,
)


def is_noise(entry: dict) -> bool:
    if entry.get("system_component") or entry.get("parent"):
        return True
    if entry.get("release_type", "").lower() in {"update", "hotfix", "security update"}:
        return True
    return bool(NOISE.search(entry.get("name", "")))


def _read_registry() -> list[dict]:
    import winreg  # Windows only

    hives = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
    found = []
    for hive_name, path in UNINSTALL_KEYS:
        try:
            root = winreg.OpenKey(hives[hive_name], path, 0, winreg.KEY_READ)
        except OSError:
            continue
        with root:
            index = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(root, index)
                except OSError:
                    break
                index += 1
                try:
                    with winreg.OpenKey(root, sub_name, 0, winreg.KEY_READ) as sub:
                        found.append(_entry_from_key(winreg, sub))
                except OSError:
                    continue
    return found


def _entry_from_key(winreg, key) -> dict:
    def value(name, default=""):
        try:
            return winreg.QueryValueEx(key, name)[0]
        except OSError:
            return default

    return {
        "name": str(value("DisplayName")).strip(),
        "version": str(value("DisplayVersion")).strip(),
        "publisher": str(value("Publisher")).strip(),
        "system_component": value("SystemComponent", 0) == 1,
        "parent": str(value("ParentKeyName")).strip(),
        "release_type": str(value("ReleaseType")).strip(),
        "source": "Installed program",
    }


def _read_store_apps() -> list[dict]:
    rows = run_powershell_json(
        "Get-StartApps | Where-Object { $_.AppID -like '*!*' } | "
        "Select-Object Name, AppID | ConvertTo-Json -Compress"
    )
    apps = []
    for row in rows:
        app_id = str(row.get("AppID", ""))
        # Skip apps that ship with Windows itself.
        if app_id.lower().startswith(("microsoft.", "windows.", "microsoftwindows.")):
            continue
        apps.append({"name": str(row.get("Name", "")).strip(), "version": "",
                     "publisher": "", "source": "Microsoft Store"})
    return apps


def clean(entries: list[dict]) -> list[dict]:
    """Drop blanks and noise, and de-duplicate by name (32/64-bit copies)."""
    seen: dict[str, dict] = {}
    for entry in entries:
        name = entry.get("name", "")
        if not name or is_noise(entry):
            continue
        key = name.lower()
        if key not in seen:
            seen[key] = {k: entry.get(k, "") for k in ("name", "version", "publisher", "source")}
    return list(seen.values())


def scan_apps() -> list[dict]:
    if sys.platform != "win32":
        return []
    return clean(_read_registry() + _read_store_apps())
