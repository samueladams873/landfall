"""List drives the bundle can be saved to (USB sticks and external disks)."""
from __future__ import annotations

import os
import shutil
import string
import sys
from dataclasses import dataclass

DRIVE_REMOVABLE, DRIVE_FIXED, DRIVE_REMOTE = 2, 3, 4


@dataclass
class Drive:
    root: str
    label: str
    free: int
    total: int
    filesystem: str
    removable: bool
    network: bool = False

    @property
    def title(self) -> str:
        kind = "USB drive" if self.removable else "Network drive" if self.network else "Drive"
        name = self.label or kind
        return f"{name} ({self.root.rstrip(chr(92))})"


def _volume_info(root: str) -> tuple[str, str]:
    import ctypes
    label = ctypes.create_unicode_buffer(261)
    fs = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(root), label, 261, None, None, None, fs, 261)
    return (label.value, fs.value) if ok else ("", "")


def list_drives() -> list[Drive]:
    """Every drive except the one Windows runs from. USB drives are listed first."""
    if sys.platform != "win32":
        return []
    import ctypes
    system_root = os.environ.get("SystemDrive", "C:").upper() + "\\"
    drives = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if root == system_root:
            continue
        kind = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))
        if kind not in (DRIVE_REMOVABLE, DRIVE_FIXED, DRIVE_REMOTE):
            continue
        try:
            usage = shutil.disk_usage(root)
        except OSError:
            continue  # empty card reader slot, etc.
        label, fs = _volume_info(root)
        drives.append(Drive(root, label, usage.free, usage.total, fs,
                            kind == DRIVE_REMOVABLE, kind == DRIVE_REMOTE))
    drives.sort(key=lambda d: (not d.removable, d.root))
    return drives
