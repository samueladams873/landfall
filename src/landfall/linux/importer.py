"""Landfall on Linux: unpack the bundle made on Windows and set up the new PC."""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QProgressBar, QPushButton, QScrollArea,
                               QStackedWidget, QVBoxLayout, QWidget)

from landfall import __version__
from landfall.app import (ICON, HeaderPage, SidePage, label, logo, set_role, start_task)
from landfall.linux import apps as apps_mod
from landfall.linux.dirs import user_dirs
from landfall.linux.restore import (RestoreCancelled, WrongPassword, find_bundles,
                                    read_manifest, restore)
from landfall.scan.folders import human_size
from landfall.theme import STYLE


class Importer(QWidget):
    WELCOME, FIND, PASSWORD, WHAT, APPS, WORKING, DONE = range(7)

    def __init__(self):
        super().__init__()
        self.setObjectName("Root")
        self.setWindowTitle("Landfall Moving Wizard")
        self.resize(860, 620)
        self.bundles = []
        self.bundle = None
        self.manifest = None
        self.password = ""
        self.dests = user_dirs()
        self.folder_checks: dict[str, QCheckBox] = {}
        self.app_checks: list[tuple[QCheckBox, apps_mod.AppChoice]] = []
        self.link_apps: list[apps_mod.AppChoice] = []
        self._cancel = False
        self.restore_result = None
        self.app_results: list[tuple[str, bool, str]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._banner())
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        root.addWidget(self._footer())
        for build in (self._page_welcome, self._page_find, self._page_password,
                      self._page_what, self._page_apps, self._page_working, self._page_done):
            self.stack.addWidget(build())
        self.go(self.WELCOME)

    # chrome -------------------------------------------------------------
    def _banner(self):
        banner = QFrame()
        banner.setObjectName("Banner")
        row = QHBoxLayout(banner)
        row.setContentsMargins(14, 8, 18, 8)
        row.addWidget(logo(46))
        row.addSpacing(6)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(label("Landfall Moving Wizard", "BannerTitle"))
        col.addWidget(label("Welcome to Linux. Let's bring your things over.", "BannerSub"))
        row.addLayout(col, 1)
        return banner

    def _footer(self):
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
        for b in (self.back_btn, self.next_btn):
            f.addWidget(b)
        f.addSpacing(10)
        f.addWidget(self.cancel_btn)
        return footer

    # pages --------------------------------------------------------------
    def _page_welcome(self):
        page = SidePage("Welcome")
        b = page.body
        b.addWidget(label("Welcome to your new Linux PC", "BigTitle"))
        b.addSpacing(10)
        b.addWidget(label("Landfall will take the bundle you made on Windows and:"))
        for line in ("1.  Put your documents, pictures and other files in the right folders",
                     "2.  Install the Linux versions of your apps",
                     "3.  Give you a short list of anything left to do"):
            b.addWidget(label(line))
        b.addSpacing(10)
        b.addWidget(label("Plug in the USB drive with your bundle now, if you haven't yet.",
                          "Good"))
        b.addStretch(1)
        b.addWidget(label("Click Next to continue.", "Muted"))
        return page

    def _page_find(self):
        page = HeaderPage("Find your bundle", "Pick the bundle you made on your Windows PC.")
        b = page.body
        self.find_status = label("")
        b.addWidget(self.find_status)
        self.bundle_list = QListWidget()
        self.bundle_list.currentRowChanged.connect(lambda _: self.update_buttons())
        b.addWidget(self.bundle_list, 1)
        row = QHBoxLayout()
        again = QPushButton("Look again")
        again.clicked.connect(self.refresh_bundles)
        browse = QPushButton("Look somewhere else...")
        browse.clicked.connect(self.browse_bundle)
        row.addWidget(again)
        row.addWidget(browse)
        row.addStretch(1)
        b.addLayout(row)
        return page

    def _page_password(self):
        page = HeaderPage("Unlock your bundle", "Type the password you chose on Windows.")
        b = page.body
        grid = QGridLayout()
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw.textChanged.connect(lambda _: self.update_buttons())
        self.pw.returnPressed.connect(self.on_next)
        grid.addWidget(QLabel("Password:"), 0, 0)
        grid.addWidget(self.pw, 0, 1)
        show = QCheckBox("Show password")
        show.toggled.connect(lambda on: self.pw.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        grid.addWidget(show, 1, 1)
        b.addLayout(grid)
        self.pw_status = label("")
        b.addWidget(self.pw_status)
        b.addStretch(1)
        return page

    def _page_what(self):
        page = HeaderPage("Choose what to bring in",
                          "Tick the folders to unpack. Nothing already here gets replaced.")
        b = page.body
        self.what_grid = QGridLayout()
        self.what_grid.setColumnStretch(2, 1)
        b.addLayout(self.what_grid)
        b.addSpacing(10)
        self.what_info = label("", "Muted")
        b.addWidget(self.what_info)
        b.addStretch(1)
        self.what_total = label("")
        b.addWidget(self.what_total)
        return page

    def _page_apps(self):
        page = HeaderPage("Install your apps",
                          "These are the Linux versions of the apps you used on Windows.")
        b = page.body
        self.apps_note = label("", "Muted")
        b.addWidget(self.apps_note)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        self.apps_box = QVBoxLayout(holder)
        self.apps_box.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(holder)
        b.addWidget(scroll, 1)
        return page

    def _page_working(self):
        page = HeaderPage("Setting up your PC", "This can take a while. Keep the drive plugged in.")
        b = page.body
        b.addStretch(1)
        self.work_status = label("Starting...")
        b.addWidget(self.work_status)
        self.work_bar = QProgressBar()
        self.work_bar.setRange(0, 1000)
        b.addWidget(self.work_bar)
        self.work_detail = label("", "Muted")
        b.addWidget(self.work_detail)
        row = QHBoxLayout()
        row.addStretch(1)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_work)
        row.addWidget(self.stop_btn)
        b.addLayout(row)
        b.addStretch(2)
        return page

    def _page_done(self):
        page = SidePage("You've landed!")
        b = page.body
        b.addWidget(label("Your new PC is ready", "BigTitle"))
        b.addSpacing(8)
        self.done_summary = label("")
        self.done_summary.setTextFormat(Qt.TextFormat.RichText)
        b.addWidget(self.done_summary)
        b.addSpacing(8)
        b.addWidget(label("<b>What's left to do</b>"))
        self.todo = label("")
        self.todo.setTextFormat(Qt.TextFormat.RichText)
        self.todo.setOpenExternalLinks(True)
        b.addWidget(self.todo)
        b.addStretch(1)
        row = QHBoxLayout()
        docs = QPushButton("Open my files")
        docs.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path.home()))))
        row.addWidget(docs)
        row.addStretch(1)
        b.addLayout(row)
        return page

    # navigation ---------------------------------------------------------
    def go(self, index):
        self.stack.setCurrentIndex(index)
        if index == self.FIND:
            self.refresh_bundles()
        if index == self.PASSWORD:
            self.pw.setFocus()
        self.update_buttons()

    def update_buttons(self):
        i = self.stack.currentIndex()
        self.back_btn.setEnabled(i not in (self.WELCOME, self.WORKING, self.DONE))
        self.cancel_btn.setEnabled(i != self.DONE)
        self.next_btn.setText({self.APPS: "Start", self.DONE: "Finish",
                               self.PASSWORD: "Unlock"}.get(i, "Next >"))
        ok = {
            self.WELCOME: True,
            self.FIND: 0 <= self.bundle_list.currentRow() < len(self.bundles),
            self.PASSWORD: bool(self.pw.text()) and not getattr(self, "_checking", False),
            self.WHAT: self._space_ok(),
            self.APPS: True,
            self.WORKING: False,
            self.DONE: True,
        }[i]
        self.next_btn.setEnabled(ok)

    def on_back(self):
        self.go(max(self.stack.currentIndex() - 1, 0))

    def on_next(self):
        i = self.stack.currentIndex()
        if not self.next_btn.isEnabled():
            return
        if i == self.FIND:
            self.bundle = self.bundles[self.bundle_list.currentRow()]
            self.go(self.PASSWORD)
        elif i == self.PASSWORD:
            self.check_password()
        elif i == self.APPS:
            self.go(self.WORKING)
            self.start_work()
        elif i == self.DONE:
            self.close()
        else:
            self.go(i + 1)

    def closeEvent(self, event):
        if self.stack.currentIndex() == self.WORKING:
            if QMessageBox.question(self, "Stop?", "Landfall is still working. Stop and close?") \
                    != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._cancel = True
        event.accept()

    # step: find --------------------------------------------------------
    def refresh_bundles(self, roots=None):
        self.bundles = find_bundles(roots) if roots else find_bundles()
        self.bundle_list.clear()
        for bundle in self.bundles:
            when = datetime.fromtimestamp(bundle.folder.stat().st_mtime)
            self.bundle_list.addItem(QListWidgetItem(
                f"{bundle.move_folder}     {human_size(bundle.size)}, made {when:%B %d, %Y}"))
        if self.bundles:
            self.bundle_list.setCurrentRow(0)
            set_role(self.find_status, "Good")
            self.find_status.setText(f"Found {len(self.bundles)} bundle(s).")
        else:
            set_role(self.find_status, "Warn")
            self.find_status.setText("No bundle found yet. Plug in your USB drive, wait a few "
                                     "seconds, then click Look again.")
        self.update_buttons()

    def browse_bundle(self):
        folder = QFileDialog.getExistingDirectory(self, "Where is your bundle?", str(Path.home()))
        if folder:
            self.refresh_bundles([Path(folder)])

    # step: password ----------------------------------------------------
    def check_password(self):
        self._checking = True
        self.update_buttons()
        set_role(self.pw_status, "Muted")
        self.pw_status.setText("Checking...")
        bundle, password = self.bundle, self.pw.text()
        start_task(self, lambda report: read_manifest(bundle, password),
                   self.password_ok, self.password_bad)

    def password_ok(self, manifest):
        self._checking = False
        self.manifest, self.password = manifest, self.pw.text()
        self.pw_status.setText("")
        self.fill_what()
        self.fill_apps()
        self.go(self.WHAT)

    def password_bad(self, err):
        self._checking = False
        set_role(self.pw_status, "Warn")
        if isinstance(err, WrongPassword):
            self.pw_status.setText("That password didn't unlock the bundle. Check Caps Lock "
                                   "and try again.")
        else:
            self.pw_status.setText(f"The bundle couldn't be opened: {err}")
        self.update_buttons()

    # step: what --------------------------------------------------------
    def fill_what(self):
        while self.what_grid.count():
            w = self.what_grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.folder_checks.clear()
        stats: dict[str, list[int]] = {}
        for f in self.manifest.get("files", []):
            top = f["path"].split("/", 1)[0]
            s = stats.setdefault(top, [0, 0])
            s[0] += 1
            s[1] += f["size"]
        for row, name in enumerate(self.manifest.get("folders", [])):
            files, size = stats.get(name, [0, 0])
            box = QCheckBox(name)
            box.setChecked(files > 0)
            box.setEnabled(files > 0)
            box.toggled.connect(lambda _: self.update_what())
            self.folder_checks[name] = box
            self.what_grid.addWidget(box, row, 0)
            self.what_grid.addWidget(label(f"{files:,} files, {human_size(size)}", "Muted",
                                           wrap=False), row, 1)
            dest = self.dests.get(name, Path.home() / name)
            self.what_grid.addWidget(label(f"\u2192  {dest}", "Muted", wrap=False), row, 2)
        made = self.manifest.get("created", "")[:10]
        self.what_info.setText(f"Bundle made on {made} by Landfall "
                               f"{self.manifest.get('landfall_version', '?')}. If a file with "
                               "the same name is already here, the new one is saved as "
                               "\u201cname (from Windows)\u201d.")
        self.update_what()

    def chosen_folders(self):
        return [n for n, b in self.folder_checks.items() if b.isChecked()]

    def chosen_bytes(self):
        chosen = set(self.chosen_folders())
        return sum(f["size"] for f in self.manifest.get("files", [])
                   if f["path"].split("/", 1)[0] in chosen)

    def _space_ok(self):
        if not self.manifest:
            return False
        import shutil as _sh
        return _sh.disk_usage(Path.home()).free > self.chosen_bytes() * 2 + 200 * 1024 * 1024

    def update_what(self):
        need = self.chosen_bytes()
        import shutil as _sh
        free = _sh.disk_usage(Path.home()).free
        if self._space_ok():
            set_role(self.what_total, "Good")
            self.what_total.setText(f"Bringing in {human_size(need)}. "
                                    f"{human_size(free)} free on this PC.")
        else:
            set_role(self.what_total, "Warn")
            self.what_total.setText(f"Not enough room: unpacking needs about "
                                    f"{human_size(need * 2)} while it works, and only "
                                    f"{human_size(free)} is free.")
        self.update_buttons()

    # step: apps --------------------------------------------------------
    def fill_apps(self):
        while self.apps_box.count():
            w = self.apps_box.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.app_checks.clear()
        self.link_apps = []
        choices = apps_mod.choices_from_manifest(self.manifest)
        installed = apps_mod.installed_flatpaks()
        installable = [c for c in choices if c.flatpak]
        self.link_apps = [c for c in choices if not c.flatpak]
        if not apps_mod.flatpak_available():
            self.apps_note.setText("First, Landfall will set up Flatpak, the app store most "
                                   "Linux PCs use. You'll be asked for your computer "
                                   "password once.")
        else:
            self.apps_note.setText("Apps are installed just for you, from Flathub.")
        if not installable and not self.link_apps:
            self.apps_box.addWidget(label("No matching apps were found in your bundle.",
                                          "Muted"))
        for c in installable:
            already = c.flatpak in installed
            text = f"{c.linux_name}     (for your {c.windows_name})"
            box = QCheckBox(text + ("   - already installed" if already else ""))
            box.setChecked(not already)
            box.setEnabled(not already)
            self.app_checks.append((box, c))
            self.apps_box.addWidget(box)
        if self.link_apps:
            self.apps_box.addSpacing(10)
            self.apps_box.addWidget(label("<b>Get these from their websites</b> "
                                          "(links will be on the last page)"))
            for c in self.link_apps:
                tag = "  [new, Oct 2026]" if c.new else ""
                self.apps_box.addWidget(label(f"\u2022  {c.linux_name}{tag}     "
                                              f"(for your {c.windows_name})", "Muted"))

    # step: working -----------------------------------------------------
    def start_work(self):
        self._cancel = False
        folders = self.chosen_folders()
        apps = [c for box, c in self.app_checks if box.isChecked() and box.isEnabled()]
        bundle, password, manifest, dests = self.bundle, self.password, self.manifest, self.dests

        def work(report):
            result = restore(bundle, password, folders, dests, manifest,
                             progress=lambda d, t, n: report(("files", d, t, n)),
                             cancelled=lambda: self._cancel)
            app_results = []
            if apps and not self._cancel:
                if not apps_mod.flatpak_available():
                    report(("note", "Setting up Flatpak (watch for the password pop-up)..."))
                    ok, msg = apps_mod.install_flatpak_tool()
                    if not ok:
                        return result, [(a.linux_name, False, msg) for a in apps]
                report(("note", "Connecting to Flathub..."))
                apps_mod.ensure_flathub()
                for n, a in enumerate(apps, 1):
                    if self._cancel:
                        break
                    report(("app", n, len(apps), a.linux_name))
                    ok, msg = apps_mod.install_app(a.flatpak)
                    app_results.append((a.linux_name, ok, msg))
            return result, app_results

        start_task(self, work, self.work_done, self.work_failed, self.work_progress)

    def work_progress(self, info):
        kind = info[0]
        if kind == "files":
            _, done, total, name = info
            self.work_status.setText(f"Unpacking your files: {human_size(done)} of "
                                     f"{human_size(total)}")
            self.work_bar.setValue(int(1000 * done / total) if total else 1000)
            self.work_detail.setText(name)
        elif kind == "note":
            self.work_status.setText(info[1])
            self.work_bar.setRange(0, 0)  # busy animation
            self.work_detail.setText("")
        elif kind == "app":
            _, n, total, name = info
            self.work_bar.setRange(0, total)
            self.work_bar.setValue(n - 1)
            self.work_status.setText(f"Installing app {n} of {total}: {name}")
            self.work_detail.setText("Downloading from Flathub. Bigger apps take a few minutes.")

    def stop_work(self):
        self._cancel = True
        self.stop_btn.setEnabled(False)
        self.work_status.setText("Stopping...")

    def work_done(self, result):
        self.restore_result, self.app_results = result
        r = self.restore_result
        lines = [f"<b>{r.restored:,}</b> file(s) unpacked into your folders."]
        if r.already_there:
            lines.append(f"{r.already_there:,} were already here, so they were left alone.")
        if r.renamed:
            lines.append(f"{len(r.renamed):,} were saved as \u201c(from Windows)\u201d copies "
                         "because a different file had the same name.")
        good = [n for n, ok, _ in self.app_results if ok]
        if good:
            lines.append(f"<b>{len(good)}</b> app(s) installed: {', '.join(good)}. "
                         "Find them in your app menu.")
        self.done_summary.setText("<br>".join(lines))
        todo = []
        for name, ok, msg in self.app_results:
            if not ok:
                todo.append(f"\u2022 {name} didn't install. You can get it from your "
                            "Software app.")
        for c in self.link_apps:
            if c.url:
                tag = " (brand new, still young)" if c.new else ""
                todo.append(f"\u2022 Get <a href='{c.url}'>{c.linux_name}</a>{tag} for your "
                            f"{c.windows_name}.")
            else:
                todo.append(f"\u2022 For your {c.windows_name}: use {c.linux_name}.")
        if r.failed:
            todo.append(f"\u2022 {len(r.failed)} file(s) couldn't be unpacked.")
        todo.append("\u2022 Sign in to your browser to bring back bookmarks and passwords "
                    "(automatic moving for these is coming soon).")
        todo.append("\u2022 Keep the USB drive until you've checked everything arrived.")
        self.todo.setText("<br>".join(todo))
        self.go(self.DONE)

    def work_failed(self, err):
        self.stop_btn.setEnabled(True)
        self.work_bar.setRange(0, 1000)
        if isinstance(err, RestoreCancelled):
            self.go(self.APPS)
            return
        QMessageBox.warning(self, "Something went wrong",
                            f"Landfall stopped before finishing. Nothing already on this PC "
                            f"was replaced.\n\nDetails: {err}")
        self.go(self.APPS)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setWindowIcon(QIcon(str(ICON)))
    app.setDesktopFileName("landfall")
    window = Importer()
    window.show()
    return app.exec()
