"""Landfall on Linux: unpack the bundle made on Windows and set up the new PC."""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from landfall.linux import apps as apps_mod
from landfall.linux import browsers as browsers_mod
from landfall.linux import system_update
from landfall.linux.dirs import user_dirs
from landfall.linux.tips import QUICK_START, TIPS
from landfall.linux.restore import (RestoreCancelled, WrongPassword, extract_private,
                                    find_bundles, read_manifest, restore)
from landfall.scan.folders import human_size
from landfall.sysenv import open_path
from landfall.ui import (ICONS, ChoiceRow, StageList, StepDialog, TipCard, logo_for, HeroPage, Page, Shell, card, folder_icon, label,
                         make_app, picture, run_window, set_role, start_task,
                         text_field, plural)

STEPS = ["Welcome", "Update your PC", "Find your bundle", "Unlock it", "Review", "Setting up",
         "All done"]


class Importer(Shell):
    WELCOME, UPDATE, FIND, PASSWORD, WHAT, WORKING, DONE = range(7)

    def __init__(self):
        super().__init__(STEPS, "Welcome to Linux")
        self.setWindowTitle("PenguinPort \u2014 Move to Linux")
        self.bundles, self.bundle, self.manifest, self.password = [], None, None, ""
        self.dests = user_dirs()
        self.folder_rows: dict[str, ChoiceRow] = {}
        self.to_install: list[apps_mod.AppChoice] = []
        self.link_apps: list[apps_mod.AppChoice] = []
        self.present_apps: list[apps_mod.AppChoice] = []
        self._cancel = False
        self._checking = False
        self.restore_result = None
        self.app_results: list[tuple[str, bool, str]] = []
        self.browser_results: list = []
        self.back_btn.clicked.connect(self.on_back)
        self.next_btn.clicked.connect(self.on_next)
        self.update_state = "ready"          # ready / running / done / failed / skipped
        self.update_plan = system_update.detect()
        self.restart_later = False
        for build in (self._page_welcome, self._page_update, self._page_find, self._page_password,
                      self._page_what, self._page_working, self._page_done):
            self.stack.addWidget(build())
        self.go(self.WELCOME)

    # --- pages ------------------------------------------------------------
    def _page_welcome(self):
        page = HeroPage("Welcome to your new PC", "Let's bring your things over from Windows.")
        frame, box = card()
        box.addWidget(label("PenguinPort will", "Section"))
        for icon, title, text in (
                ("Documents", "Unpack your files", "Documents, pictures and more go into the "
                                                   "matching folders."),
                ("Apps", "Install your apps", "The Linux apps you picked on Windows, "
                                              "installed for you."),
                ("Soon", "Show what's left", "A short to-do list at the end.")):
            row = QHBoxLayout()
            row.addWidget(picture(ICONS / f"{icon}.svg", 30))
            row.addSpacing(10)
            col = QVBoxLayout()
            col.setSpacing(0)
            col.addWidget(label(f"<b>{title}</b>"))
            col.addWidget(label(text, "Muted"))
            row.addLayout(col, 1)
            box.addLayout(row)
        page.body.addWidget(frame)
        page.body.addSpacing(6)
        page.body.addWidget(label("Plug in the USB drive with your PenguinPort Move folder now, "
                                  "if you haven't yet.", "Good"))
        page.body.addStretch(1)
        return page

    def _page_update(self):
        page = Page("Let's update your PC first",
                    "New Linux PCs usually have updates waiting. PenguinPort installs them for you, "
                    "no typing commands. It asks for your password once.")
        frame, box = card()
        head = QHBoxLayout()
        head.addWidget(picture(ICONS / "hardware.svg", 40))
        head.addSpacing(8)
        words = QVBoxLayout()
        words.setSpacing(2)
        name = self.update_plan.label if self.update_plan else "your Linux"
        words.addWidget(label(f"Update {name}", "Section"))
        self.update_status = label("This usually takes 5 to 20 minutes. You can keep the "
                                   "window open and watch, or step away.", "Muted")
        words.addWidget(self.update_status)
        head.addLayout(words, 1)
        box.addLayout(head)
        self.update_stages = StageList(["Checking for updates", "Installing updates",
                                        "Updating your apps", "All up to date"])
        box.addWidget(self.update_stages)
        self.update_bar = QProgressBar()
        self.update_bar.setRange(0, 1000)
        self.update_bar.setValue(0)
        box.addWidget(self.update_bar)
        self.update_item = label("", "Muted", wrap=False)
        box.addWidget(self.update_item)
        row = QHBoxLayout()
        row.addStretch(1)
        self.skip_update_btn = QPushButton("Skip for now")
        self.skip_update_btn.clicked.connect(self.skip_update)
        row.addWidget(self.skip_update_btn)
        box.addLayout(row)
        page.body.addWidget(frame)
        page.body.addWidget(TipCard(TIPS))
        page.body.addStretch(1)
        if not self.update_plan:
            self.update_state = "skipped"
            self.update_status.setText("PenguinPort couldn't tell how this Linux installs updates, "
                                       "so this step is skipped. Use your Software app later.")
        return page

    def start_update(self):
        self.update_state = "running"
        self.update_stages.set_stage(0)
        self.update_bar.setRange(0, 0)
        self.skip_update_btn.setEnabled(False)
        set_role(self.update_status, "Muted")
        self.update_status.setText("A password window will pop up. Type the password you "
                                   "use to sign in to this PC.")
        self.update_buttons()
        plan = self.update_plan
        start_task(self, lambda report: system_update.run_update(plan, report),
                   self.update_finished, self.update_crashed, self.update_progress)

    def update_progress(self, ev):
        kind = ev[0]
        if kind == "stage":
            idx = {"check": 0, "install": 1, "apps": 2, "done": 3}.get(ev[1], 0)
            self.update_stages.set_stage(idx)
            if ev[1] == "check":
                self.update_status.setText("Checking which updates are available...")
            elif ev[1] == "apps":
                self.update_bar.setRange(0, 0)
                self.update_status.setText("Updating your apps from the app store...")
                self.update_item.setText("")
        elif kind == "progress":
            done, total = ev[1], ev[2]
            if total:
                self.update_bar.setRange(0, total)
                self.update_bar.setValue(done)
                self.update_status.setText(f"Installing updates  \u00b7  {int(100 * done / total)}%")
            if len(ev) > 3:
                self.update_item.setText(ev[3])
        elif kind == "item":
            self.update_item.setText(ev[1])

    def update_finished(self, result):
        ok, msg = result
        self.update_bar.setRange(0, 1000)
        self.skip_update_btn.setEnabled(True)
        if ok:
            self.update_state = "done"
            self.update_stages.set_stage(4)
            self.update_bar.setValue(1000)
            self.update_item.setText("")
            self.restart_later = system_update.restart_needed()
            set_role(self.update_status, "Good")
            self.update_status.setText("\u2714  Your PC is up to date."
                                       + ("  A restart finishes a few updates; PenguinPort will "
                                          "remind you at the end." if self.restart_later else ""))
            self.skip_update_btn.hide()
        else:
            self.update_state = "failed"
            set_role(self.update_status, "Warn")
            self.update_status.setText(f"The update didn't finish: {msg}  You can try again, "
                                       "or skip it and update later from the Software app.")
            self.skip_update_btn.setText("Skip for now")
        self.update_buttons()

    def update_crashed(self, err):
        self.update_finished((False, str(err)))

    def skip_update(self):
        self.update_state = "skipped"
        self.go(self.FIND)

    def _page_find(self):
        page = Page("Find your bundle", "Pick the one you made on your Windows PC.")
        self.find_status = label("", "Section")
        page.body.addWidget(self.find_status)
        self.bundle_list = QListWidget()
        self.bundle_list.currentRowChanged.connect(lambda _: self.update_buttons())
        page.body.addWidget(self.bundle_list, 1)
        row = QHBoxLayout()
        again = QPushButton("Look again")
        again.clicked.connect(lambda: self.refresh_bundles())
        browse = QPushButton("Look somewhere else...")
        browse.clicked.connect(self.browse_bundle)
        row.addWidget(again)
        row.addWidget(browse)
        row.addStretch(1)
        page.body.addLayout(row)
        return page

    def _page_password(self):
        page = Page("Unlock your bundle", "Type the password you chose on your Windows PC.")
        frame, box = card()
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self.pw = text_field("Your bundle password", password=True)
        self.pw.textChanged.connect(lambda _: self.update_buttons())
        self.pw.returnPressed.connect(self.on_next)
        grid.addWidget(QLabel("Password"), 0, 0)
        grid.addWidget(self.pw, 0, 1)
        show = QCheckBox("Show password")
        show.toggled.connect(lambda on: self.pw.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        grid.addWidget(show, 1, 1)
        box.addLayout(grid)
        self.pw_status = label("")
        box.addWidget(self.pw_status)
        page.body.addWidget(frame)
        page.body.addStretch(1)
        return page

    def _scroll_box(self, page):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        holder.setObjectName("Content")
        box = QVBoxLayout(holder)
        box.setContentsMargins(0, 0, 6, 0)
        box.setSpacing(8)
        box.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(holder)
        page.body.addWidget(scroll, 1)
        return box

    def _page_what(self):
        page = Page("Review and start",
                    "Here's everything PenguinPort will set up. Click Start and it does the rest.")
        self.what_box = self._scroll_box(page)
        self.what_total = label("", "Section")
        page.body.addWidget(self.what_total)
        return page

    def _page_working(self):
        page = Page("Setting up your PC", "Keep the drive plugged in. This can take a while.")
        frame, box = card()
        self.work_status = label("Starting...", "Section")
        box.addWidget(self.work_status)
        self.work_bar = QProgressBar()
        self.work_bar.setRange(0, 1000)
        box.addWidget(self.work_bar)
        self.work_detail = label("", "Muted")
        box.addWidget(self.work_detail)
        row = QHBoxLayout()
        row.addStretch(1)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_work)
        row.addWidget(self.stop_btn)
        box.addLayout(row)
        page.body.addWidget(frame)
        page.body.addWidget(TipCard(TIPS[3:] + TIPS[:3]))   # start with different tips
        page.body.addStretch(1)
        return page

    def _page_done(self):
        page = HeroPage("You've landed!", "Your new PC is ready.")
        frame, box = card()
        self.done_summary = label("")
        self.done_summary.setTextFormat(Qt.TextFormat.RichText)
        box.addWidget(self.done_summary)
        retry_row = QHBoxLayout()
        self.retry_btn = QPushButton("Try again")
        self.retry_btn.setObjectName("Primary")
        self.retry_btn.clicked.connect(self.retry_failed)
        self.retry_btn.hide()
        retry_row.addWidget(self.retry_btn)
        retry_row.addStretch(1)
        box.addLayout(retry_row)
        page.body.addWidget(frame)
        frame2, box2 = card()
        box2.addWidget(label("What's left to do", "Section"))
        self.todo = label("")
        self.todo.setTextFormat(Qt.TextFormat.RichText)
        self.todo.linkActivated.connect(open_path)
        box2.addWidget(self.todo)
        page.body.addWidget(frame2)
        self.browser_card, self.browser_box = card()
        self.browser_card.hide()
        page.body.addWidget(self.browser_card)
        frame3, box3 = card()
        box3.addWidget(label("Your Linux quick start", "Section"))
        for n, tip in enumerate(QUICK_START, 1):
            box3.addWidget(label(f"<b>{n}.</b>&nbsp;&nbsp;{tip}"))
        page.body.addWidget(frame3)
        row = QHBoxLayout()
        files = QPushButton("Open my files")
        files.clicked.connect(lambda: open_path(str(Path.home())))
        row.addWidget(files)
        row.addStretch(1)
        page.body.addLayout(row)
        page.body.addStretch(1)
        return page

    # --- navigation -------------------------------------------------------
    def go(self, index):
        self.stack.setCurrentIndex(index)
        self.set_step(index)
        if index == self.FIND:
            self.refresh_bundles()
        if index == self.PASSWORD:
            self.pw.setFocus()
        self.update_buttons()

    def update_buttons(self):
        i = self.stack.currentIndex()
        self.back_btn.setVisible(i not in (self.WELCOME, self.DONE))
        self.back_btn.setEnabled(i != self.WORKING
                                 and not (i == self.UPDATE and self.update_state == "running"))
        self.cancel_btn.setVisible(i != self.DONE)
        update_label = {"ready": "Update now", "failed": "Try again"}.get(self.update_state,
                                                                           "Next")
        self.next_btn.setText({self.WELCOME: "Get started", self.UPDATE: update_label,
                               self.PASSWORD: "Unlock", self.WHAT: "Start",
                               self.DONE: "Finish"}.get(i, "Next"))
        self.next_btn.setEnabled({
            self.WELCOME: True,
            self.UPDATE: self.update_state != "running",
            self.FIND: 0 <= self.bundle_list.currentRow() < len(self.bundles),
            self.PASSWORD: bool(self.pw.text()) and not self._checking,
            self.WHAT: self._space_ok(), self.WORKING: False,
            self.DONE: True}[i])

    def on_back(self):
        self.go(max(self.stack.currentIndex() - 1, 0))

    def on_next(self):
        i = self.stack.currentIndex()
        if not self.next_btn.isEnabled():
            return
        if i == self.UPDATE:
            if self.update_state in ("ready", "failed"):
                self.start_update()
            else:
                self.go(self.FIND)
        elif i == self.FIND:
            self.bundle = self.bundles[self.bundle_list.currentRow()]
            self.go(self.PASSWORD)
        elif i == self.PASSWORD:
            self.check_password()
        elif i == self.WHAT:
            self.go(self.WORKING)
            self.start_work()
        elif i == self.DONE:
            self.close()
        else:
            self.go(i + 1)

    def closeEvent(self, event):
        if self.stack.currentIndex() == self.UPDATE and self.update_state == "running":
            QMessageBox.information(self, "Updating", "Please wait for the update to finish. "
                                    "Stopping in the middle can leave things half-installed.")
            event.ignore()
            return
        if self.stack.currentIndex() == self.WORKING:
            if QMessageBox.question(self, "Stop?", "PenguinPort is still working. Stop and close?") \
                    != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._cancel = True
        event.accept()

    # --- step: find -------------------------------------------------------
    def refresh_bundles(self, roots=None):
        self.bundles = find_bundles(roots) if roots else find_bundles()
        self.bundle_list.clear()
        for bundle in self.bundles:
            when = datetime.fromtimestamp(bundle.folder.stat().st_mtime)
            self.bundle_list.addItem(QListWidgetItem(
                f"{bundle.move_folder}\n{human_size(bundle.size)}  \u00b7  made "
                f"{when:%B %d, %Y}"))
        if self.bundles:
            self.bundle_list.setCurrentRow(0)
            set_role(self.find_status, "Good")
            self.find_status.setText(f"\u2714  Found {len(self.bundles)} bundle"
                                     f"{'s' if len(self.bundles) > 1 else ''}.")
        else:
            set_role(self.find_status, "Warn")
            self.find_status.setText("No bundle found yet. Plug in your USB drive, wait a few "
                                     "seconds, then click Look again.")
        self.update_buttons()

    def browse_bundle(self):
        folder = QFileDialog.getExistingDirectory(self, "Where is your PenguinPort Move folder?",
                                                  str(Path.home()))
        if folder:
            self.refresh_bundles([Path(folder)])

    # --- step: password ---------------------------------------------------
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
        self.go(self.WHAT)

    def password_bad(self, err):
        self._checking = False
        set_role(self.pw_status, "Warn")
        self.pw_status.setText("That password didn't unlock the bundle. Check Caps Lock and "
                               "try again." if isinstance(err, WrongPassword)
                               else f"The bundle couldn't be opened: {err}")
        self.update_buttons()

    # --- step: what -------------------------------------------------------
    @staticmethod
    def _clear(box):
        while box.count():
            item = box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def fill_what(self):
        self._clear(self.what_box)
        self.folder_rows.clear()
        self.what_box.addWidget(label("Your files", "Section"))
        stats: dict[str, list[int]] = {}
        for f in self.manifest.get("files", []):
            s = stats.setdefault(f["path"].split("/", 1)[0], [0, 0])
            s[0] += 1
            s[1] += f["size"]
        for name in self.manifest.get("folders", []):
            files, size = stats.get(name, [0, 0])
            dest = self.dest_for(name)
            detail = (f"{plural(files, 'file')}  \u00b7  {human_size(size)}  \u2192  {dest}" if files
                      else f"Empty folder  \u2192  {dest}")
            row = ChoiceRow(folder_icon(name), name, detail, True, True)
            row.box.toggled.connect(lambda _: self.update_what())
            self.folder_rows[name] = row
            self.what_box.addWidget(row)
        self.what_box.addWidget(label(
            "If a file with the same name is already here, the one from Windows is saved as "
            "\u201cname (from Windows)\u201d. Nothing gets replaced.", "Muted"))
        self.fill_apps()
        self.update_what()

    def dest_for(self, name: str) -> Path:
        """Standard folders go to their Linux twins (Documents -> ~/Documents). Anything the
        user added on Windows goes into ~/From Windows/<name>, so nothing gets mixed up."""
        extras = set(self.manifest.get("extra_folders", [])) if self.manifest else set()
        if name in self.dests and name not in extras:
            return self.dests[name]
        return Path.home() / "From Windows" / name

    def chosen_folders(self):
        return [n for n, r in self.folder_rows.items() if r.box.isChecked()]

    def chosen_bytes(self):
        chosen = set(self.chosen_folders())
        return sum(f["size"] for f in self.manifest.get("files", [])
                   if f["path"].split("/", 1)[0] in chosen)

    def _space_ok(self):
        if not self.manifest:
            return False
        return shutil.disk_usage(Path.home()).free > self.chosen_bytes() * 2 + 200 * 1024 ** 2

    def update_what(self):
        need, free = self.chosen_bytes(), shutil.disk_usage(Path.home()).free
        if self._space_ok():
            set_role(self.what_total, "Section")
            self.what_total.setText(f"Bringing in {human_size(need)}  \u00b7  "
                                    f"{human_size(free)} free on this PC")
        else:
            set_role(self.what_total, "Warn")
            self.what_total.setText(f"Not enough room: unpacking needs about "
                                    f"{human_size(need * 2)} while it works, and only "
                                    f"{human_size(free)} is free.")
        self.update_buttons()

    # --- step: apps -------------------------------------------------------
    def fill_apps(self):
        choices = apps_mod.choices_from_manifest(self.manifest)
        flatpaks, snaps = apps_mod.installed_flatpaks(), apps_mod.installed_snaps()
        self.to_install, self.present_apps, self.link_apps = [], [], []
        for c in choices:
            if c.included or (c.flatpak and apps_mod.already_present(c, flatpaks, snaps)):
                self.present_apps.append(c)
            elif c.flatpak:
                self.to_install.append(c)
            else:
                self.link_apps.append(c)
        self.what_box.addSpacing(8)
        self.what_box.addWidget(label("Your apps", "Section"))
        if not choices:
            self.what_box.addWidget(label("No apps were picked on Windows.", "Muted"))
        rows = ([(c, "Will be installed for you", "Pill") for c in self.to_install]
                + [(c, "Already on this PC", "Good") for c in self.present_apps]
                + [(c, "Link at the end", "Muted") for c in self.link_apps])
        for c, status, role in rows:
            detail = f"For your {c.windows_name}" + (f"  \u00b7  {c.about}" if c.about else "")
            row = ChoiceRow(logo_for({"flatpak": c.flatpak}), c.linux_name, detail, False, False)
            row.box.hide()
            row.title.setStyleSheet("")
            row.detail.setWordWrap(True)
            row.side.addWidget(label(status, role, wrap=False))
            if c.new:
                row.side.addWidget(label("New", "PillNew", wrap=False))
            self.what_box.addWidget(row)
        recs = self.manifest.get("browsers", [])
        if recs:
            self.what_box.addSpacing(8)
            self.what_box.addWidget(label("Your browsers", "Section"))
            picked = [c.linux_name for c in self.to_install + self.present_apps
                      if c.flatpak in browsers_mod.FLATPAK_TO_BROWSER]
            for r in recs:
                into = self._planned_target(r, picked)
                bits = [plural(r["bookmarks"], "bookmark")]
                if r["family"] == "firefox" and into == "Firefox":
                    bits.append("history")
                    if r["passwords"]:
                        bits.append(plural(r["passwords"], "password"))
                elif r.get("password_csv") or r.get("passwords"):
                    bits.append("passwords (one click at the end)")
                row = ChoiceRow(logo_for({"flatpak": {"firefox": "org.mozilla.firefox",
                                                      "chrome": "com.google.Chrome",
                                                      "brave": "com.brave.Browser"}
                                          .get(r["browser"], "")}),
                                f"{r['name']}  \u2192  {into}", "  \u00b7  ".join(bits),
                                False, False)
                row.box.hide()
                row.title.setStyleSheet("")
                self.what_box.addWidget(row)
        if self.to_install and not apps_mod.flatpak_available():
            self.what_box.addWidget(label(
                "PenguinPort will first set up Flatpak, the app store most Linux PCs use. "
                "You'll be asked for your computer password once.", "Muted"))

    @staticmethod
    def _planned_target(rec, picked_names):
        if rec["family"] == "firefox" and "Firefox" in picked_names:
            return "Firefox"
        chromium = [n for n in picked_names if n != "Firefox"]
        if rec["family"] == "chromium" and chromium:
            return chromium[0]
        return picked_names[0] if picked_names else "Firefox"

    # --- step: working ----------------------------------------------------
    def start_work(self):
        self._cancel = False
        self.stop_btn.setEnabled(True)
        folders = self.chosen_folders()
        apps = list(self.to_install)
        bundle, password, manifest = self.bundle, self.password, self.manifest
        dests = {name: self.dest_for(name) for name in manifest.get("folders", [])}

        def work(report):
            result = restore(bundle, password, folders, dests, manifest,
                             progress=lambda d, t, n: report(("files", d, t, n)),
                             cancelled=lambda: self._cancel)
            app_results = []
            if apps and not self._cancel:
                if not apps_mod.flatpak_available():
                    report(("note", "Setting up Flatpak. Watch for the password pop-up..."))
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
                apps_mod.make_visible()   # show them in the app menu now, no logging out
            browser_results = []
            if manifest.get("browsers") and not self._cancel:
                report(("note", "Moving your bookmarks and passwords..."))
                browser_results = self._import_browsers(bundle, password, manifest, apps)
            self.browser_results = browser_results
            return result, app_results

        start_task(self, work, self.work_done, self.work_failed, self.work_progress)

    def _import_browsers(self, bundle, password, manifest, apps):
        import shutil as _sh
        import tempfile
        home = Path.home()
        tmp = Path(tempfile.mkdtemp(prefix=".landfall-browsers-", dir=home))
        results = []
        try:
            extract_private(bundle, password, "landfall/browsers/", tmp)
            flatpaks, snaps = apps_mod.installed_flatpaks(), apps_mod.installed_snaps()
            picked = [c.flatpak for c in apps_mod.choices_from_manifest(manifest) if c.flatpak]
            targets = browsers_mod.choose_targets(picked, home, flatpaks, snaps)
            for rec in manifest["browsers"]:
                target = browsers_mod.match_target(rec["family"], rec["browser"], targets)
                if target is None:
                    results.append(browsers_mod.BrowserResult(
                        rec["name"], "", problem="No browser was found on this PC to put "
                                                 "them in. Install one, then run PenguinPort again."))
                    continue
                try:
                    results.append(browsers_mod.import_browser(
                        rec, tmp / "landfall" / "browsers" / rec["key"], target, home))
                except Exception as err:  # noqa: BLE001 - shown to the user
                    results.append(browsers_mod.BrowserResult(rec["name"], target.name,
                                                              problem=str(err)))
        finally:
            _sh.rmtree(tmp, ignore_errors=True)
        return results

    def work_progress(self, info):
        kind = info[0]
        if kind == "files":
            _, done, total, name = info
            self.work_bar.setRange(0, 1000)
            self.work_bar.setValue(int(1000 * done / total) if total else 1000)
            pct = int(100 * done / total) if total else 100
            self.work_status.setText(f"Unpacking your files  \u00b7  {pct}%")
            self.work_detail.setText(name)
        elif kind == "note":
            self.work_status.setText(info[1])
            self.work_bar.setRange(0, 0)
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
        self.show_done()
        self.go(self.DONE)

    def show_done(self):
        r = self.restore_result
        lines = [f"<b>{plural(r.restored, 'file')}</b> unpacked into your folders."]
        if r.already_there:
            lines.append(f"{plural(r.already_there, 'file')} already here, so left alone.")
        if r.renamed:
            lines.append(f"{len(r.renamed):,} saved as \u201c(from Windows)\u201d copies "
                         "because a different file had the same name.")
        good = [n for n, ok, _ in self.app_results if ok]
        bad = [(n, msg) for n, ok, msg in self.app_results if not ok]
        if good:
            lines.append(f"<b>{plural(len(good), 'app')}</b> installed: {', '.join(good)}. "
                         "Find them in your app menu: press the Windows key and type the name.")
        if self.present_apps:
            lines.append("Already on this PC: "
                         + ", ".join(c.linux_name for c in self.present_apps) + ".")
        for name, msg in bad:
            lines.append(f"<span style='color:#B4410E'><b>{name}</b> didn't install: "
                         f"{msg}</span>")
        self.done_summary.setText("<br>".join(lines))
        self.retry_btn.setVisible(bool(bad))
        todo = []
        for c in self.link_apps:
            if c.url:
                tag = " (brand new, still young)" if c.new else ""
                todo.append(f"\u2022 Get <a href='{c.url}'>{c.linux_name}</a>{tag} for your "
                            f"{c.windows_name}.")
        if r.failed:
            todo.append(f"\u2022 {len(r.failed)} file(s) couldn't be unpacked.")
        todo.append("\u2022 Sign in to your browser to bring back bookmarks and passwords "
                    "(automatic moving for these is coming soon).")
        todo.append("\u2022 Keep the USB drive until you've checked everything arrived.")
        if self.restart_later:
            todo.insert(0, "\u2022 <b>Restart your PC</b> when you're ready, to finish "
                           "installing updates.")
        elif self.update_state == "skipped":
            todo.insert(0, "\u2022 Install updates when you have a moment: open the "
                           "Software app and click Updates.")
        self.todo.setText("<br>".join(todo))
        self.show_browser_results()

    def show_browser_results(self):
        while self.browser_box.count():
            item = self.browser_box.takeAt(0)
            w = item.widget() if item else None
            if w:
                w.deleteLater()
            elif item and item.layout():
                lay = item.layout()
                while lay.count():
                    x = lay.takeAt(0).widget()
                    if x:
                        x.deleteLater()
        if not self.browser_results:
            self.browser_card.hide()
            return
        self.browser_card.show()
        self.browser_box.addWidget(label("Your browsers", "Section"))
        for r in self.browser_results:
            if r.problem:
                self.browser_box.addWidget(label(
                    f"<span style='color:#B4410E'><b>{r.source}:</b> {r.problem}</span>"))
                continue
            got = [plural(r.bookmarks, "bookmark")]
            if r.history:
                got.append("history")
            if r.passwords == "copied":
                got.append("saved passwords")
            self.browser_box.addWidget(label(f"\u2714 <b>{r.source} \u2192 {r.target}:</b> "
                                             f"{', '.join(got)} moved in."))
            if r.passwords == "file":
                row = QHBoxLayout()
                row.addWidget(label(f"Passwords from {r.source}: one short step left.", "Muted"), 1)
                imp = QPushButton(f"Finish {r.source} passwords")
                imp.setObjectName("Primary")
                imp.clicked.connect(lambda _=False, res=r: self.import_passwords(res))
                row.addWidget(imp)
                self.browser_box.addLayout(row)

    def import_passwords(self, res):
        if res.target == "Firefox":
            find_it = "click the \u22ef menu (top right), then <b>Import from a File</b>"
        else:
            find_it = "scroll to <b>Import passwords</b> and click <b>Select file</b>"

        def open_browser():
            browsers_mod.open_import_page(res)
            return None

        def delete_file():
            if res.password_file:
                res.password_file.unlink(missing_ok=True)
            res.passwords = ""
            return "advance"

        steps = [
            {"title": f"Bring your passwords into {res.target}",
             "body": f"Your {res.source} passwords came across. The last step is to load them "
                     f"into {res.target}. PenguinPort opens the right page and tells you exactly "
                     "what to click."},
            {"title": f"Close {res.target} windows first",
             "body": f"If you have any <b>{res.target}</b> windows open, close them now.<br><br>"
                     f"That way the next step can open {res.target} straight to the right page."
                     "<br><br>Then click <b>Next</b>."},
            {"title": f"Open {res.target}'s password page",
             "body": f"Click the green button below to open {res.target} on its passwords page."
                     f"<br><br>There, {find_it}. When it asks for a file, choose this one:<br>"
                     f"<code>{res.password_file}</code><br><br><b>If it opens somewhere else</b>, "
                     "click the address bar, type this and press Enter:<br>"
                     f"<code>{res.import_url}</code><br><br>Your passwords appear in "
                     f"{res.target}. Then come back here and click <b>Next</b>.",
             "action": (f"Open {res.target}", open_browser)},
            {"title": "Tidy up",
             "body": "All done. For safety, PenguinPort will now delete the leftover passwords "
                     "file, since it holds your passwords in plain text. Your passwords stay "
                     f"safely inside {res.target}.",
             "action": ("Delete the leftover file", delete_file)},
        ]
        result = StepDialog(f"Passwords \u2192 {res.target}", steps, self,
                            accent_last="Finish").run()
        if result in ("done", "skip"):
            self.show_browser_results()

    def retry_failed(self):
        failed = {n for n, ok, _ in self.app_results if not ok}
        apps = [c for c in self.to_install if c.linux_name in failed]
        self.retry_btn.setEnabled(False)
        self.retry_btn.setText("Installing...")

        def work(report):
            apps_mod.ensure_flathub()
            return [(a.linux_name, *apps_mod.install_app(a.flatpak)) for a in apps]

        def finished(results):
            apps_mod.make_visible()
            by_name = {n: (n, ok, msg) for n, ok, msg in results}
            self.app_results = [by_name.get(n, (n, ok, msg)) for n, ok, msg in self.app_results]
            self.retry_btn.setEnabled(True)
            self.retry_btn.setText("Try again")
            self.show_done()

        start_task(self, work, finished, self.task_failed)

    def task_failed(self, err):
        QMessageBox.warning(self, "Something went wrong", f"PenguinPort hit a problem:\n{err}")

    def work_failed(self, err):
        self.stop_btn.setEnabled(True)
        self.work_bar.setRange(0, 1000)
        if not isinstance(err, RestoreCancelled):
            QMessageBox.warning(self, "Something went wrong",
                                "PenguinPort stopped before finishing. Nothing already on this PC "
                                f"was replaced.\n\nDetails: {err}")
        self.go(self.WHAT)


def main() -> int:
    app = make_app()
    return run_window(app, Importer())
