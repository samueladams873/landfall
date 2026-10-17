"""Landfall - Phase 0 test build.

Opens one window that proves the build pipeline works on Windows and Linux.
"""
import platform
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from landfall import __version__


def build_window() -> QWidget:
    window = QWidget()
    window.setWindowTitle(f"Landfall {__version__}")
    window.resize(480, 220)
    layout = QVBoxLayout(window)
    lines = [
        f"<h2>Landfall {__version__}</h2>",
        "Phase 0 test build - the pipeline works.",
        f"OS: {platform.system()} {platform.release()} ({platform.machine()})",
        f"Python: {platform.python_version()}",
    ]
    for text in lines:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
    return window


def main() -> int:
    app = QApplication(sys.argv)
    window = build_window()
    window.show()
    return app.exec()
