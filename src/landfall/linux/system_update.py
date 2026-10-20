"""'Let's update your system first': a full system update with one password, no terminal."""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from landfall.sysenv import system_env

# One script per family. Each waits politely if the PC is already updating itself
# (Ubuntu's automatic updates hold the package lock for a while after boot).
SCRIPTS = {
    "apt": r"""
export DEBIAN_FRONTEND=noninteractive
echo "LANDFALL STAGE check"
apt-get -o DPkg::Lock::Timeout=900 update
echo "LANDFALL STAGE install"
apt-get -o DPkg::Lock::Timeout=900 -o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef -y full-upgrade
apt-get -o DPkg::Lock::Timeout=900 -y autoremove
""",
    "dnf": r"""
echo "LANDFALL STAGE check"
dnf -y makecache --refresh
echo "LANDFALL STAGE install"
dnf -y upgrade
""",
    "zypper": r"""
echo "LANDFALL STAGE check"
zypper --non-interactive refresh
echo "LANDFALL STAGE install"
zypper --non-interactive update
""",
    "pacman": r"""
echo "LANDFALL STAGE check"
echo "LANDFALL STAGE install"
pacman -Syu --noconfirm
""",
}
APPS_SCRIPT = r"""
echo "LANDFALL STAGE apps"
if command -v flatpak >/dev/null 2>&1; then flatpak update -y --noninteractive --system || true; fi
if command -v snap >/dev/null 2>&1; then snap refresh || true; fi
echo "LANDFALL DONE"
"""


@dataclass
class UpdatePlan:
    tool: str            # apt / dnf / zypper / pacman
    label: str           # shown to the user, e.g. "Ubuntu"


def detect(os_release: Path = Path("/etc/os-release")) -> UpdatePlan | None:
    path = system_env().get("PATH")
    name = "your Linux"
    try:
        info = dict(line.split("=", 1) for line in os_release.read_text().splitlines()
                    if "=" in line)
        name = info.get("NAME", name).strip('"')
    except OSError:
        pass
    for tool in ("apt-get", "dnf", "zypper", "pacman"):
        if shutil.which(tool, path=path):
            return UpdatePlan("apt" if tool == "apt-get" else tool, name)
    return None


def script_for(plan: UpdatePlan) -> str:
    """The script exits non-zero if any update command failed (app-store refreshes are
    best-effort and never fail the update)."""
    lines = []
    for line in SCRIPTS[plan.tool].strip().splitlines():
        first = line.split()[0] if line.split() else ""
        lines.append(line + " || FAIL=1" if first in ("apt-get", "dnf", "zypper", "pacman")
                     else line)
    return "FAIL=0\n" + "\n".join(lines) + "\n" + APPS_SCRIPT + "exit $FAIL\n"


_APT_TOTAL = re.compile(r"(\d+) upgraded, (\d+) newly installed")
_APT_STEP = re.compile(r"^(Unpacking|Setting up) ")
_DNF_STEP = re.compile(r"^\s*(Upgrading|Installing|Verifying)\s*:.*\s(\d+)/(\d+)\s*$")


class ProgressParser:
    """Turns update-tool output into ('stage', name) / ('progress', done, total) / ('item', text)."""

    def __init__(self, tool: str):
        self.tool, self.total, self.done = tool, 0, 0

    def feed(self, line: str):
        line = line.rstrip()
        if line.startswith("LANDFALL STAGE "):
            return ("stage", line.split()[-1])
        if line == "LANDFALL DONE":
            return ("stage", "done")
        if self.tool == "apt":
            m = _APT_TOTAL.search(line)
            if m:
                self.total = (int(m.group(1)) + int(m.group(2))) * 2   # unpack + set up
                return ("progress", 0, self.total)
            if _APT_STEP.match(line) and self.total:
                self.done = min(self.done + 1, self.total)
                words = line.split()
                at = 1 if words[0] == "Unpacking" else 2        # "Setting up <pkg>"
                pkg = words[at] if len(words) > at else ""
                return ("progress", self.done, self.total, pkg.split(":")[0])
        elif self.tool == "dnf":
            m = _DNF_STEP.match(line)
            if m:
                done, total = int(m.group(2)), int(m.group(3))
                return ("progress", done, total, line.split(":")[1].split()[0])
        if "Could not get lock" in line or "Waiting for cache lock" in line:
            return ("item", "Your PC is already installing updates by itself. Waiting for it...")
        return None


def run_update(plan: UpdatePlan, report, log_path: Path | None = None) -> tuple[bool, str]:
    """Run the update as root with one password pop-up. Streams progress via report()."""
    if not shutil.which("pkexec", path=system_env().get("PATH")):
        return False, "This system can't show a password pop-up (pkexec is missing)."
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
        f.write(script_for(plan))
        script = f.name
    Path(script).chmod(0o755)
    parser = ProgressParser(plan.tool)
    tail: list[str] = []
    log = open(log_path, "w", encoding="utf-8") if log_path else None
    try:
        proc = subprocess.Popen(["pkexec", "/bin/sh", script], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, env=system_env(),
                                stdin=subprocess.DEVNULL, bufsize=1)
        for line in proc.stdout:
            if log:
                log.write(line)
            tail = (tail + [line.rstrip()])[-8:]
            event = parser.feed(line)
            if event:
                report(event)
        code = proc.wait()
    finally:
        if log:
            log.close()
        Path(script).unlink(missing_ok=True)
    if code in (126, 127):
        return False, "The password window was closed, so nothing was updated."
    if code != 0:
        return False, next((l for l in reversed(tail) if l.strip()), f"Update stopped (code {code}).")
    return True, ""


def restart_needed() -> bool:
    return Path("/var/run/reboot-required").exists()
