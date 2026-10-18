"""Pick the right half of Landfall: the packer on Windows, the unpacker on Linux."""
import os
import sys


def _snapshot_hook():
    """Testing aid: LANDFALL_SNAPSHOT=/path.png saves a picture of the window, then quits."""
    path = os.environ.get("LANDFALL_SNAPSHOT")
    if not path:
        return
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    def take():
        app = QApplication.instance()
        windows = [w for w in app.topLevelWidgets() if w.isVisible()]
        if windows:
            windows[0].grab().save(path)
        for w in windows:
            w.close()  # closing (not quitting) lets Qt shut down in the normal, safe order

    QTimer.singleShot(2500, take)


def _selftest(out_path: str) -> int:
    """Testing aid: LANDFALL_SELFTEST=/path.txt proves the packaged app can run system
    programs (flatpak, xdg-open) with clean library settings, then exits."""
    from landfall.sysenv import run
    lines = []
    for cmd in (["flatpak", "--version"], ["flatpak", "remotes", "--user"], ["xdg-open", "--version"]):
        try:
            p = run(cmd, capture_output=True, text=True, timeout=60)
            lines.append(f"{' '.join(cmd)} -> exit {p.returncode}: {(p.stdout or p.stderr).strip()[:200]}")
        except Exception as err:  # noqa: BLE001 - this is a diagnostic
            lines.append(f"{' '.join(cmd)} -> FAILED {err}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0


def main() -> int:
    if os.environ.get("LANDFALL_SELFTEST"):
        return _selftest(os.environ["LANDFALL_SELFTEST"])
    mode = os.environ.get("LANDFALL_MODE") or ("pack" if sys.platform == "win32" else "unpack")
    if mode == "pack":
        from landfall.app import main as run
    else:
        from landfall.linux.importer import main as run
    from landfall import ui
    original = ui.make_app

    def make_app(*args, **kwargs):
        app = original(*args, **kwargs)
        _snapshot_hook()
        return app

    ui.make_app = make_app
    import landfall.app as win_app
    import landfall.linux.importer as lin_app
    win_app.make_app = lin_app.make_app = make_app
    return run()
