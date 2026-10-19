"""Install the Linux apps the user picked on Windows, using Flatpak (works on any distro)."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from landfall.sysenv import run, system_env

FLATHUB_URL = "https://dl.flathub.org/repo/flathub.flatpakrepo"

# How to get Flatpak itself when it's missing. pkexec shows the normal password pop-up.
PACKAGE_MANAGERS = [
    ("apt-get", ["apt-get", "install", "-y", "flatpak"]),
    ("dnf", ["dnf", "install", "-y", "flatpak"]),
    ("zypper", ["zypper", "--non-interactive", "install", "flatpak"]),
    ("pacman", ["pacman", "-S", "--noconfirm", "flatpak"]),
]


@dataclass
class AppChoice:
    windows_name: str
    linux_name: str
    flatpak: str | None
    url: str | None
    new: bool = False
    about: str = ""
    commands: list = field(default_factory=list)
    snap: str | None = None
    included: bool = False     # comes with Linux already, nothing to install


def _choice(windows: str, opt: dict) -> AppChoice:
    return AppChoice(windows, opt["name"], opt.get("flatpak"), opt.get("url"),
                     bool(opt.get("new")), opt.get("about", ""), opt.get("commands") or [],
                     opt.get("snap"), bool(opt.get("included")))


def choices_from_manifest(manifest: dict) -> list[AppChoice]:
    """The apps to set up. Bundles from v0.4+ carry the user's own picks ("install");
    older bundles fall back to the recommended option for each matched app."""
    out, seen = [], set()
    if "install" in manifest:
        for pick in manifest["install"]:
            c = _choice(pick.get("windows", ""), pick)
            key = c.flatpak or c.url or c.linux_name
            if key not in seen:
                seen.add(key)
                out.append(c)
        return out
    for app in manifest.get("apps", []):
        options = app.get("linux") or []
        if options:
            c = _choice(app["name"], options[0])
            key = c.flatpak or c.url or c.linux_name
            if key not in seen:
                seen.add(key)
                out.append(c)
    return out


def flatpak_available() -> bool:
    return shutil.which("flatpak", path=system_env().get("PATH")) is not None


def _lines(cmd) -> set[str]:
    try:
        out = run(cmd, capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    return {line.split()[0] for line in out.splitlines() if line.strip()}


def installed_flatpaks() -> set[str]:
    if not flatpak_available():
        return set()
    return _lines(["flatpak", "list", "--app", "--columns=application"])


def installed_snaps() -> set[str]:
    if not shutil.which("snap", path=system_env().get("PATH")):
        return set()
    return _lines(["snap", "list"]) - {"Name"}


def already_present(choice: AppChoice, flatpaks: set[str], snaps: set[str]) -> bool:
    """True if this app is already on the PC in any form (Flatpak, Snap or regular package),
    e.g. Firefox that comes with Ubuntu, so we never install a second copy."""
    if choice.flatpak and choice.flatpak in flatpaks:
        return True
    if choice.snap and choice.snap in snaps:
        return True
    path = system_env().get("PATH")
    return any(shutil.which(cmd, path=path) for cmd in choice.commands)


def install_flatpak_tool() -> tuple[bool, str]:
    """Install Flatpak through the system's package manager, with a password pop-up."""
    path = system_env().get("PATH")
    if not shutil.which("pkexec", path=path):
        return False, "This system can't show a password pop-up (pkexec is missing)."
    for tool, cmd in PACKAGE_MANAGERS:
        if shutil.which(tool, path=path):
            proc = run(["pkexec", *cmd], capture_output=True, text=True)
            if proc.returncode == 0 and flatpak_available():
                return True, ""
            return False, (proc.stderr or proc.stdout).strip()[-500:] or "Install was cancelled."
    return False, "Couldn't tell which package manager this Linux uses."


def ensure_flathub() -> tuple[bool, str]:
    proc = run(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub", FLATHUB_URL],
               capture_output=True, text=True)
    return proc.returncode == 0, proc.stderr.strip()


def install_app(app_id: str) -> tuple[bool, str]:
    """Install one app for this user only (no password needed). Retries once, since a
    first failure is often a brief network hiccup."""
    msg = ""
    for _attempt in range(2):
        proc = run(["flatpak", "install", "--user", "-y", "--noninteractive", "flathub", app_id],
                   capture_output=True, text=True)
        if proc.returncode == 0:
            return True, ""
        msg = (proc.stderr or proc.stdout).strip()[-500:]
    return False, friendly_error(msg)


def friendly_error(msg: str) -> str:
    low = msg.lower()
    if any(w in low for w in ("could not resolve", "network", "timeout", "connection")):
        return "No internet connection. Connect to Wi-Fi and press Try again."
    if "no space" in low:
        return "Not enough disk space."
    if "not found" in low or "nothing matches" in low:
        return "This app isn't available on Flathub right now."
    return msg.splitlines()[-1] if msg else "Unknown problem."
