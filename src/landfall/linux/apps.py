"""Install the Linux matches for the user's Windows apps, using Flatpak (works on any distro)."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

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


def choices_from_manifest(manifest: dict) -> list[AppChoice]:
    """One suggested Linux app per Windows app: the first (proven) installable option."""
    out, seen = [], set()
    for app in manifest.get("apps", []):
        options = app.get("linux") or []
        if not options:
            continue
        pick = next((o for o in options if o.get("flatpak")), options[0])
        key = pick.get("flatpak") or pick.get("name")
        if key in seen:
            continue
        seen.add(key)
        out.append(AppChoice(app["name"], pick["name"], pick.get("flatpak"),
                             pick.get("url"), bool(pick.get("new"))))
        for extra in options:  # also offer brand-new picks (e.g. ArtCraft) as their own row
            if extra is not pick and extra.get("new") and extra.get("url"):
                k = extra["url"]
                if k not in seen:
                    seen.add(k)
                    out.append(AppChoice(app["name"], extra["name"], None, extra["url"], True))
    return out


def flatpak_available() -> bool:
    return shutil.which("flatpak") is not None


def installed_flatpaks() -> set[str]:
    if not flatpak_available():
        return set()
    try:
        out = subprocess.run(["flatpak", "list", "--app", "--columns=application"],
                             capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    return {line.strip() for line in out.splitlines() if line.strip()}


def install_flatpak_tool() -> tuple[bool, str]:
    """Install Flatpak through the system's package manager, with a password pop-up."""
    if not shutil.which("pkexec"):
        return False, "This system can't show a password pop-up (pkexec is missing)."
    for tool, cmd in PACKAGE_MANAGERS:
        if shutil.which(tool):
            proc = subprocess.run(["pkexec", *cmd], capture_output=True, text=True)
            if proc.returncode == 0 and flatpak_available():
                return True, ""
            return False, (proc.stderr or proc.stdout).strip()[-500:] or "Install was cancelled."
    return False, "Couldn't tell which package manager this Linux uses."


def ensure_flathub() -> tuple[bool, str]:
    proc = subprocess.run(["flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
                           FLATHUB_URL], capture_output=True, text=True)
    return proc.returncode == 0, proc.stderr.strip()


def install_app(app_id: str) -> tuple[bool, str]:
    """Install one app for this user only (no password needed)."""
    proc = subprocess.run(["flatpak", "install", "--user", "-y", "--noninteractive",
                           "flathub", app_id], capture_output=True, text=True)
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip()[-500:]
