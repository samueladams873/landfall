"""Pack the chosen folders into one password-locked bundle (7z, AES-256).

The bundle is split into 3.9 GB parts so it fits USB drives formatted FAT32.
Anyone can open it with free 7-Zip, or with PenguinPort on Linux.
"""
from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import multivolumefile
import py7zr

from landfall import __version__

PART_SIZE = 3900 * 1024 * 1024
BUNDLE_NAME = "PenguinPort-bundle.7z"
INFO_NAME = "PenguinPort-info.7z"  # small locked file: list of contents, for a fast password check
MOVE_FOLDER = "PenguinPort Move"
DATA_FOLDER = ".landfall-data"  # hidden: users never need to open it; Landfall reads it
FILTERS = [{"id": py7zr.FILTER_COPY}, {"id": py7zr.FILTER_CRYPTO_AES256_SHA256}]
OVERHEAD = 1.01  # archive headers and padding
EXTRA = 50 * 1024 * 1024

# Linux installers carried inside the Windows app, copied next to the bundle.
LINUX_DIR = Path(__file__).parent / "data" / "linux"
INSTALLER_NAMES = {".deb": "PenguinPort for Ubuntu and Mint.deb", ".rpm": "PenguinPort for Fedora.rpm"}

README = """START HERE - made by PenguinPort {version}, a free tool for moving from Windows to Linux.

ON YOUR NEW LINUX PC
  1. Double-click the PenguinPort installer for your Linux:
       Ubuntu, Linux Mint, Zorin OS, Pop!_OS, elementary:  "PenguinPort for Ubuntu and Mint.deb"
       Fedora:                                              "PenguinPort for Fedora.rpm"
  2. Click Install and type your computer password.
  3. Open PenguinPort from your app menu and type your bundle password.

  You don't need to open or unzip anything yourself. PenguinPort finds your locked files on
  this drive and unpacks them for you.

PLEASE KEEP THIS WHOLE FOLDER TOGETHER
  Your files are stored, locked with your password, in a hidden folder inside it.

Learn more: https://github.com/voidwhereprohibited/penguinport
"""


def linux_installers() -> list[Path]:
    if not LINUX_DIR.is_dir():
        return []
    return sorted(p for p in LINUX_DIR.iterdir() if p.suffix in INSTALLER_NAMES)


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
    installers = sum(p.stat().st_size for p in linux_installers())
    return int(total_bytes * OVERHEAD) + EXTRA + installers


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
    move_dir = choose_output_folder(Path(drive_root))
    out_dir = move_dir / DATA_FOLDER
    out_dir.mkdir(parents=True)
    _hide(out_dir)
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
                    # browser data travels in its own private section ("landfall/..."),
                    # never unpacked as a folder
                    "folders": [f.name for f in folders if not f.name.startswith("landfall/")],
                    "files": manifest_files,
                    "skipped": skipped,
                    **(extra_data or {}),
                }
                z.writestr(json.dumps(manifest, indent=1), "landfall/manifest.json")
        progress(total, total, "")
    except BaseException:
        shutil.rmtree(move_dir, ignore_errors=True)
        raise
    with py7zr.SevenZipFile(out_dir / INFO_NAME, "w", filters=FILTERS, password=password) as z:
        z.set_encrypted_header(True)
        z.writestr(json.dumps(manifest, indent=1), "landfall/manifest.json")
    for installer in linux_installers():
        shutil.copyfile(installer, move_dir / INSTALLER_NAMES[installer.suffix])
    (move_dir / "START HERE.txt").write_text(README.format(version=__version__), encoding="utf-8")
    parts = sorted(out_dir.glob(BUNDLE_NAME + ".*"))
    return PackResult(move_dir, parts, files, done, skipped)


def _hide(path: Path) -> None:
    """Hide the data folder in Windows Explorer too (Linux already hides dot-folders)."""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02)  # FILE_ATTRIBUTE_HIDDEN


def _copy_shared(src: Path, dest: Path) -> bool:
    """Copy a file even if a browser has it open. Browsers keep bookmarks/history as plain
    files they read with a shared lock, so a normal copy works; if the OS still refuses,
    fall back to a byte-by-byte read with shared access. Returns True on success."""
    import shutil
    try:
        shutil.copy2(src, dest)
        return True
    except (OSError, shutil.Error):
        pass
    try:
        # Windows: open with full sharing so a running browser can't block the read
        with open(src, "rb") as fh, open(dest, "wb") as out:
            while chunk := fh.read(1 << 20):
                out.write(chunk)
        return True
    except OSError:
        return False


def browser_folders(profiles, staging: Path | None = None) -> list:
    """Turn picked browser profiles into pack-able groups under landfall/browsers/<key>/.

    Each browser file is first copied to a staging folder using a shared-read copy, so this
    works even while the browser is still open (no need to make the user close it). We pack
    from the copies."""
    import tempfile
    from landfall.scan.folders import FolderInfo, measure
    staging = staging or Path(tempfile.mkdtemp(prefix="penguinport-browsers-"))
    out = []
    for prof in profiles:
        dest_dir = staging / prof.key
        dest_dir.mkdir(parents=True, exist_ok=True)
        staged = []
        for f in prof.files:
            copy = dest_dir / f.name
            if _copy_shared(f, copy):
                staged.append(copy)
        if prof.password_csv:
            pwcopy = dest_dir / "passwords.csv"
            if _copy_shared(prof.password_csv, pwcopy):
                staged.append(pwcopy)
        if not staged:
            continue
        folder = FolderInfo(f"landfall/browsers/{prof.key}", dest_dir, only_files=staged)
        measure(folder)
        out.append(folder)
    return out


def browser_records(profiles) -> list[dict]:
    return [{"key": p.key, "browser": p.browser, "name": p.name, "family": p.family,
             "profile": p.profile, "bookmarks": p.bookmarks, "history": p.history,
             "passwords": p.passwords, "files": [f.name for f in p.files],
             "password_csv": bool(p.password_csv)} for p in profiles]
