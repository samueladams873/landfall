"""Find web browsers on Windows and what they hold. Read-only.

Firefox:   bookmarks + history (places.sqlite), saved passwords (logins.json + key4.db,
           which are NOT tied to Windows, so they move exactly as they are).
Chromium family (Chrome, Edge, Brave, Vivaldi, Opera): bookmarks (Bookmarks, JSON) and
           history (History, SQLite). Their saved passwords are locked so only that browser
           can read them; the user exports them with the browser's own Export button.
"""
from __future__ import annotations

import configparser
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

FIREFOX_FILES = ("places.sqlite", "favicons.sqlite", "logins.json", "key4.db")
CHROMIUM_FILES = ("Bookmarks", "History")

# (id, display name, process name, user-data folder relative to %LOCALAPPDATA% or %APPDATA%,
#  which env var, password-page URL for the export step)
CHROMIUM_BROWSERS = [
    ("chrome", "Google Chrome", "chrome.exe", r"Google\Chrome\User Data", "LOCALAPPDATA",
     "chrome://password-manager/settings"),
    ("edge", "Microsoft Edge", "msedge.exe", r"Microsoft\Edge\User Data", "LOCALAPPDATA",
     "edge://settings/passwords"),
    ("brave", "Brave", "brave.exe", r"BraveSoftware\Brave-Browser\User Data", "LOCALAPPDATA",
     "brave://password-manager/settings"),
    ("vivaldi", "Vivaldi", "vivaldi.exe", r"Vivaldi\User Data", "LOCALAPPDATA",
     "vivaldi://settings/passwords"),
    ("opera", "Opera", "opera.exe", r"Opera Software\Opera Stable", "APPDATA",
     "opera://settings/passwords"),
]


@dataclass
class BrowserProfile:
    browser: str                # firefox / chrome / edge / brave / vivaldi / opera
    name: str                   # "Firefox", "Microsoft Edge"
    family: str                 # firefox / chromium
    profile: str                # profile folder name
    path: Path
    process: str
    bookmarks: int = 0
    history: int = 0
    passwords: int = 0          # Firefox only (Chromium passwords can't be read)
    password_url: str = ""      # where the user exports passwords (Chromium family)
    password_csv: Path | None = None   # the export file the user picked
    files: list = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.browser}-{self.profile}".replace(" ", "_")

    @property
    def label(self) -> str:
        return self.name if self.profile in ("Default", "default-release", "default") \
            else f"{self.name} ({self.profile})"


# --- counting -------------------------------------------------------------------------------
def _sqlite_count(db: Path, sql: str) -> int:
    """Count rows from a copy, so a running browser's lock never matters."""
    if not db.is_file():
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / db.name
        try:
            shutil.copy2(db, copy)
            for ext in ("-wal", "-shm"):
                if Path(str(db) + ext).exists():
                    shutil.copy2(str(db) + ext, str(copy) + ext)
            con = sqlite3.connect(f"file:{copy}?mode=ro", uri=True)
            try:
                return int(con.execute(sql).fetchone()[0])
            finally:
                con.close()
        except (OSError, sqlite3.Error):
            return 0


def count_chromium_bookmarks(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0

    def walk(node):
        if node.get("type") == "url":
            return 1
        return sum(walk(c) for c in node.get("children", []))

    return sum(walk(root) for root in data.get("roots", {}).values() if isinstance(root, dict))


def count_firefox_logins(path: Path) -> int:
    try:
        return len(json.loads(path.read_text(encoding="utf-8")).get("logins", []))
    except (OSError, ValueError):
        return 0


# --- finding --------------------------------------------------------------------------------
def firefox_profiles(appdata: Path) -> list[BrowserProfile]:
    root = appdata / "Mozilla" / "Firefox"
    ini = root / "profiles.ini"
    if not ini.is_file():
        return []
    cfg = configparser.ConfigParser(interpolation=None)
    try:
        cfg.read(ini, encoding="utf-8")
    except configparser.Error:
        return []
    out = []
    for section in cfg.sections():
        if not section.startswith("Profile"):
            continue
        rel = cfg.get(section, "Path", fallback="")
        if not rel:
            continue
        path = (root / rel) if cfg.get(section, "IsRelative", fallback="1") == "1" else Path(rel)
        if not (path / "places.sqlite").is_file():
            continue
        name = cfg.get(section, "Name", fallback=path.name)
        p = BrowserProfile("firefox", "Firefox", "firefox", name, path, "firefox.exe")
        p.bookmarks = _sqlite_count(path / "places.sqlite",
                                    # real bookmarks only: not saved searches (place:) and
                                    # not the hidden copies Firefox keeps for each tag
                                    "SELECT count(*) FROM moz_bookmarks WHERE type=1 AND fk IN "
                                    "(SELECT id FROM moz_places WHERE url NOT LIKE 'place:%') "
                                    "AND parent NOT IN (SELECT id FROM moz_bookmarks WHERE parent="
                                    "(SELECT id FROM moz_bookmarks WHERE guid='tags________'))")
        p.history = _sqlite_count(path / "places.sqlite",
                                  "SELECT count(*) FROM moz_places WHERE visit_count > 0")
        p.passwords = count_firefox_logins(path / "logins.json")
        p.files = [path / f for f in FIREFOX_FILES if (path / f).is_file()]
        if p.bookmarks or p.history or p.passwords:
            out.append(p)
    return out


def chromium_profiles(env: dict) -> list[BrowserProfile]:
    out = []
    for bid, name, proc, rel, var, pw_url in CHROMIUM_BROWSERS:
        base = env.get(var)
        if not base:
            continue
        user_data = Path(base, *rel.split("\\"))
        if not user_data.is_dir():
            continue
        # Opera keeps its single profile right in the folder; others use Default, Profile 1...
        candidates = [user_data] if bid == "opera" else sorted(
            p for p in user_data.iterdir()
            if p.is_dir() and (p.name == "Default" or p.name.startswith("Profile ")))
        for prof in candidates:
            if not (prof / "Bookmarks").is_file() and not (prof / "History").is_file():
                continue
            p = BrowserProfile(bid, name, "chromium", prof.name if bid != "opera" else "Default",
                               prof, proc, password_url=pw_url)
            p.bookmarks = count_chromium_bookmarks(prof / "Bookmarks")
            p.history = _sqlite_count(prof / "History", "SELECT count(*) FROM urls")
            p.files = [prof / f for f in CHROMIUM_FILES if (prof / f).is_file()]
            if p.bookmarks or p.history:
                out.append(p)
    return out


def find_browsers(env: dict | None = None) -> list[BrowserProfile]:
    env = dict(os.environ if env is None else env)
    found = []
    if env.get("APPDATA"):
        found += firefox_profiles(Path(env["APPDATA"]))
    found += chromium_profiles(env)
    return found


# --- running? -------------------------------------------------------------------------------
def running_browsers(profiles: list[BrowserProfile]) -> list[str]:
    """Names of picked browsers that are open right now (their files are locked while open)."""
    if sys.platform != "win32" or not profiles:
        return []
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True,
                             timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                             stdin=subprocess.DEVNULL).stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return []
    names = []
    for p in profiles:
        if f'"{p.process}"' in out and p.name not in names:
            names.append(p.name)
    return names


def open_password_export(profile: BrowserProfile) -> bool:
    """Open the browser's own password page so the user can click Export."""
    if sys.platform != "win32":
        return False
    exe = shutil.which(profile.process)
    candidates = [exe] if exe else []
    for var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.environ.get(var)
        if not base:
            continue
        for rel in (r"Google\Chrome\Application\chrome.exe",
                    r"Microsoft\Edge\Application\msedge.exe",
                    r"BraveSoftware\Brave-Browser\Application\brave.exe",
                    r"Vivaldi\Application\vivaldi.exe", r"Programs\Opera\opera.exe"):
            if rel.lower().endswith(profile.process):
                candidates.append(str(Path(base) / rel))
    for exe in candidates:
        if exe and Path(exe).is_file():
            try:
                subprocess.Popen([exe, profile.password_url], stdin=subprocess.DEVNULL)
                return True
            except OSError:
                continue
    return False
