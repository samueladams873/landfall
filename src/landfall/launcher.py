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
        app.quit()

    QTimer.singleShot(2500, take)


def main() -> int:
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
