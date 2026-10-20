"""Re-creates the README screenshot gallery (docs/screenshots/*.png).

Run:  QT_QPA_PLATFORM=offscreen PYTHONPATH=src python tools/make_screenshots.py
Uses made-up sample data (the app list mirrors a real Windows 10 test VM); nothing on
this computer is scanned, changed or installed.
"""
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
sys.path.insert(0, str(ROOT / "src"))

from landfall.ui import make_app  # noqa: E402

app = make_app([])


def pump(seconds=0.4):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def shot(widget, name):
    pump()
    widget.grab().save(str(OUT / f"{name}.png"))
    print("saved", name)


def windows_side():
    from landfall import app as A
    from landfall.drives import Drive
    from landfall.mapping import builtin_apps, match_all
    from landfall.pack import PackResult
    from landfall.scan.folders import FolderInfo

    apps = [{"name": n} for n in (
        "Mozilla Firefox (x64 en-US)", "Steam", "Adobe Acrobat (64-bit)", "iTunes",
        "Microsoft 365 - en-us", "Microsoft Edge", "Microsoft OneDrive", "Spotify",
        "Discord", "VLC media player", "Adobe Photoshop 2025", "\u00b5Torrent")]
    hw = {"windows": "Windows 10 (10.0.19045)", "model": "Dell OptiPlex 790",
          "cpu": ["Intel(R) Core(TM) i7-2600 CPU @ 3.40GHz"], "ram_gb": 16,
          "gpu": ["NVIDIA GeForce GTX 1050"], "wifi": ["Intel Wi-Fi 6 AX200"],
          "ethernet": ["Intel 82579LM"], "bluetooth": [], "webcam": [], "printers": [],
          "disks": ["Samsung SSD 870 (500 GB)"], "boot_mode": "UEFI", "secure_boot": "On"}
    A.scan_apps = lambda: apps
    A.scan_hardware = lambda: hw
    tmp = Path(tempfile.mkdtemp())
    sizes = {"Desktop": (38, 41e6), "Documents": (1412, 3.1e9), "Pictures": (6230, 22.4e9),
             "Downloads": (214, 5.6e9), "Music": (980, 6.2e9), "Videos": (41, 18.9e9)}
    folders = []
    for n in sizes:
        (tmp / n).mkdir()
        folders.append(FolderInfo(n, tmp / n))
    A.find_folders = lambda: folders

    def fake_measure(f):
        f.files, f.bytes = int(sizes.get(f.name, (0, 0))[0]), int(sizes.get(f.name, (0, 0))[1])
        f.windows_only = 3 if f.name == "Desktop" else 0
        return f

    A.measure = fake_measure
    A.list_drives = lambda: [Drive("E:\\", "SANDISK 128GB", 118e9, 128e9, "exFAT", True)]
    w = A.Wizard()
    w.resize(1120, 720)
    w.show()
    shot(w, "win-1-welcome")
    w.go(w.CHECK)
    pump(5)
    shot(w, "win-2-check")
    w.go(w.PICK)
    pump(0.8)
    shot(w, "win-3-pick-apps")
    w.go(w.WHAT)
    pump(1.2)
    shot(w, "win-4-pick-files")
    w.go(w.WHERE)
    w.pw1.setText("correct horse")
    w.pw2.setText("correct horse")
    shot(w, "win-5-where")
    w.stack.setCurrentIndex(w.PACKING)
    w.set_step(w.PACKING)
    w.update_buttons()
    w.pack_progress((21.8e9, 56.2e9, "Pictures/Vacation 2024/IMG_2231.jpg"))
    shot(w, "win-6-packing")
    w.pack_done(PackResult(Path("E:/Landfall Move"), [], 8915, int(56.2e9)))
    shot(w, "win-7-done")
    w.close()


def linux_side():
    from landfall.linux import importer as I
    from landfall.linux.apps import AppChoice
    from landfall.linux.restore import RestoreResult

    import collections
    import pathlib
    pathlib.Path.home = classmethod(lambda cls: cls("/home/alex"))   # a neutral sample home
    Usage = collections.namedtuple("Usage", "total used free")
    I.shutil.disk_usage = lambda p: Usage(500e9, 120e9, 380e9)
    I.apps_mod.installed_flatpaks = lambda: set()
    I.apps_mod.installed_snaps = lambda: {"firefox"}
    I.apps_mod.flatpak_available = lambda: True
    v = I.Importer()
    v.dests = {n: Path("/home/alex") / n for n in
               ("Desktop", "Documents", "Pictures", "Downloads", "Music", "Videos")}
    v.resize(1120, 720)
    v.show()
    shot(v, "linux-1-welcome")
    v.go(v.UPDATE)
    v.update_state = "running"
    v.update_stages.set_stage(1)
    v.update_buttons()
    v.update_progress(("progress", 0, 350))
    v.update_progress(("progress", 126, 350, "gnome-shell-common"))
    shot(v, "linux-2-update")
    v.update_state = "done"
    picks = [
        {"windows": "Mozilla Firefox (x64 en-US), Microsoft Edge", "name": "Firefox",
         "flatpak": "org.mozilla.firefox", "snap": "firefox",
         "about": "Your best match: bookmarks and passwords can come over as they are."},
        {"windows": "Steam", "name": "Steam", "flatpak": "com.valvesoftware.Steam",
         "about": "The same Steam. Most Windows games run through Proton."},
        {"windows": "Microsoft 365 - en-us", "name": "LibreOffice",
         "flatpak": "org.libreoffice.LibreOffice", "about": "Opens and saves Word and Excel files."},
        {"windows": "iTunes", "name": "Strawberry", "flatpak": "org.strawberrymusicplayer.strawberry",
         "about": "Music library player, great for big collections."},
        {"windows": "Adobe Photoshop 2025", "name": "GIMP", "flatpak": "org.gimp.GIMP",
         "about": "Powerful photo editor."},
        {"windows": "Adobe Photoshop 2025", "name": "PhotoCraft", "new": True,
         "url": "https://github.com/storytold/photocraft",
         "about": "Brand-new free Photoshop look-alike."},
    ]
    files = [{"path": f"{n}/f{i}", "size": s} for n, c, s in (
        ("Documents", 1412, 2.2e6), ("Pictures", 6230, 3.6e6), ("Music", 980, 6.3e6),
        ("Downloads", 214, 26e6)) for i in range(c)]
    v.manifest = {"folders": ["Documents", "Pictures", "Music", "Downloads", "Saved Games"],
                  "extra_folders": ["Saved Games"], "files": files, "install": picks,
                  "created": "2026-10-20"}
    v.fill_what()
    v.go(v.WHAT)
    shot(v, "linux-3-review")
    v.stack.setCurrentIndex(v.WORKING)
    v.set_step(v.WORKING)
    v.update_buttons()
    v.work_progress(("app", 3, 5, "LibreOffice"))
    shot(v, "linux-4-setting-up")
    v.work_done((RestoreResult(restored=8836, already_there=0),
                 [("Steam", True, ""), ("LibreOffice", True, ""), ("Strawberry", True, ""),
                  ("GIMP", True, "")]))
    shot(v, "linux-5-done")
    v.close()


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    windows_side()
    linux_side()
