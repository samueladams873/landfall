"""Where each Windows folder should land on Linux (XDG user folders)."""
from __future__ import annotations

import os
import re
from pathlib import Path

# Windows folder name -> XDG key
XDG_KEYS = {
    "Desktop": "XDG_DESKTOP_DIR",
    "Documents": "XDG_DOCUMENTS_DIR",
    "Pictures": "XDG_PICTURES_DIR",
    "Downloads": "XDG_DOWNLOAD_DIR",
    "Music": "XDG_MUSIC_DIR",
    "Videos": "XDG_VIDEOS_DIR",
}


def user_dirs(home: Path | None = None) -> dict[str, Path]:
    """Map each Windows folder name to the matching folder in this Linux account.

    Reads ~/.config/user-dirs.dirs so translated folder names (e.g. "Bilder") work.
    """
    home = home or Path.home()
    config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "user-dirs.dirs"
    found: dict[str, str] = {}
    try:
        for line in config.read_text(encoding="utf-8").splitlines():
            m = re.match(r'^\s*(XDG_\w+_DIR)\s*=\s*"(.*)"\s*$', line)
            if m:
                found[m.group(1)] = m.group(2).replace("$HOME", str(home))
    except OSError:
        pass
    result = {}
    for name, key in XDG_KEYS.items():
        path = Path(found[key]) if key in found else home / name
        if path == home:  # some setups point unused folders at $HOME itself
            path = home / name
        result[name] = path
    return result
