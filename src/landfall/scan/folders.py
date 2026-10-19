"""Find the user's personal folders and measure them. Read-only."""
from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

# Windows "Known Folder" IDs. Using these (not just ~/Documents) finds folders the
# user moved to another drive or that OneDrive redirected.
KNOWN_FOLDERS = [
    ("Desktop", "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}"),
    ("Documents", "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"),
    ("Pictures", "{33E28130-4E1E-4676-835A-98395C3BC3BB}"),
    ("Downloads", "{374DE290-123F-4565-9164-39C4925E467B}"),
    ("Music", "{4BD8D571-6D19-48D3-BE97-422220080E43}"),
    ("Videos", "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}"),
]

SKIP_NAMES = {"desktop.ini", "thumbs.db", ".ds_store"}
# Files that live only in the cloud (OneDrive "online-only"). Reading them would
# trigger a download, so we count them separately and leave them alone.
CLOUD_ONLY_ATTRS = 0x00400000 | 0x00040000 | 0x00001000  # RECALL_ON_DATA_ACCESS | RECALL_ON_OPEN | OFFLINE


@dataclass
class FolderInfo:
    name: str
    path: Path
    files: int = 0
    bytes: int = 0
    cloud_only: int = 0
    unreadable: int = 0
    file_list: list = field(default_factory=list, repr=False)  # (abs_path, rel_path, size)
    excludes: set = field(default_factory=set)       # paths inside the folder to leave out
    extra: bool = False                              # added by the user, not a standard folder
    only_files: list | None = None                   # a hand-picked list of single files


def _known_folder_path(guid: str) -> Path | None:
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD),
                    ("d3", wintypes.WORD), ("d4", ctypes.c_ubyte * 8)]

    u = uuid.UUID(guid)
    g = GUID(u.time_low, u.time_mid, u.time_hi_version,
             (ctypes.c_ubyte * 8)(*u.bytes[8:]))
    out = ctypes.c_wchar_p()
    try:
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None,
                                                      ctypes.byref(out)) != 0:
            return None
        return Path(out.value)
    except OSError:
        return None
    finally:
        if out:
            ctypes.windll.ole32.CoTaskMemFree(out)


def find_folders(home: Path | None = None) -> list[FolderInfo]:
    home = home or Path.home()
    found = []
    for name, guid in KNOWN_FOLDERS:
        path = _known_folder_path(guid) or home / name
        if path.is_dir():
            found.append(FolderInfo(name, path))
    return found


def measure(folder: FolderInfo, cancelled=lambda: False) -> FolderInfo:
    """Walk a folder, filling in file count, size and the list of files to pack."""
    folder.files = folder.bytes = folder.cloud_only = folder.unreadable = 0
    folder.file_list = []
    if folder.only_files is not None:
        for path in folder.only_files:
            try:
                size = Path(path).stat().st_size
            except OSError:
                folder.unreadable += 1
                continue
            folder.file_list.append((Path(path), Path(folder.name) / Path(path).name, size))
            folder.files += 1
            folder.bytes += size
        return folder
    excludes = {str(Path(p)) for p in folder.excludes}
    stack = [folder.path]
    while stack:
        if cancelled():
            break
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            folder.unreadable += 1
            continue
        for entry in entries:
            if excludes and str(Path(entry.path)) in excludes:
                continue  # the user unticked this one
            try:
                attrs = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
                is_junction = getattr(entry, "is_junction", lambda: False)()
                if entry.is_symlink() or is_junction:
                    continue  # never follow links/junctions out of the folder
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                    continue
                if entry.name.lower() in SKIP_NAMES:
                    continue
                if attrs & CLOUD_ONLY_ATTRS:
                    folder.cloud_only += 1
                    continue
                size = entry.stat(follow_symlinks=False).st_size
            except OSError:
                folder.unreadable += 1
                continue
            rel = Path(entry.path).relative_to(folder.path)
            folder.file_list.append((Path(entry.path), Path(folder.name) / rel, size))
            folder.files += 1
            folder.bytes += size
    return folder


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "bytes" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} bytes"


def unique_name(wanted: str, taken) -> str:
    name, n = wanted or "Folder", 2
    while name in taken:
        name = f"{wanted} ({n})"
        n += 1
    return name


def extra_folder(path, taken) -> FolderInfo:
    """A folder the user added from anywhere on the PC (e.g. C:\\Projects)."""
    path = Path(path)
    return FolderInfo(unique_name(path.name or path.anchor.strip(":\\/"), taken), path,
                      extra=True)


def extra_files(paths, taken) -> FolderInfo:
    """Single files the user picked; they travel together in one "Other files" folder."""
    paths = [Path(p) for p in paths]
    return FolderInfo(unique_name("Other files", taken), paths[0].parent if paths else Path("."),
                      extra=True, only_files=paths)
