"""Landfall on Windows: the moving wizard that packs everything up."""
from __future__ import annotations

import os
import sys
import time
import webbrowser
from pathlib import Path

from PySide6.QtWidgets import (QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QProgressBar, QPushButton, QScrollArea, QTabWidget,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from landfall.drives import list_drives
from landfall.mapping import GROUP_ALT, GROUP_SAME, GROUPS, match_all
from landfall.pack import PackCancelled, pack, space_needed
from landfall.report import build_html, option_text
from landfall.scan.apps import scan_apps
from landfall.scan.folders import find_folders, human_size, measure
from landfall.scan.hardware import hardware_notes, scan_hardware
from landfall.ui import (ICON, ICONS, ChoiceRow, HeroPage, Page, Shell, card, folder_icon,
                         label, logo, make_app, picture, set_role, start_task)

__all__ = ["ICON", "Wizard", "build_window", "main", "label", "logo", "set_role", "start_task"]

COMING_SOON = [
    "Browser bookmarks, saved passwords and history",
    "Email and contacts",
    "Wi-Fi networks and passwords",
    "Wallpaper and fonts",
    "Game saves",
    "Product keys and licenses list",
]
STEPS = ["Welcome", "Check this PC", "Choose what to move", "Choose where to save",
         "Packing", "All done"]


class Wizard(Shell):
    WELCOME, CHECK, WHAT, WHERE, PACKING, DONE = range(6)

    def __init__(self):
        super().__init__(STEPS, "Moving Wizard")
        self.setWindowTitle("Landfall Moving Wizard")
        self.grouped = self.hw = None
        self.folders = []
        self.measured = False
        self.drives = []
        self.result = None
        self._cancel_pack = False
        self.folder_rows: dict[str, ChoiceRow] = {}
        self.back_btn.clicked.connect(self.on_back)
        self.next_btn.clicked.connect(self.on_next)
        for build in (self._page_welcome, self._page_check, self._page_what,
                      self._page_where, self._page_packing, self._page_done):
            self.stack.addWidget(build())
        self.go(self.WELCOME)

    # --- pages ------------------------------------------------------------
    def _page_welcome(self):
        page = HeroPage("Welcome to Landfall",
                        "Move from Windows to Linux without losing a thing.")
        frame, box = card()
        box.addWidget(label("Here's what happens next", "Section"))
        for icon, title, text in (
                ("Apps", "Check this PC", "See which of your apps and devices work on Linux."),
                ("Documents", "Choose what to move", "Documents, pictures, music and more."),
                ("Downloads", "Pack it up", "Everything goes onto a USB drive, locked with "
                                            "a password you choose.")):
            row = QHBoxLayout()
            row.addWidget(picture(ICONS / f"{icon}.svg", 30))
            row.addSpacing(10)
            words = QWidget()
            w = QVBoxLayout(words)
            w.setContentsMargins(0, 0, 0, 0)
            w.setSpacing(0)
            w.addWidget(label(f"<b>{title}</b>"))
            w.addWidget(label(text, "Muted"))
            row.addWidget(words, 1)
            box.addLayout(row)
        page.body.addWidget(frame)
        page.body.addSpacing(6)
        page.body.addWidget(label("\u2714  Landfall only reads from this PC. It never changes, "
                                  "deletes or moves anything here.", "Good"))
        page.body.addStretch(1)
        return page

    def _page_check(self):
        page = Page("Checking this PC", "Here's how ready your apps and devices are for Linux.")
        self.check_status = label("Getting ready...", "Section")
        page.body.addWidget(self.check_status)
        tabs = QTabWidget()
        self.apps_tree = QTreeWidget()
        self.apps_tree.setHeaderLabels(["Your Windows app", "On Linux"])
        self.apps_tree.setColumnWidth(0, 300)
        self.hw_tree = QTreeWidget()
        self.hw_tree.setHeaderLabels(["Part", "Details"])
        self.hw_tree.setColumnWidth(0, 150)
        for tree in (self.apps_tree, self.hw_tree):
            tree.setRootIsDecorated(False)
        tabs.addTab(self.apps_tree, "Apps")
        tabs.addTab(self.hw_tree, "Hardware")
        page.body.addWidget(tabs, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        self.save_report_btn = QPushButton("Save this report")
        self.save_report_btn.setEnabled(False)
        self.save_report_btn.clicked.connect(self.save_report)
        row.addWidget(self.save_report_btn)
        page.body.addLayout(row)
        return page

    def _page_what(self):
        page = Page("Choose what to move", "Tick what you want to bring to your Linux PC.")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        holder.setObjectName("Content")
        self.what_box = QVBoxLayout(holder)
        self.what_box.setContentsMargins(0, 0, 6, 0)
        self.what_box.setSpacing(8)
        scroll.setWidget(holder)
        page.body.addWidget(scroll, 1)
        self.what_total = label("", "Section")
        page.body.addWidget(self.what_total)
        return page

    def _page_where(self):
        page = Page("Choose where to save", "Pick a USB drive or external disk, then a password.")
        frame, box = card()
        top = QHBoxLayout()
        top.addWidget(label("Save to", "Section", wrap=False))
        top.addStretch(1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh_drives)
        top.addWidget(refresh)
        box.addLayout(top)
        self.drive_list = QListWidget()
        self.drive_list.setMaximumHeight(120)
        self.drive_list.currentRowChanged.connect(lambda _: self.update_where())
        box.addWidget(self.drive_list)
        self.space_label = label("")
        box.addWidget(self.space_label)
        page.body.addWidget(frame)

        frame2, box2 = card()
        box2.addWidget(label("Choose a password", "Section"))
        box2.addWidget(label("You'll type it once more on your Linux PC. Write it down: if it's "
                             "lost, nobody can open your files, not even Landfall.", "Muted"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        self.pw1, self.pw2 = QLineEdit(), QLineEdit()
        for field in (self.pw1, self.pw2):
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.textChanged.connect(lambda _: self.update_where())
        self.pw1.setPlaceholderText("At least 6 characters")
        self.pw2.setPlaceholderText("Type it again")
        grid.addWidget(QLabel("Password"), 0, 0)
        grid.addWidget(self.pw1, 0, 1)
        grid.addWidget(QLabel("Confirm"), 1, 0)
        grid.addWidget(self.pw2, 1, 1)
        show = QCheckBox("Show password")
        show.toggled.connect(lambda on: [f.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password)
            for f in (self.pw1, self.pw2)])
        grid.addWidget(show, 2, 1)
        box2.addLayout(grid)
        self.pw_label = label("")
        box2.addWidget(self.pw_label)
        page.body.addWidget(frame2)
        page.body.addStretch(1)
        return page

    def _page_packing(self):
        page = Page("Packing your things", "Keep the drive plugged in. Big folders take a while.")
        frame, box = card()
        self.pack_status = label("Starting...", "Section")
        box.addWidget(self.pack_status)
        self.pack_bar = QProgressBar()
        self.pack_bar.setRange(0, 1000)
        box.addWidget(self.pack_bar)
        self.pack_file = label("", "Muted")
        box.addWidget(self.pack_file)
        row = QHBoxLayout()
        row.addStretch(1)
        self.stop_btn = QPushButton("Stop packing")
        self.stop_btn.clicked.connect(self.stop_packing)
        row.addWidget(self.stop_btn)
        box.addLayout(row)
        page.body.addWidget(frame)
        page.body.addStretch(1)
        return page

    def _page_done(self):
        page = HeroPage("All packed!", "Your things are ready to move.")
        frame, box = card()
        self.done_summary = label("")
        box.addWidget(self.done_summary)
        page.body.addWidget(frame)
        frame2, box2 = card()
        box2.addWidget(label("On your new Linux PC", "Section"))
        for n, line in enumerate((
                "Plug in the USB drive and open the \u201cLandfall Move\u201d folder.",
                "Double-click the Landfall installer for your Linux, then click Install.",
                "Open Landfall from your app menu and type your password."), 1):
            box2.addWidget(label(f"<b>{n}.</b>&nbsp;&nbsp;{line}"))
        box2.addWidget(label("The \u201cSTART HERE\u201d file on the drive has the same steps.",
                             "Muted"))
        page.body.addWidget(frame2)
        row = QHBoxLayout()
        open_btn = QPushButton("Open the Landfall Move folder")
        open_btn.clicked.connect(self.open_result_folder)
        row.addWidget(open_btn)
        row.addStretch(1)
        page.body.addLayout(row)
        page.body.addStretch(1)
        return page

    # --- navigation -------------------------------------------------------
    def go(self, index: int):
        self.stack.setCurrentIndex(index)
        self.set_step(index)
        if index == self.CHECK and self.grouped is None:
            self.start_check()
        if index == self.WHAT and not self.folders:
            self.start_measure()
        if index == self.WHERE:
            self.refresh_drives()
        self.update_buttons()

    def update_buttons(self):
        i = self.stack.currentIndex()
        self.back_btn.setVisible(i not in (self.WELCOME, self.DONE))
        self.back_btn.setEnabled(i != self.PACKING)
        self.cancel_btn.setVisible(i != self.DONE)
        self.next_btn.setText({self.WELCOME: "Get started", self.WHERE: "Start packing",
                               self.DONE: "Finish"}.get(i, "Next"))
        self.next_btn.setEnabled({
            self.WELCOME: True, self.CHECK: self.grouped is not None, self.WHAT: self.measured,
            self.WHERE: self._where_ready(), self.PACKING: False, self.DONE: True}[i])

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
            if QMessageBox.question(self, "Stop packing?",
                                    "Packing isn't finished. Stop and close Landfall?") \
                    != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._cancel_pack = True
        event.accept()

    # --- step: check this PC ---------------------------------------------
    def start_check(self):
        self.check_status.setText("Looking at your apps and hardware. This takes about "
                                  "30 seconds...")
        start_task(self, lambda report: (match_all(scan_apps()), scan_hardware()),
                   self.show_check, self.task_failed)

    def show_check(self, result):
        self.grouped, self.hw = result
        total = sum(len(v) for v in self.grouped.values())
        ready = len(self.grouped[GROUP_SAME]) + len(self.grouped[GROUP_ALT])
        set_role(self.check_status, "Good" if total and ready == total else "Section")
        self.check_status.setText(f"{ready} of {total} of your apps work on Linux or have "
                                  "a Linux alternative.")
        self.apps_tree.clear()
        self.apps_tree.setRootIsDecorated(True)
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
        for key, name in (("windows", "Windows"), ("model", "Computer"), ("cpu", "Processor"),
                          ("ram_gb", "Memory (GB)"), ("gpu", "Graphics"), ("wifi", "Wi-Fi"),
                          ("ethernet", "Ethernet"), ("bluetooth", "Bluetooth"),
                          ("webcam", "Webcam"), ("printers", "Printers"), ("disks", "Disks"),
                          ("boot_mode", "Boot mode"), ("secure_boot", "Secure Boot")):
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

    # --- step: choose what to move ---------------------------------------
    def start_measure(self):
        self.folders = find_folders()
        self.what_box.addWidget(label("Your folders", "Section"))
        for folder in self.folders:
            row = ChoiceRow(folder_icon(folder.name), folder.name, "Measuring...")
            row.box.toggled.connect(lambda _: self.update_total())
            self.folder_rows[folder.name] = row
            self.what_box.addWidget(row)
        if not self.folders:
            self.what_box.addWidget(label("No personal folders were found.", "Muted"))
        apps = ChoiceRow(ICONS / "Apps.svg", "Your app list",
                         "So Linux can install the matching apps", True, False)
        apps.title.setStyleSheet("")
        self.what_box.addWidget(apps)
        self.what_box.addSpacing(8)
        self.what_box.addWidget(label("Coming soon", "Section"))
        for item in COMING_SOON:
            self.what_box.addWidget(ChoiceRow(ICONS / "Soon.svg", item, "", False, False))
        self.what_box.addStretch(1)
        self.what_total.setText("Measuring your folders...")

        def work(report):
            for folder in self.folders:
                measure(folder)
                report(folder)
            return True

        start_task(self, work, self.measure_done, self.task_failed, self.show_measured)

    def show_measured(self, folder):
        text = f"{folder.files:,} files  \u00b7  {human_size(folder.bytes)}"
        if folder.cloud_only:
            text += f"  \u00b7  {folder.cloud_only:,} online-only OneDrive files stay in the cloud"
        self.folder_rows[folder.name].detail.setText(text)

    def measure_done(self, _):
        self.measured = True
        self.update_total()
        self.update_buttons()

    def selected_folders(self):
        return [f for f in self.folders if self.folder_rows[f.name].box.isChecked()]

    def selected_bytes(self) -> int:
        return sum(f.bytes for f in self.selected_folders())

    def update_total(self):
        if self.measured:
            files = sum(f.files for f in self.selected_folders())
            self.what_total.setText(f"Total to move: {files:,} files, "
                                    f"{human_size(self.selected_bytes())}")

    # --- step: choose where ----------------------------------------------
    def refresh_drives(self):
        self.drives = list_drives()
        self.drive_list.clear()
        for d in self.drives:
            self.drive_list.addItem(QListWidgetItem(
                f"{d.title}   \u00b7   {human_size(d.free)} free of {human_size(d.total)}"))
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
            self.space_label.setText("No USB drive found. Plug one in, then click Refresh.")
        elif d and d.free >= need:
            set_role(self.space_label, "Good")
            self.space_label.setText(f"\u2714  Plenty of room: needs about {human_size(need)}, "
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
            self.pw_label.setText("\u2714  Passwords match.")
        self.update_buttons()

    # --- step: packing ---------------------------------------------------
    def start_pack(self):
        self._cancel_pack = False
        self.stop_btn.setEnabled(True)
        folders, drive, password = self.selected_folders(), self.current_drive(), self.pw1.text()
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
        return [{"name": r.app["name"], "group": group, "linux": r.options}
                for group, results in (self.grouped or {}).items() for r in results]

    def pack_progress(self, info):
        done, total, name = info
        self.pack_bar.setValue(int(1000 * done / total) if total else 1000)
        pct = int(100 * done / total) if total else 100
        self.pack_status.setText(f"{pct}%  \u00b7  {human_size(done)} of {human_size(total)}")
        self.pack_file.setText(name)

    def stop_packing(self):
        self._cancel_pack = True
        self.stop_btn.setEnabled(False)
        self.pack_status.setText("Stopping and cleaning up...")

    def pack_done(self, result):
        self.result = result
        text = (f"<b>{result.files:,} files</b> ({human_size(result.bytes)}) packed and locked "
                f"with your password in:<br><b>{result.folder}</b>")
        if result.skipped:
            text += (f"<br><br>{len(result.skipped):,} file(s) couldn't be read (for example, "
                     "open in another program) and were left out.")
        self.done_summary.setText(text)
        self.go(self.DONE)

    def pack_failed(self, err):
        self.stop_btn.setEnabled(True)
        if not isinstance(err, PackCancelled):
            QMessageBox.warning(self, "Packing stopped",
                                "Something went wrong while packing, so the unfinished copy "
                                f"was removed. Nothing on this PC was changed.\n\nDetails: {err}")
        self.go(self.WHERE)

    def open_result_folder(self):
        if self.result and sys.platform == "win32":
            os.startfile(self.result.folder)  # noqa: S606 - opens Explorer on our own folder

    def task_failed(self, err):
        QMessageBox.warning(self, "Something went wrong", f"Landfall hit a problem:\n{err}")


def build_window() -> QWidget:
    return Wizard()


def main() -> int:
    app = make_app()
    window = build_window()
    window.show()
    return app.exec()
