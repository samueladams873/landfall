"""Landfall v0.1 - Linux readiness report (read-only)."""
from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QTabWidget, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget)

from landfall import __version__
from landfall.mapping import GROUP_SAME, GROUP_ALT, GROUPS, match_all
from landfall.report import build_html, option_text
from landfall.scan.apps import scan_apps
from landfall.scan.hardware import hardware_notes, scan_hardware


class ScanWorker(QObject):
    finished = Signal(dict, dict)
    progress = Signal(str)

    def run(self):
        self.progress.emit("Looking at your installed apps...")
        grouped = match_all(scan_apps())
        self.progress.emit("Checking your hardware...")
        hw = scan_hardware()
        self.finished.emit(grouped, hw)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Landfall {__version__}")
        self.resize(820, 600)
        self.grouped: dict | None = None
        self.hw: dict | None = None
        self._thread: QThread | None = None

        layout = QVBoxLayout(self)
        title = QLabel(f"<h2>Landfall {__version__}</h2>"
                       "Find out how ready this PC is for Linux. Landfall only looks; "
                       "it never changes anything on this computer.")
        title.setWordWrap(True)
        layout.addWidget(title)

        buttons = QHBoxLayout()
        self.scan_button = QPushButton("Scan this PC")
        self.scan_button.setMinimumHeight(40)
        self.scan_button.clicked.connect(self.start_scan)
        self.save_button = QPushButton("Save report")
        self.save_button.setMinimumHeight(40)
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_report)
        buttons.addWidget(self.scan_button)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

        self.status = QLabel("Click \u201cScan this PC\u201d to start.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.tabs = QTabWidget()
        self.apps_tree = QTreeWidget()
        self.apps_tree.setHeaderLabels(["Your Windows app", "On Linux"])
        self.apps_tree.setColumnWidth(0, 330)
        self.hw_tree = QTreeWidget()
        self.hw_tree.setHeaderLabels(["Part", "Details"])
        self.hw_tree.setColumnWidth(0, 160)
        self.tabs.addTab(self.apps_tree, "Apps")
        self.tabs.addTab(self.hw_tree, "Hardware")
        layout.addWidget(self.tabs, 1)

    # --- scanning -------------------------------------------------------
    def start_scan(self):
        self.scan_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self._thread = QThread(self)
        self._worker = ScanWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.status.setText)
        self._worker.finished.connect(self.show_results)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()

    def show_results(self, grouped: dict, hw: dict):
        self.grouped, self.hw = grouped, hw
        total = sum(len(v) for v in grouped.values())
        ready = len(grouped[GROUP_SAME]) + len(grouped[GROUP_ALT])
        self.status.setText(f"<b>{ready} of {total}</b> of your apps work on Linux or have "
                            "a Linux alternative. Click \u201cSave report\u201d to keep a copy.")
        self.fill_apps(grouped)
        self.fill_hardware(hw)
        self.scan_button.setText("Scan again")
        self.scan_button.setEnabled(True)
        self.save_button.setEnabled(True)

    def fill_apps(self, grouped: dict):
        self.apps_tree.clear()
        for group in GROUPS:
            parent = QTreeWidgetItem([f"{group} ({len(grouped[group])})", ""])
            font = parent.font(0)
            font.setBold(True)
            parent.setFont(0, font)
            for r in grouped[group]:
                linux = ", ".join(option_text(o) for o in r.options) or "Unknown"
                parent.addChild(QTreeWidgetItem([r.app["name"], linux]))
            self.apps_tree.addTopLevelItem(parent)
            parent.setExpanded(True)

    def fill_hardware(self, hw: dict):
        self.hw_tree.clear()
        labels = [("windows", "Windows"), ("model", "Computer"), ("cpu", "Processor"),
                  ("ram_gb", "Memory (GB)"), ("gpu", "Graphics"), ("wifi", "Wi-Fi"),
                  ("ethernet", "Ethernet"), ("bluetooth", "Bluetooth"), ("webcam", "Webcam"),
                  ("printers", "Printers"), ("disks", "Disks"), ("boot_mode", "Boot mode"),
                  ("secure_boot", "Secure Boot")]
        for key, label in labels:
            value = hw.get(key)
            text = ", ".join(value) if isinstance(value, list) else str(value)
            self.hw_tree.addTopLevelItem(QTreeWidgetItem([label, text or "None found"]))
        for note in hardware_notes(hw):
            self.hw_tree.addTopLevelItem(QTreeWidgetItem(["Heads-up", note]))

    # --- saving ---------------------------------------------------------
    def save_report(self):
        default = Path.home() / "Desktop" / "Landfall report.html"
        if not default.parent.exists():
            default = Path.home() / "Landfall report.html"
        path, _ = QFileDialog.getSaveFileName(self, "Save report", str(default),
                                              "Web page (*.html)")
        if not path:
            return
        try:
            Path(path).write_text(build_html(self.grouped, self.hw), encoding="utf-8")
        except OSError as err:
            QMessageBox.warning(self, "Couldn't save", f"The report couldn't be saved:\n{err}")
            return
        self.status.setText(f"Report saved to {path}")
        webbrowser.open(Path(path).as_uri())


def build_window() -> QWidget:
    return MainWindow()


def main() -> int:
    app = QApplication(sys.argv)
    window = build_window()
    window.show()
    return app.exec()
