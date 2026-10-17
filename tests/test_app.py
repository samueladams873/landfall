import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from landfall import __version__
from landfall.app import build_window


def test_window_builds():
    app = QApplication.instance() or QApplication([])
    window = build_window()
    assert window.windowTitle() == f"Landfall {__version__}"
