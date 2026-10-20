"""Find a Landfall bundle, check its password, and put files where they belong."""
from __future__ import annotations

import getpass
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import multivolumefile
import py7zr
from py7zr.callbacks import ExtractCallback

import tempfile

from landfall.pack import BUNDLE_NAME, DATA_FOLDER, INFO_NAME

MANIFEST = "landfall/manifest.json"


class WrongPassword(Exception):
    pass


class RestoreCancelled(Exception):
    pass


@dataclass
class Bundle:
    base: Path            # .../Landfall Move/Landfall-bundle.7z (without the .0001)

    @property
    def folder(self) -> Path:
        """Where the bundle's files live (the hidden data folder)."""
        return self.base.parent

    @property
    def move_folder(self) -> Path:
        """The folder the user sees ("Landfall Move")."""
        f = self.folder
        return f.parent if f.name == DATA_FOLDER else f

    @property
    def size(self) -> int:
        return sum(p.stat().st_size for p in self.folder.glob(BUNDLE_NAME + ".*"))


@dataclass
class RestoreResult:
    restored: int = 0
    already_there: int = 0
    renamed: list = field(default_factory=list)
    failed: list = field(default_factory=list)


def search_roots(home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    user = getpass.getuser()
    roots = [Path("/media") / user, Path("/run/media") / user, Path("/media"), Path("/mnt"),
             home]
    exe_dir = Path(sys.argv[0]).resolve().parent if sys.argv and sys.argv[0] else None
    if exe_dir:
        roots.insert(0, exe_dir)
    if os.environ.get("APPIMAGE"):
        roots.insert(0, Path(os.environ["APPIMAGE"]).parent)
    return roots


def find_bundles(roots: list[Path] | None = None, depth: int = 3) -> list[Bundle]:
    """Look a few folders deep under each root for Landfall-bundle.7z.0001."""
    found: dict[Path, Bundle] = {}
    for root in roots if roots is not None else search_roots():
        if not root.is_dir():
            continue
        stack = [(root, 0)]
        while stack:
            folder, level = stack.pop()
            hit = None
            for data in (folder / DATA_FOLDER, folder):  # new layout, then older bundles
                if (data / (BUNDLE_NAME + ".0001")).is_file():
                    hit = data
                    break
            if hit:
                key = (hit / (BUNDLE_NAME + ".0001")).resolve()
                found.setdefault(key, Bundle(hit / BUNDLE_NAME))
                continue
            if level >= depth:
                continue
            try:
                for entry in os.scandir(folder):
                    if entry.is_dir(follow_symlinks=False) and not entry.name.startswith("."):
                        stack.append((Path(entry.path), level + 1))
            except OSError:
                continue
    return sorted(found.values(), key=lambda b: str(b.base))


def _open(bundle: Bundle, password: str) -> py7zr.SevenZipFile:
    vol = multivolumefile.open(str(bundle.base), mode="rb")
    try:
        return py7zr.SevenZipFile(vol, "r", password=password)
    except Exception as err:
        vol.close()
        raise WrongPassword(str(err)) from err


def read_manifest(bundle: Bundle, password: str) -> dict:
    """Unlock the small info file and return the manifest. Raises WrongPassword."""
    info = bundle.folder / INFO_NAME
    try:
        with tempfile.TemporaryDirectory() as tmp:
            if info.is_file():
                with py7zr.SevenZipFile(info, "r", password=password) as z:
                    z.extract(path=tmp, targets=[MANIFEST])
            else:  # older bundles: the manifest only lives inside the main bundle
                with _open(bundle, password) as z:
                    z.extract(path=tmp, targets=[MANIFEST])
            return json.loads((Path(tmp) / MANIFEST).read_text(encoding="utf-8"))
    except WrongPassword:
        raise
    except Exception as err:
        raise WrongPassword(str(err)) from err


def _free_name(dest: Path) -> Path:
    """'photo.jpg' -> 'photo (from Windows).jpg', then '(from Windows 2)' and so on."""
    stem, suffix = dest.stem, dest.suffix
    n = 1
    while True:
        tag = "from Windows" if n == 1 else f"from Windows {n}"
        candidate = dest.with_name(f"{stem} ({tag}){suffix}")
        if not candidate.exists():
            return candidate
        n += 1


class _Progress(ExtractCallback):
    def __init__(self, total, progress, cancelled):
        self.total, self.done = total, 0
        self.progress, self.cancelled = progress, cancelled
        self.last = 0.0

    def report_start_preparation(self):
        pass

    def report_start(self, processing_file_path, processing_bytes):
        pass  # py7zr runs this on its own thread; errors raised here are swallowed

    def report_update(self, decompressed_bytes):
        pass

    def report_end(self, processing_file_path, wrote_bytes):
        self.done += int(wrote_bytes or 0)
        now = time.monotonic()
        if now - self.last > 0.1:
            self.last = now
            self.progress(min(self.done, self.total), self.total, processing_file_path)

    def report_postprocess(self):
        pass

    def report_warning(self, message):
        pass


def restore(bundle: Bundle, password: str, folders: list[str], destinations: dict[str, Path],
            manifest: dict, progress=lambda done, total, name: None,
            cancelled=lambda: False, home: Path | None = None) -> RestoreResult:
    """Unpack the chosen folders. Never overwrites a file that's already there."""
    home = home or Path.home()
    wanted = {f["path"]: f["size"] for f in manifest.get("files", [])
              if f["path"].split("/", 1)[0] in folders}
    total = sum(wanted.values())
    staging = home / f".landfall-unpack-{int(time.time())}"
    staging.mkdir(parents=True)
    result = RestoreResult()
    try:
        if cancelled():
            raise RestoreCancelled()
        if wanted:
            with _open(bundle, password) as z:
                z.extract(path=staging, targets=list(wanted),
                          callback=_Progress(total, progress, cancelled))
        if cancelled():  # stopped while unpacking: move nothing into place
            raise RestoreCancelled()
        for name in folders:        # bring empty folders along too (e.g. "Saved Games")
            if name in destinations:
                destinations[name].mkdir(parents=True, exist_ok=True)
        for rel in wanted:
            src = staging / rel
            top, _, rest = rel.partition("/")
            dest = destinations[top] / rest
            if not src.is_file():
                result.failed.append(rel)
                continue
            if dest.exists():
                if dest.is_file() and dest.stat().st_size == src.stat().st_size:
                    result.already_there += 1
                    continue
                dest = _free_name(dest)
                result.renamed.append(str(dest))
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            if dest.suffix.lower() == ".url":
                dest = windows_url_to_link(dest)
            result.restored += 1
        progress(total, total, "")
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return result


def windows_url_to_link(path: Path) -> Path:
    """A Windows web shortcut (.url) does nothing on Linux. Turn it into a Linux web link
    (.desktop, Type=Link) with the same name, so double-clicking still opens the site."""
    import configparser
    cfg = configparser.ConfigParser(interpolation=None)
    try:
        cfg.read_string(path.read_text(encoding="utf-8", errors="replace"))
        url = cfg.get("InternetShortcut", "URL", fallback="").strip()
    except (configparser.Error, OSError):
        return path
    if not url.startswith(("http://", "https://")):
        return path
    link = path.with_suffix(".desktop")
    if link.exists():
        return path
    link.write_text("[Desktop Entry]\nType=Link\n"
                    f"Name={path.stem}\nURL={url}\nIcon=text-html\n", encoding="utf-8")
    link.chmod(0o755)
    path.unlink()
    return link


def extract_private(bundle: Bundle, password: str, prefix: str, dest: Path) -> list[str]:
    """Unpack Landfall's own data (e.g. landfall/browsers/...) into dest. Returns the names."""
    with _open(bundle, password) as z:
        names = [n for n in z.getnames() if n.startswith(prefix)]
    if names:
        with _open(bundle, password) as z:
            z.extract(path=dest, targets=names)
    return names
