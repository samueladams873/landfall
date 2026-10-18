"""Landfall - the Windows to Linux moving wizard."""
from __future__ import annotations

import os
import sys
import time
import webbrowser
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QProgressBar, QPushButton, QStackedWidget,
                               QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from landfall import __version__
from landfall.drives import list_drives
from landfall.mapping import GROUP_ALT, GROUP_SAME, GROUPS, match_all
from landfall.pack import PackCancelled, pack, space_needed
from landfall.report import build_html, option_text
from landfall.scan.apps import scan_apps
from landfall.scan.folders import find_folders, human_size, measure
from landfall.scan.hardware import hardware_notes, scan_hardware
from landfall.theme import STYLE

DATA = Path(__file__).parent / "data"
ICON = DATA / "landfall.png"


def logo(size: int) -> QLabel:
    lab = QLabel()
    lab.setPixmap(QPixmap(str(ICON)).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))
    lab.setStyleSheet("background: transparent;")
    return lab


COMING_SOON = [
    "Browser bookmarks, saved passwords and history",
    "Email and contacts",
    "Wi-Fi networks and passwords",
    "Wallpaper and fonts",
    "Game saves",
    "Product keys and licenses list",
]


# --- background work -------------------------------------------------------
class Task(QObject):
    """Runs fn(report) on a background thread so the window never freezes."""
    done = Signal(object)
    failed = Signal(object)
    progress = Signal(object)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn(self.progress.emit))
        except BaseException as err:  # reported to the user, never silently lost
            self.failed.emit(err)


def start_task(owner, fn, on_done, on_failed=None, on_progress=None):
    thread = QThread(owner)
    task = Task(fn)
    task.moveToThread(thread)
    thread.started.connect(task.run)
    task.done.connect(on_done)
    if on_failed:
        task.failed.connect(on_failed)
    if on_progress:
        task.progress.connect(on_progress)
    task.done.connect(thread.quit)
    task.failed.connect(thread.quit)
    owner._tasks = [t for t in getattr(owner, "_tasks", []) if t[0].isRunning()]
    owner._tasks.append((thread, task))
    thread.start()
    return task


# --- page building blocks --------------------------------------------------
def set_role(widget: QWidget, role: str):
    """Switch a label between styles (Good / Warn / Muted) and repaint it."""
    widget.setObjectName(role)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def label(text: str, name: str | None = None, wrap: bool = True) -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(wrap)
    if name:
        lab.setObjectName(name)
    return lab


class HeaderPage(QWidget):
    """A page with the classic white header strip: bold title and a short subtitle."""

    def __init__(self, title: str, subtitle: str):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        header = QFrame()
        header.setObjectName("PageHeader")
        h = QVBoxLayout(header)
        h.setContentsMargins(16, 10, 16, 10)
        h.addWidget(label(title, "PageTitle"))
        h.addWidget(label(subtitle, "PageSub"))
        outer.addWidget(header)
        body = QWidget()
        self.body = QVBoxLayout(body)
        self.body.setContentsMargins(24, 16, 24, 12)
        outer.addWidget(body, 1)


class SidePage(QWidget):
    """A page with the blue side panel, used for Welcome and Finished."""

    def __init__(self, side_text: str):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        side = QFrame()
        side.setObjectName("SidePanel")
        side.setFixedWidth(190)
        s = QVBoxLayout(side)
        s.setContentsMargins(18, 24, 18, 24)
        s.addWidget(logo(120), 0, Qt.AlignmentFlag.AlignHCenter)
        s.addSpacing(12)
        s.addWidget(label(side_text, "SideText"))
        s.addStretch(1)
        s.addWidget(label(f"Landfall {__version__}\nFree and open source", "SideSmall"))
        row.addWidget(side)
        body = QWidget()
        body.setStyleSheet("background: white;")
        self.body = QVBoxLayout(body)
        self.body.setContentsMargins(28, 24, 28, 16)
        row.addWidget(body, 1)


# --- the wizard ------------------------------------------------------------
class Wizard(QWidget):
    WELCOME, CHECK, WHAT, WHERE, PACKING, DONE = range(6)

    def __init__(self):
        super().__init__()
        self.setObjectName("Root")
        self.setWindowTitle("Landfall Moving Wizard")
        self.resize(860, 620)
        self.grouped = self.hw = None
        self.folders = []
        self.measured = False
        self.drives = []
        self.result = None
        self._cancel_pack = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._banner())
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        root.addWidget(self._footer())

        for build in (self._page_welcome, self._page_check, self._page_what,
                      self._page_where, self._page_packing, self._page_done):
            self.stack.addWidget(build())
        self.go(self.WELCOME)

    # banner and footer
    def _banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("Banner")
        row = QHBoxLayout(banner)
        row.setContentsMargins(14, 8, 18, 8)
        row.addWidget(logo(46))
        row.addSpacing(6)
        b = QVBoxLayout()
        b.setSpacing(0)
        b.addWidget(label("Landfall Moving Wizard", "BannerTitle"))
        b.addWidget(label("Bring your files and settings from Windows to Linux", "BannerSub"))
        row.addLayout(b, 1)
        return banner

    def _footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("Footer")
        f = QHBoxLayout(footer)
        f.setContentsMargins(16, 10, 16, 10)
        f.addStretch(1)
        self.back_btn = QPushButton("< Back")
        self.next_btn = QPushButton("Next >")
        self.next_btn.setObjectName("Primary")
        self.cancel_btn = QPushButton("Cancel")
        self.back_btn.clicked.connect(self.on_back)
        self.next_btn.clicked.connect(self.on_next)
        self.cancel_btn.clicked.connect(self.close)
        f.addWidget(self.back_btn)
        f.addWidget(self.next_btn)
        f.addSpacing(10)
        f.addWidget(self.cancel_btn)
        return footer

    # pages
    def _page_welcome(self) -> QWidget:
        page = SidePage("Welcome")
        b = page.body
        b.addWidget(label("Welcome to the Landfall Moving Wizard", "BigTitle"))
        b.addSpacing(10)
        b.addWidget(label(
            "This wizard helps you move to Linux without losing anything. It will:"))
        for line in ("1.  Check which of your apps and devices work on Linux",
                     "2.  Let you pick what to bring: documents, pictures, and more",
                     "3.  Pack everything into one password-locked bundle on a USB drive"):
            b.addWidget(label(line))
        b.addSpacing(10)
        b.addWidget(label(
            "Landfall only reads from this computer. It never changes, deletes or moves "
            "anything here.", "Good"))
        b.addStretch(1)
        b.addWidget(label("Click Next to continue.", "Muted"))
        return page

    def _page_check(self) -> QWidget:
        page = HeaderPage("Checking this PC",
                          "See which of your apps and devices will work on Linux.")
        b = page.body
        self.check_status = label("Getting ready...")
        b.addWidget(self.check_status)
        tabs = QTabWidget()
        self.apps_tree = QTreeWidget()
        self.apps_tree.setHeaderLabels(["Your Windows app", "On Linux"])
        self.apps_tree.setColumnWidth(0, 320)
        self.hw_tree = QTreeWidget()
        self.hw_tree.setHeaderLabels(["Part", "Details"])
        self.hw_tree.setColumnWidth(0, 150)
        tabs.addTab(self.apps_tree, "Apps")
        tabs.addTab(self.hw_tree, "Hardware")
        b.addWidget(tabs, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        self.save_report_btn = QPushButton("Save this report...")
        self.save_report_btn.setEnabled(False)
        self.save_report_btn.clicked.connect(self.save_report)
        row.addWidget(self.save_report_btn)
        b.addLayout(row)
        return page

    def _page_what(self) -> QWidget:
        page = HeaderPage("Choose what to move",
                          "Tick the things you want to bring to your Linux PC.")
        b = page.body
        b.addWidget(label("<b>Your folders</b>"))
        self.folder_grid = QGridLayout()
        self.folder_grid.setColumnStretch(1, 1)
        b.addLayout(self.folder_grid)
        self.folder_checks: dict[str, QCheckBox] = {}
        self.folder_sizes: dict[str, QLabel] = {}
        b.addSpacing(8)
        always = QCheckBox("Your app list, so Linux can install the matching apps")
        always.setChecked(True)
        always.setEnabled(False)
        b.addWidget(always)
        b.addSpacing(8)
        b.addWidget(label("<b>Coming soon</b>"))
        for item in COMING_SOON:
            box = QCheckBox(item)
            box.setEnabled(False)
            b.addWidget(box)
        b.addStretch(1)
        self.what_total = label("")
        b.addWidget(self.what_total)
        return page

    def _page_where(self) -> QWidget:
        page = HeaderPage("Choose where to save",
                          "Pick a USB drive or external disk, then choose a password.")
        b = page.body
        top = QHBoxLayout()
        top.addWidget(label("<b>Save the bundle to:</b>", wrap=False))
        top.addStretch(1)
        refresh = QPushButton("Refresh list")
        refresh.clicked.connect(self.refresh_drives)
        top.addWidget(refresh)
        b.addLayout(top)
        self.drive_list = QListWidget()
        self.drive_list.setMaximumHeight(130)
        self.drive_list.currentRowChanged.connect(lambda _: self.update_where())
        b.addWidget(self.drive_list)
        self.space_label = label("")
        b.addWidget(self.space_label)
        b.addSpacing(10)
        b.addWidget(label("<b>Choose a password for the bundle</b>"))
        b.addWidget(label("You'll type it once more on your Linux PC. Write it down: "
                          "if it's lost, nobody can open the bundle, not even Landfall.",
                          "Muted"))
        grid = QGridLayout()
        self.pw1 = QLineEdit()
        self.pw2 = QLineEdit()
        for field in (self.pw1, self.pw2):
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.textChanged.connect(lambda _: self.update_where())
        grid.addWidget(QLabel("Password:"), 0, 0)
        grid.addWidget(self.pw1, 0, 1)
        grid.addWidget(QLabel("Type it again:"), 1, 0)
        grid.addWidget(self.pw2, 1, 1)
        show = QCheckBox("Show password")
        show.toggled.connect(lambda on: [f.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password)
            for f in (self.pw1, self.pw2)])
        grid.addWidget(show, 2, 1)
        b.addLayout(grid)
        self.pw_label = label("")
        b.addWidget(self.pw_label)
        b.addStretch(1)
        return page

    def _page_packing(self) -> QWidget:
        page = HeaderPage("Packing your things",
                          "This can take a while for big folders. Keep the drive plugged in.")
        b = page.body
        b.addStretch(1)
        self.pack_status = label("Starting...")
        b.addWidget(self.pack_status)
        self.pack_bar = QProgressBar()
        self.pack_bar.setRange(0, 1000)
        b.addWidget(self.pack_bar)
        self.pack_file = label("", "Muted")
        b.addWidget(self.pack_file)
        row = QHBoxLayout()
        row.addStretch(1)
        self.stop_btn = QPushButton("Stop packing")
        self.stop_btn.clicked.connect(self.stop_packing)
        row.addWidget(self.stop_btn)
        b.addLayout(row)
        b.addStretch(2)
        return page

    def _page_done(self) -> QWidget:
        page = SidePage("All packed!")
        b = page.body
        b.addWidget(label("Your bundle is ready", "BigTitle"))
        b.addSpacing(8)
        self.done_summary = label("")
        b.addWidget(self.done_summary)
        b.addSpacing(10)
        b.addWidget(label("<b>What's next</b>"))
        for line in ("1.  Safely remove the USB drive and plug it into your Linux PC.",
                     "2.  Open the \u201cLandfall Move\u201d folder on the drive.",
                     "3.  Double-click the Landfall installer for your Linux and click "
                     "Install.",
                     "4.  Open Landfall from your app menu and type your password."):
            b.addWidget(label(line))
        b.addWidget(label("The \u201cSTART HERE\u201d file in that folder has the same steps.",
                          "Muted"))
        b.addSpacing(10)
        open_btn = QPushButton("Open the Landfall Move folder")
        open_btn.clicked.connect(self.open_result_folder)
        row = QHBoxLayout()
        row.addWidget(open_btn)
        row.addStretch(1)
        b.addLayout(row)
        b.addStretch(1)
        return page

    # navigation
    def go(self, index: int):
        self.stack.setCurrentIndex(index)
        if index == self.CHECK and self.grouped is None:
            self.start_check()
        if index == self.WHAT and not self.folders:
            self.start_measure()
        if index == self.WHERE:
            self.refresh_drives()
        self.update_buttons()

    def update_buttons(self):
        i = self.stack.currentIndex()
        self.back_btn.setEnabled(i not in (self.WELCOME, self.PACKING, self.DONE))
        self.cancel_btn.setEnabled(i != self.DONE)
        self.next_btn.setText({self.WHERE: "Start packing", self.DONE: "Finish"}
                              .get(i, "Next >"))
        ok = {
            self.WELCOME: True,
            self.CHECK: self.grouped is not None,
            self.WHAT: self.measured,
            self.WHERE: self._where_ready(),
            self.PACKING: False,
            self.DONE: True,
        }[i]
        self.next_btn.setEnabled(ok)

    def on_back(self):
        self.go(max(self.stack.currentIndex() - 1, 0))

    def on_next(self):
        i = self.stack.currentIndex()
        if i == self.DONE:
            self.close()
        elif i == self.WHERE:
            self.go(self.PACKING)
            self.start_pack()
        else:
            self.go(i + 1)

    def closeEvent(self, event):
        if self.stack.currentIndex() == self.PACKING:
            answer = QMessageBox.question(self, "Stop packing?",
                                          "Packing isn't finished. Stop and close Landfall?")
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._cancel_pack = True
        event.accept()

    # step 1: check this PC
    def start_check(self):
        self.check_status.setText("Looking at your installed apps and hardware. "
                                  "This takes about 30 seconds...")

        def work(report):
            grouped = match_all(scan_apps())
            return grouped, scan_hardware()

        start_task(self, work, self.show_check, self.task_failed)

    def show_check(self, result):
        self.grouped, self.hw = result
        total = sum(len(v) for v in self.grouped.values())
        ready = len(self.grouped[GROUP_SAME]) + len(self.grouped[GROUP_ALT])
        self.check_status.setText(f"<b>{ready} of {total}</b> of your apps work on Linux "
                                  "or have a Linux alternative.")
        self.apps_tree.clear()
        for group in GROUPS:
            parent = QTreeWidgetItem([f"{group} ({len(self.grouped[group])})", ""])
            font = parent.font(0)
            font.setBold(True)
            parent.setFont(0, font)
            for r in self.grouped[group]:
                linux = ", ".join(option_text(o) for o in r.options) or "Unknown"
                parent.addChild(QTreeWidgetItem([r.app["name"], linux]))
            self.apps_tree.addTopLevelItem(parent)
            parent.setExpanded(True)
        self.hw_tree.clear()
        rows = [("windows", "Windows"), ("model", "Computer"), ("cpu", "Processor"),
                ("ram_gb", "Memory (GB)"), ("gpu", "Graphics"), ("wifi", "Wi-Fi"),
                ("ethernet", "Ethernet"), ("bluetooth", "Bluetooth"), ("webcam", "Webcam"),
                ("printers", "Printers"), ("disks", "Disks"), ("boot_mode", "Boot mode"),
                ("secure_boot", "Secure Boot")]
        for key, name in rows:
            value = self.hw.get(key)
            text = ", ".join(value) if isinstance(value, list) else str(value)
            self.hw_tree.addTopLevelItem(QTreeWidgetItem([name, text or "None found"]))
        for note in hardware_notes(self.hw):
            self.hw_tree.addTopLevelItem(QTreeWidgetItem(["Heads-up", note]))
        self.save_report_btn.setEnabled(True)
        self.update_buttons()

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
        webbrowser.open(Path(path).as_uri())

    # step 2: choose what to move
    def start_measure(self):
        self.folders = find_folders()
        for row, folder in enumerate(self.folders):
            box = QCheckBox(folder.name)
            box.setChecked(True)
            box.toggled.connect(lambda _: self.update_total())
            size = label("Measuring...", "Muted", wrap=False)
            self.folder_checks[folder.name] = box
            self.folder_sizes[folder.name] = size
            self.folder_grid.addWidget(box, row, 0)
            self.folder_grid.addWidget(size, row, 1)
        if not self.folders:
            self.folder_grid.addWidget(label("No personal folders were found.", "Muted"), 0, 0)
        self.what_total.setText("Measuring your folders...")

        def work(report):
            for folder in self.folders:
                measure(folder)
                report(folder)
            return True

        start_task(self, work, self.measure_done, self.task_failed, self.show_measured)

    def show_measured(self, folder):
        text = f"{folder.files:,} files, {human_size(folder.bytes)}"
        if folder.cloud_only:
            text += f"   ({folder.cloud_only:,} online-only OneDrive files left in the cloud)"
        self.folder_sizes[folder.name].setText(text)

    def measure_done(self, _):
        self.measured = True
        self.update_total()
        self.update_buttons()

    def selected_folders(self):
        return [f for f in self.folders if self.folder_checks[f.name].isChecked()]

    def selected_bytes(self) -> int:
        return sum(f.bytes for f in self.selected_folders())

    def update_total(self):
        if self.measured:
            chosen = self.selected_folders()
            files = sum(f.files for f in chosen)
            self.what_total.setText(f"<b>Total to move: {files:,} files, "
                                    f"{human_size(self.selected_bytes())}</b>")

    # step 3: choose where
    def refresh_drives(self):
        self.drives = list_drives()
        self.drive_list.clear()
        for d in self.drives:
            item = QListWidgetItem(f"{d.title}     {human_size(d.free)} free "
                                   f"of {human_size(d.total)}")
            self.drive_list.addItem(item)
        if self.drives:
            self.drive_list.setCurrentRow(0)
        self.update_where()

    def current_drive(self):
        row = self.drive_list.currentRow()
        return self.drives[row] if 0 <= row < len(self.drives) else None

    def _space_ok(self) -> bool:
        d = self.current_drive()
        return bool(d and d.free >= space_needed(self.selected_bytes()))

    def _pw_ok(self) -> bool:
        return len(self.pw1.text()) >= 6 and self.pw1.text() == self.pw2.text()

    def _where_ready(self) -> bool:
        return self._space_ok() and self._pw_ok()

    def update_where(self):
        need = space_needed(self.selected_bytes())
        d = self.current_drive()
        if not self.drives:
            set_role(self.space_label, "Warn")
            self.space_label.setText("No USB drive found. Plug one in, then click Refresh list.")
        elif d and d.free >= need:
            set_role(self.space_label, "Good")
            self.space_label.setText(f"Plenty of room: needs about {human_size(need)}, "
                                     f"{human_size(d.free)} free.")
        elif d:
            set_role(self.space_label, "Warn")
            self.space_label.setText(f"Not enough room: needs about {human_size(need)}, only "
                                     f"{human_size(d.free)} free. Pick a bigger drive or "
                                     "untick some folders.")
        p1, p2 = self.pw1.text(), self.pw2.text()
        if not p1:
            self.pw_label.setText("")
        elif len(p1) < 6:
            set_role(self.pw_label, "Warn")
            self.pw_label.setText("Use at least 6 characters.")
        elif p2 and p1 != p2:
            set_role(self.pw_label, "Warn")
            self.pw_label.setText("The two passwords don't match yet.")
        elif p1 == p2:
            set_role(self.pw_label, "Good")
            self.pw_label.setText("Passwords match.")
        self.update_buttons()

    # step 4: packing
    def start_pack(self):
        self._cancel_pack = False
        folders = self.selected_folders()
        drive = self.current_drive()
        password = self.pw1.text()
        extra = {"apps": self._app_records(), "hardware": self.hw or {}}
        self.pack_status.setText(f"Packing to {drive.title}...")

        def work(report):
            last = [0.0]

            def progress(done, total, name):
                now = time.monotonic()
                if now - last[0] > 0.1 or done >= total:
                    last[0] = now
                    report((done, total, name))

            return pack(folders, password, Path(drive.root), extra, progress,
                        lambda: self._cancel_pack)

        start_task(self, work, self.pack_done, self.pack_failed, self.pack_progress)

    def _app_records(self):
        records = []
        for group, results in (self.grouped or {}).items():
            for r in results:
                records.append({"name": r.app["name"], "group": group,
                                "linux": r.options})
        return records

    def pack_progress(self, info):
        done, total, name = info
        self.pack_bar.setValue(int(1000 * done / total) if total else 1000)
        self.pack_status.setText(f"Packed {human_size(done)} of {human_size(total)}")
        self.pack_file.setText(name)

    def stop_packing(self):
        self._cancel_pack = True
        self.stop_btn.setEnabled(False)
        self.pack_status.setText("Stopping and cleaning up...")

    def pack_done(self, result):
        self.result = result
        text = (f"Packed <b>{result.files:,} files</b> ({human_size(result.bytes)}), locked "
                f"with your password, into:<br><b>{result.folder}</b>")
        if result.skipped:
            text += (f"<br><br>{len(result.skipped):,} file(s) couldn't be read (for "
                     "example, open in another program) and were left out.")
        self.done_summary.setText(text)
        self.go(self.DONE)

    def pack_failed(self, err):
        self.stop_btn.setEnabled(True)
        if isinstance(err, PackCancelled):
            self.go(self.WHERE)
            return
        QMessageBox.warning(self, "Packing stopped",
                            f"Something went wrong while packing, so the partial bundle "
                            f"was removed. Nothing on this PC was changed.\n\nDetails: {err}")
        self.go(self.WHERE)

    def open_result_folder(self):
        if self.result and sys.platform == "win32":
            os.startfile(self.result.folder)  # noqa: S606 - opens Explorer on our folder

    def task_failed(self, err):
        QMessageBox.warning(self, "Something went wrong", f"Landfall hit a problem:\n{err}")


def build_window() -> QWidget:
    return Wizard()


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setWindowIcon(QIcon(str(ICON)))
    window = build_window()
    window.show()
    return app.exec()
