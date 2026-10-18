"""Pack the chosen folders into one password-locked bundle (7z, AES-256).

The bundle is split into 3.9 GB parts so it fits USB drives formatted FAT32.
Anyone can open it with free 7-Zip, or with Landfall on Linux.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import multivolumefile
import py7zr

from landfall import __version__

PART_SIZE = 3900 * 1024 * 1024
BUNDLE_NAME = "Landfall-bundle.7z"
MOVE_FOLDER = "Landfall Move"
FILTERS = [{"id": py7zr.FILTER_COPY}, {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}]
OVERHEAD = 1.01  # archive headers and padding
EXTRA = 50 * 1024 * 1024

README = """This folder was made by Landfall {version}, a free tool for moving from Windows to Linux.

Landfall-bundle.7z.0001 (and any .0002, .0003 ... parts) hold your files, locked with
the password you chose. Keep all the parts together.

To unpack on Linux: plug this drive in and double-click Landfall.
To open it anywhere else: use free 7-Zip (https://www.7-zip.org) and open the .0001 file.

Learn more: https://github.com/samueladams873/landfall
"""


class PackCancelled(Exception):
    pass


@dataclass
class PackResult:
    folder: Path
    parts: list[Path]
    files: int
    bytes: int
    skipped: list[str] = field(default_factory=list)


def space_needed(total_bytes: int) -> int:
    return int(total_bytes * OVERHEAD) + EXTRA


def choose_output_folder(drive_root: Path) -> Path:
    candidate = drive_root / MOVE_FOLDER
    n = 2
    while candidate.exists():
        candidate = drive_root / f"{MOVE_FOLDER} ({n})"
        n += 1
    return candidate


def _long_path(p: Path) -> str:
    s = str(p)
    if sys.platform == "win32" and len(s) > 240 and not s.startswith("\\\\?\\"):
        return "\\\\?\\" + s
    return s


def _readable(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            f.read(1)
        return True
    except OSError:
        return False


def pack(folders, password: str, drive_root: Path, extra_data: dict | None = None,
         progress=lambda done, total, name: None, cancelled=lambda: False) -> PackResult:
    """folders: measured FolderInfo objects. Never writes anywhere except drive_root."""
    if not password:
        raise ValueError("A password is required.")
    out_dir = choose_output_folder(Path(drive_root))
    out_dir.mkdir(parents=True)
    bundle = out_dir / BUNDLE_NAME
    total = sum(f.bytes for f in folders)
    done = files = 0
    skipped: list[str] = []
    manifest_files = []
    try:
        with multivolumefile.open(str(bundle), mode="wb", volume=PART_SIZE) as vol:
            with py7zr.SevenZipFile(vol, "w", filters=FILTERS, password=password) as z:
                z.set_encrypted_header(True)
                for folder in folders:
                    for src, rel, size in folder.file_list:
                        if cancelled():
                            raise PackCancelled()
                        arcname = rel.as_posix()
                        progress(done, total, arcname)
                        source = _long_path(src)
                        if not _readable(source):
                            skipped.append(arcname)
                            continue
                        z.write(source, arcname)
                        manifest_files.append({"path": arcname, "size": size})
                        done += size
                        files += 1
                manifest = {
                    "landfall_version": __version__,
                    "created": datetime.now().isoformat(timespec="seconds"),
                    "folders": [f.name for f in folders],
                    "files": manifest_files,
                    "skipped": skipped,
                    **(extra_data or {}),
                }
                z.writestr(json.dumps(manifest, indent=1), "landfall/manifest.json")
        progress(total, total, "")
    except BaseException:
        for part in out_dir.glob(BUNDLE_NAME + "*"):
            part.unlink(missing_ok=True)
        try:
            out_dir.rmdir()
        except OSError:
            pass
        raise
    (out_dir / "READ ME.txt").write_text(README.format(version=__version__), encoding="utf-8")
    parts = sorted(out_dir.glob(BUNDLE_NAME + ".*"))
    return PackResult(out_dir, parts, files, done, skipped)
