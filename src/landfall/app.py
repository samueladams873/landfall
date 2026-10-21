"""Landfall on Windows: the moving wizard that packs everything up."""
from __future__ import annotations

import os
import sys
import time
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QProgressBar, QPushButton, QScrollArea, QStackedWidget, QTabWidget,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from landfall.drives import list_drives
from landfall.mapping import (GROUP_ALT, GROUP_SAME, GROUPS, builtin_apps, by_category,
                              match_all)
from landfall.pack import PackCancelled, browser_folders, browser_records, pack, space_needed
from landfall.scan.browsers import find_browsers, open_password_export
from landfall.report import build_html, option_text
from landfall.scan.apps import scan_apps
from landfall.scan.folders import extra_files, extra_folder, find_folders, human_size, measure
from landfall.scan.hardware import hardware_notes, scan_hardware
from landfall.ui import (ICON, ICONS, CategoryCard, ChoiceRow, FolderPicker, ScoreRing, StepDialog,
                         logo_for,
                         StageList,
                         WidthWatcher, HeroPage, Page, Shell, card, folder_icon,
                         label, logo, make_app, picture, run_window, set_role,
                         start_task, text_field, fit_list, plural)

__all__ = ["ICON", "Wizard", "build_window", "main", "label", "logo", "set_role", "start_task"]

COMING_SOON = [
    "Email and contacts",
    "Wi-Fi networks and passwords",
    "Wallpaper and fonts",
    "Game saves",
    "Product keys and licenses list",
]
STEPS = ["Welcome", "Check this PC", "Pick your apps", "Pick your files", "Where to save",
         "Packing", "All done"]


class Wizard(Shell):
    WELCOME, CHECK, PICK, WHAT, WHERE, PACKING, DONE = range(7)

    def __init__(self):
        super().__init__(STEPS, "Moving Wizard")
        self.setWindowTitle("PenguinPort \u2014 Move to Linux")
        self.grouped = self.hw = None
        self.folders = []
        self.measured = False
        self.drives = []
        self.result = None
        self._cancel_pack = False
        self.folder_rows: dict[str, ChoiceRow] = {}
        self.browsers: list = []
        self.browser_rows: list[tuple] = []
        self.pick_cards: list[CategoryCard] = []
        self.pick_filled = False
        self.back_btn.clicked.connect(self.on_back)
        self.next_btn.clicked.connect(self.on_next)
        for build in (self._page_welcome, self._page_check, self._page_pick, self._page_what,
                      self._page_where, self._page_packing, self._page_done):
            self.stack.addWidget(build())
        self.go(self.WELCOME)

    # --- pages ------------------------------------------------------------
    def _page_welcome(self):
        page = HeroPage("Welcome to PenguinPort",
                        "Move from Windows to Linux without losing a thing.")
        frame, box = card()
        box.addWidget(label("Here's what happens next", "Section"))
        for icon, title, text in (
                ("Apps", "Check this PC and pick your apps",
                 "See what works on Linux and choose the Linux apps you want."),
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
        page.body.addWidget(label("\u2714  PenguinPort only reads from this PC. It never changes, "
                                  "deletes or moves anything here.", "Good"))
        page.body.addStretch(1)
        return page

    def _page_check(self):
        page = Page("Checking this PC", "Seeing how ready your apps and hardware are for Linux.")
        self.check_views = QStackedWidget()
        page.body.addWidget(self.check_views, 1)

        # 1) the live scan
        scan = QWidget()
        scan.setObjectName("Content")
        sv = QVBoxLayout(scan)
        sv.setContentsMargins(0, 0, 0, 0)
        frame, box = card()
        head = QHBoxLayout()
        head.addWidget(picture(ICONS / "hardware.svg", 44))
        head.addSpacing(10)
        words = QVBoxLayout()
        words.setSpacing(2)
        words.addWidget(label("Getting to know your PC", "Section"))
        words.addWidget(label("About 30 seconds. Nothing on this PC gets changed.", "Muted"))
        head.addLayout(words, 1)
        box.addLayout(head)
        box.addSpacing(8)
        self.stages = StageList(["Looking at your apps", "Finding Linux matches",
                                 "Checking your hardware", "Getting your results ready"])
        box.addWidget(self.stages)
        box.addSpacing(8)
        self.scan_bar = QProgressBar()
        self.scan_bar.setRange(0, 0)
        box.addWidget(self.scan_bar)
        self.scan_item = label("", "Muted", wrap=False)
        box.addWidget(self.scan_item)
        sv.addWidget(frame)
        sv.addStretch(1)
        self.check_views.addWidget(scan)

        # 2) the friendly results
        res = QWidget()
        res.setObjectName("Content")
        rv = QVBoxLayout(res)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(12)
        top = QHBoxLayout()
        top.setSpacing(12)
        apps_card, ab = card()
        arow = QHBoxLayout()
        self.ring = ScoreRing()
        arow.addWidget(self.ring)
        arow.addSpacing(14)
        acol = QVBoxLayout()
        acol.addStretch(1)
        self.apps_headline = label("", "Section")
        acol.addWidget(self.apps_headline)
        self.apps_sub = label("", "Muted")
        acol.addWidget(self.apps_sub)
        acol.addStretch(1)
        arow.addLayout(acol, 1)
        ab.addLayout(arow)
        top.addWidget(apps_card, 3)
        hw_card, hb = card()
        hrow = QHBoxLayout()
        hrow.addWidget(picture(ICONS / "hardware.svg", 36))
        hrow.addSpacing(8)
        hrow.addWidget(label("Your hardware", "Section"), 1)
        hb.addLayout(hrow)
        self.hw_lines = label("", "Muted")
        hb.addWidget(self.hw_lines)
        self.hw_status = label("")
        hb.addWidget(self.hw_status)
        hb.addStretch(1)
        top.addWidget(hw_card, 2)
        rv.addLayout(top)
        self.notes_card, self.notes_box = card()
        rv.addWidget(self.notes_card)
        rv.addStretch(1)
        row = QHBoxLayout()
        details = QPushButton("See the full list")
        details.clicked.connect(lambda: self.check_views.setCurrentIndex(2))
        row.addWidget(details)
        self.save_report_btn = QPushButton("Save a report")
        self.save_report_btn.clicked.connect(self.save_report)
        row.addWidget(self.save_report_btn)
        row.addStretch(1)
        rv.addLayout(row)
        self.check_views.addWidget(res)

        # 3) the full details, for anyone who wants them
        det = QWidget()
        det.setObjectName("Content")
        dv = QVBoxLayout(det)
        dv.setContentsMargins(0, 0, 0, 0)
        tabs = QTabWidget()
        self.apps_tree = QTreeWidget()
        self.apps_tree.setHeaderLabels(["Your Windows app", "On Linux"])
        self.apps_tree.setColumnWidth(0, 300)
        self.hw_tree = QTreeWidget()
        self.hw_tree.setHeaderLabels(["Part", "Details"])
        self.hw_tree.setColumnWidth(0, 150)
        self.hw_tree.setRootIsDecorated(False)
        tabs.addTab(self.apps_tree, "Apps")
        tabs.addTab(self.hw_tree, "Hardware")
        dv.addWidget(tabs, 1)
        back = QPushButton("Back to the summary")
        back.clicked.connect(lambda: self.check_views.setCurrentIndex(1))
        brow = QHBoxLayout()
        brow.addWidget(back)
        brow.addStretch(1)
        dv.addLayout(brow)
        self.check_views.addWidget(det)
        return page

    def _page_pick(self):
        page = Page("Pick your Linux apps",
                    "Here's what you use on Windows, next to the Linux apps that do the same "
                    "job. Click the ones you want; your new PC installs them for you.")
        self.pick_box = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        holder = QWidget()
        holder.setObjectName("Content")
        holder.setLayout(self.pick_box)
        self.pick_box.setContentsMargins(0, 0, 6, 0)
        self.pick_box.setSpacing(8)
        scroll.setWidget(holder)
        self.pick_scroll = scroll
        self._pick_watch = WidthWatcher(scroll, self._fit_pick_cards)
        page.body.addWidget(scroll, 1)
        self.pick_total = label("", "Section")
        page.body.addWidget(self.pick_total)
        return page

    def fill_pick(self):
        while self.pick_box.count():
            item = self.pick_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.pick_cards.clear()
        categories, unmatched = by_category(self.grouped)
        if not categories:
            self.pick_box.addWidget(label("None of your apps have a Linux alternative we know "
                                          "of yet. That's fine: your files still move.",
                                          "Muted"))
        yours = [c for c in categories if any(not a.get("builtin") for a in c.windows_apps)]
        builtin = [c for c in categories if c not in yours]
        if yours:
            self.pick_box.addWidget(label("Apps you installed", "Section"))
        for cat in yours + builtin:
            if cat is (builtin[0] if builtin else None):
                self.pick_box.addSpacing(10)
                self.pick_box.addWidget(label("Built into Windows", "Section"))
                self.pick_box.addWidget(label(
                    "Every Windows PC has these. Most Linux PCs come with their own versions, "
                    "and PenguinPort only installs what's missing.", "Muted"))
            card_ = CategoryCard(cat)
            card_.changed.connect(self.update_pick_total)
            self.pick_cards.append(card_)
            self.pick_box.addWidget(card_)
        if unmatched:
            self.pick_box.addSpacing(6)
            self.pick_box.addWidget(label(f"No Linux alternative needed or known "
                                          f"({len(unmatched)})", "Section"))
            self.pick_box.addWidget(label(
                ", ".join(a["name"] for a in unmatched) + ". Your files from these still move "
                "with everything else.", "Muted"))
        self.pick_box.addStretch(1)
        self.pick_filled = True
        self._fit_pick_cards(self.pick_scroll.viewport().width())
        self.update_pick_total()

    def _fit_pick_cards(self, width: int):
        for card_ in self.pick_cards:
            card_.fit_width(width - 8)

    def update_pick_total(self):
        picks = self.chosen_apps()
        auto = len({p["flatpak"] for p in picks if p.get("flatpak")})
        links = len({p["name"] for p in picks if not p.get("flatpak") and not p.get("included")})
        text = (f"Up to {plural(auto, 'app')} will install automatically "
                "(any already on your Linux PC are skipped)")
        if links:
            text += f"  \u00b7  {plural(links, 'website link')} for you to open"
        self.pick_total.setText(text)

    def chosen_apps(self) -> list[dict]:
        out, seen = [], set()
        for card_ in self.pick_cards:
            names = ", ".join(a["name"] for a in card_.category.windows_apps)
            for opt in card_.picks():
                key = opt.get("flatpak") or opt.get("url") or opt["name"]
                if key not in seen:
                    seen.add(key)
                    out.append({"windows": names, "category": card_.category.name, **opt})
        return out

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
        self.drive_list.currentRowChanged.connect(lambda _: self.update_where())
        box.addWidget(self.drive_list)
        self.space_label = label("")
        box.addWidget(self.space_label)
        page.body.addWidget(frame)

        frame2, box2 = card()
        box2.addWidget(label("Choose a password", "Section"))
        box2.addWidget(label("You'll type it once more on your Linux PC. Write it down: if it's "
                             "lost, nobody can open your files, not even PenguinPort.", "Muted"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self.pw1 = text_field("At least 6 characters", password=True)
        self.pw2 = text_field("Type it again", password=True)
        for field in (self.pw1, self.pw2):
            field.textChanged.connect(lambda _: self.update_where())
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
                "Plug in the USB drive and open the \u201cPenguinPort Move\u201d folder.",
                "Double-click the PenguinPort installer for your Linux, then click Install.",
                "Open PenguinPort from your app menu and type your password."), 1):
            box2.addWidget(label(f"<b>{n}.</b>&nbsp;&nbsp;{line}"))
        box2.addWidget(label("The \u201cSTART HERE\u201d file on the drive has the same steps.",
                             "Muted"))
        page.body.addWidget(frame2)
        row = QHBoxLayout()
        open_btn = QPushButton("Open the PenguinPort Move folder")
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
        if index == self.PICK and not self.pick_filled and self.grouped is not None:
            self.fill_pick()
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
            self.WELCOME: True, self.CHECK: self.grouped is not None, self.PICK: True,
            self.WHAT: self.measured,
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
                                    "Packing isn't finished. Stop and close PenguinPort?") \
                    != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._cancel_pack = True
        event.accept()

    # --- step: check this PC ---------------------------------------------
    def start_check(self):
        self.check_views.setCurrentIndex(0)
        self.stages.set_stage(0)

        def work(report):
            report(("stage", 0))
            apps = scan_apps()
            report(("stage", 1))
            pause = min(0.08, 2.5 / max(len(apps), 1))   # let names flick by, never > 2.5 s
            for app in sorted(apps, key=lambda a: a["name"].lower()):
                report(("item", f"Found {app['name']}"))
                time.sleep(pause)
            report(("item", "Notepad, Paint, Photos and the other built-in programs"))
            time.sleep(0.4)
            grouped = match_all(apps + builtin_apps(scanned=apps))
            report(("stage", 2))
            report(("item", "Processor, memory, graphics, Wi-Fi..."))
            hw = scan_hardware()
            report(("stage", 3))
            report(("item", ""))
            time.sleep(0.4)
            return grouped, hw

        start_task(self, work, self.show_check, self.task_failed, self.check_progress)

    def check_progress(self, info):
        kind, value = info
        if kind == "stage":
            self.stages.set_stage(value)
        else:
            self.scan_item.setText(value)

    def show_check(self, result):
        self.grouped, self.hw = result
        self.stages.set_stage(4)
        mine = lambda group: [r for r in self.grouped[group] if not r.app.get("builtin")]
        total = sum(len(mine(g)) for g in GROUPS)          # built-ins don't count: every
        ready = len(mine(GROUP_SAME)) + len(mine(GROUP_ALT))  # Windows PC has them
        self.ring.set_score(ready, total)
        if total == 0:
            self.apps_headline.setText("No apps to worry about")
            self.apps_sub.setText("Your files are what matter most, and they're coming with you.")
        elif ready == total:
            self.apps_headline.setText("Great news: all your apps are covered")
            self.apps_sub.setText("Every app has a Linux version or a free alternative. "
                                  "Next, you'll pick the ones you want.")
        else:
            self.apps_headline.setText(f"{ready} of {total} apps are ready for Linux")
            self.apps_sub.setText("Those have a Linux version or a free alternative. "
                                  "Next, you'll pick the ones you want.")
        hw = self.hw
        bits = []
        if hw.get("cpu"):
            bits.append(hw["cpu"][0].replace("(R)", "").replace("(TM)", "").replace("CPU ", ""))
        if hw.get("ram_gb"):
            bits.append(f"{hw['ram_gb']:g} GB of memory")
        if hw.get("gpu"):
            bits.append(hw["gpu"][0])
        self.hw_lines.setText("<br>".join(bits) or "Couldn't read the hardware details.")
        notes = hardware_notes(hw)
        if notes:
            set_role(self.hw_status, "Warn")
            self.hw_status.setText(f"{plural(len(notes), 'thing')} to know, below")
        else:
            set_role(self.hw_status, "Good")
            self.hw_status.setText("\u2714  Looks good for Linux")
        while self.notes_box.count():
            item = self.notes_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    w = item.layout().takeAt(0).widget()
                    if w:
                        w.deleteLater()
        self.notes_card.setVisible(bool(notes))
        if notes:
            self.notes_box.addWidget(label("Good to know before you switch", "Section"))
            for note in notes:
                row = QHBoxLayout()
                row.addWidget(picture(ICONS / "heads-up.svg", 22), 0, Qt.AlignmentFlag.AlignTop)
                row.addSpacing(8)
                row.addWidget(label(note), 1)
                self.notes_box.addLayout(row)
        self._fill_check_details()
        self.check_views.setCurrentIndex(1)
        self.update_buttons()

    def _fill_check_details(self):
        self.apps_tree.clear()
        for group in GROUPS:
            parent = QTreeWidgetItem([f"{group} ({len(self.grouped[group])})", ""])
            font = parent.font(0)
            font.setBold(True)
            parent.setFont(0, font)
            for r in self.grouped[group]:
                linux = ", ".join(option_text(o) for o in r.options) or "No Linux alternative"
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

    def save_report(self):
        default = Path.home() / "Desktop" / "PenguinPort report.html"
        if not default.parent.exists():
            default = Path.home() / "PenguinPort report.html"
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
        self._measuring = 0
        self.what_box.addWidget(label("Your folders", "Section"))
        for folder in self.folders:
            self._add_folder_row(folder)
        if not self.folders:
            self.what_box.addWidget(label("No personal folders were found.", "Muted"))
        self.leave_windows = QCheckBox("Leave Windows-only files behind: shortcuts (.lnk), "
                                       "programs and installers (.exe, .msi). They don't run on "
                                       "Linux.")
        self.leave_windows.setChecked(True)
        self.leave_windows.toggled.connect(self._toggle_windows_files)
        self.what_box.addWidget(self.leave_windows)
        self.what_box.addSpacing(8)
        self.what_box.addWidget(label("Other folders and files", "Section"))
        self.what_box.addWidget(label("Bring anything else too: a folder on another drive, "
                                      "your projects folder, or a few single files.", "Muted"))
        self.extra_box = QVBoxLayout()
        self.extra_box.setSpacing(8)
        self.what_box.addLayout(self.extra_box)
        add_row = QHBoxLayout()
        add_folder = QPushButton("+  Add a folder...")
        add_folder.clicked.connect(self.add_extra_folder)
        add_files = QPushButton("+  Add files...")
        add_files.clicked.connect(self.add_extra_files)
        add_row.addWidget(add_folder)
        add_row.addWidget(add_files)
        add_row.addStretch(1)
        self.what_box.addLayout(add_row)
        self.what_box.addSpacing(8)
        self.what_box.addWidget(label("Your browsers", "Section"))
        self.what_box.addWidget(label("Bookmarks and history come along automatically. Firefox "
                                      "passwords too; other browsers lock theirs, so use "
                                      "\u201cAdd passwords\u201d to export them.", "Muted"))
        self.browser_box = QVBoxLayout()
        self.browser_box.setSpacing(8)
        self.what_box.addLayout(self.browser_box)
        self.browser_box.addWidget(label("Looking for browsers...", "Muted"))
        start_task(self, lambda report: find_browsers(), self.show_browsers, self.task_failed)
        self.what_box.addSpacing(8)
        apps = ChoiceRow(ICONS / "Apps.svg", "Your app list",
                         "So Linux can install the apps you picked", True, False)
        apps.title.setStyleSheet("")
        self.what_box.addWidget(apps)
        self.what_box.addSpacing(8)
        self.what_box.addWidget(label("Coming soon", "Section"))
        for item in COMING_SOON:
            self.what_box.addWidget(ChoiceRow(ICONS / "Soon.svg", item, "", False, False))
        self.what_box.addStretch(1)
        for folder in self.folders:
            self._measure(folder)

    def _add_folder_row(self, folder, box=None):
        icon = ICONS / "Downloads.svg" if folder.only_files else folder_icon(folder.name)
        detail = str(folder.path) if folder.extra and not folder.only_files else "Measuring..."
        row = ChoiceRow(icon, folder.name, detail)
        row.box.toggled.connect(lambda _: self.update_total())
        if not folder.only_files:
            choose = QPushButton("Choose...")
            choose.setToolTip("Pick exactly which files and folders to bring")
            choose.clicked.connect(lambda _=False, f=folder: self.choose_inside(f))
            row.side.addWidget(choose)
        if folder.extra:
            remove = QPushButton("Remove")
            remove.clicked.connect(lambda _=False, f=folder: self.remove_extra(f))
            row.side.addWidget(remove)
        self.folder_rows[folder.name] = row
        (box or self.what_box).addWidget(row)

    # --- browsers -------------------------------------------------------
    BROWSER_LOGOS = {"firefox": "org.mozilla.firefox", "chrome": "com.google.Chrome",
                     "brave": "com.brave.Browser", "vivaldi": "com.vivaldi.Vivaldi",
                     "opera": "com.opera.Opera"}

    def show_browsers(self, profiles):
        while self.browser_box.count():
            item = self.browser_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.browsers = profiles
        self.browser_rows.clear()
        if not profiles:
            self.browser_box.addWidget(label("No browser bookmarks or history were found.",
                                             "Muted"))
        for p in profiles:
            icon = logo_for({"flatpak": self.BROWSER_LOGOS.get(p.browser, "")})
            row = ChoiceRow(icon, p.label, self._browser_detail(p))
            if p.family == "chromium":
                btn = QPushButton("Add passwords")
                btn.setObjectName("Primary")
                # never let the label clip: size the button to its text plus padding
                btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance("Add passwords") + 44)
                btn.clicked.connect(lambda _=False, prof=p, r=row: self.move_browser_passwords(prof, r))
                row._pw_btn = btn
                row.side.addWidget(btn)
            self.browser_rows.append((row, p))
            self.browser_box.addWidget(row)

    def _browser_detail(self, p) -> str:
        bits = [plural(p.bookmarks, "bookmark"), f"{p.history:,} history"]
        if p.family == "firefox":
            bits.append(plural(p.passwords, "saved password") + " \u2014 all move automatically")
        elif p.password_csv:
            bits.append("\u2714 passwords ready to move")
        else:
            bits.append("bookmarks and history move automatically")
        return "  \u00b7  ".join(bits)

    def move_browser_passwords(self, p, row):
        """Bulletproof password export: PenguinPort copies the exact passwords-page address to
        the clipboard, the user pastes it into the browser they already have open (pasting
        always works, unlike launching, which a running Chrome ignores), clicks Export, and
        PenguinPort auto-detects the downloaded CSV from their Downloads folder."""
        import time
        from landfall.scan.browsers import watch_for_export

        self._pw_pick_path = None
        self._pw_watching = False
        url = p.password_url

        def copy_and_watch():
            # put the address on the clipboard so the user only has to paste
            try:
                from PySide6.QtWidgets import QApplication
                QApplication.clipboard().setText(url)
            except Exception:
                pass
            # also try to open the browser to the page (works if it's not already running)
            open_password_export(p)
            self._pw_watching = True
            folders = [Path.home() / "Downloads", Path.home() / "Desktop", Path.home()]
            since = time.time()

            def work(report):
                return watch_for_export(folders, since, lambda: not self._pw_watching)

            start_task(self, work, self._pw_found, self._pw_watch_failed)
            return "advance"

        export_btn = ("its <b>Export</b> button" if p.browser == "edge"
                      else "the <b>Download file</b> button next to <b>Export passwords</b>")

        steps = [
            {"title": f"Bring your {p.name} passwords",
             "body": f"{p.name} locks your saved passwords so only it can read them. The one safe "
                     f"way to copy them is {p.name}'s own <b>Export</b> button. PenguinPort makes "
                     "this easy: it copies the exact page address for you, you paste it, click "
                     "Export, and PenguinPort grabs the file on its own.<br><br>Prefer to skip "
                     "it? Click <b>Skip this</b> and you'll just sign in to your sites again on "
                     "Linux."},
            {"title": "Copy the address, then paste it",
             "body": f"Click the orange button \u2014 it copies the {p.name} passwords-page "
                     f"address and opens {p.name} for you.<br><br>Then, in {p.name}:<br>"
                     "<b>1.</b> Click the address bar at the top (or press <b>Ctrl+L</b>).<br>"
                     "<b>2.</b> Paste with <b>Ctrl+V</b>, then press <b>Enter</b>.<br>"
                     f"<b>3.</b> On that page, click {export_btn}, and confirm with your Windows "
                     "PIN or password. Save it in your <b>Downloads</b> folder.<br><br>"
                     "That's it \u2014 PenguinPort watches for the file and takes it from there.",
             "action": (f"Copy address and open {p.name}", copy_and_watch)},
            {"title": "Grabbing your passwords\u2026",
             "body": f"Waiting for your exported file\u2026<br><br>In {p.name}: click the address "
                     f"bar, paste (<b>Ctrl+V</b>), press <b>Enter</b>, then click Export. The "
                     "address is already copied, ready to paste.<br><br>As soon as the file "
                     "lands in Downloads, PenguinPort picks it up automatically.<br><br>"
                     "(Nothing happening? You can <b>Skip this</b> and move passwords later.)",
             "wait": True},
        ]
        self._pw_dialog = StepDialog(f"{p.name} passwords", steps, self, accent_last="Done")
        result = self._pw_dialog.run()
        self._pw_watching = False
        if result == "done" and self._pw_pick_path:
            p.password_csv = self._pw_pick_path
            row.detail.setText(self._browser_detail(p))
            row._pw_btn.setText("\u2714 Added")
            row._pw_btn.setEnabled(False)

    def _pw_found(self, path):
        self._pw_watching = False
        if path:
            self._pw_pick_path = Path(path)
            # jump straight to done
            d = getattr(self, "_pw_dialog", None)
            if d is not None:
                d.result_value = "done"
                d.dialog.accept()

    def _pw_watch_failed(self, err):
        self._pw_watching = False

    def selected_browsers(self):
        return [p for row, p in self.browser_rows if row.box.isChecked()]

    def _toggle_windows_files(self, leave: bool):
        for folder in self.folders:
            folder.keep_windows_files = not leave
            self._measure(folder)

    def _measure(self, folder):
        self._measuring += 1
        self.measured = False
        self.folder_rows[folder.name].detail.setText("Measuring...")
        self.what_total.setText("Measuring your folders...")
        self.update_buttons()
        start_task(self, lambda report: measure(folder), self._measured_one, self.task_failed)

    def _measured_one(self, folder):
        self._measuring -= 1
        if folder.name in self.folder_rows:
            self.show_measured(folder)
        if self._measuring == 0:
            self.measure_done(None)

    def show_measured(self, folder):
        text = f"{plural(folder.files, 'file')}  \u00b7  {human_size(folder.bytes)}"
        if folder.excludes:
            text += f"  \u00b7  {plural(len(folder.excludes), 'item')} left out"
        if folder.windows_only:
            text += f"  \u00b7  {plural(folder.windows_only, 'Windows-only file')} left behind"
        if folder.cloud_only:
            text += f"  \u00b7  {folder.cloud_only:,} online-only OneDrive files stay in the cloud"
        if folder.extra and not folder.only_files:
            text = f"{folder.path}  \u00b7  " + text
        self.folder_rows[folder.name].detail.setText(text)

    def choose_inside(self, folder):
        picked = FolderPicker(folder.path, folder.excludes,
                              f"Choose what to bring from {folder.name}", self).run()
        if picked is not None:
            folder.excludes = picked
            self._measure(folder)

    def add_extra_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Pick a folder to bring along",
                                                str(Path.home()))
        if not path:
            return
        if any(Path(path) == f.path and not f.only_files for f in self.folders):
            QMessageBox.information(self, "Already added", "That folder is already on the list.")
            return
        folder = extra_folder(path, {f.name for f in self.folders})
        folder.keep_windows_files = not self.leave_windows.isChecked()
        self.folders.append(folder)
        self._add_folder_row(folder, self.extra_box)
        self._measure(folder)

    def add_extra_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Pick files to bring along",
                                                str(Path.home()))
        if not paths:
            return
        folder = extra_files(paths, {f.name for f in self.folders})
        self.folders.append(folder)
        self._add_folder_row(folder, self.extra_box)
        self.folder_rows[folder.name].title.setText(
            f"<b>{folder.name}</b>  ({plural(len(paths), 'file')})")
        self._measure(folder)

    def remove_extra(self, folder):
        self.folders.remove(folder)
        row = self.folder_rows.pop(folder.name)
        row.setParent(None)
        row.deleteLater()
        self.update_total()

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
            self.what_total.setText(f"Total to move: {plural(files, 'file')}, "
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
        fit_list(self.drive_list, 1, 4)
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
        # No need to close browsers: PenguinPort copies their bookmark/history files with a
        # shared read, which works even while the browser is open.
        self._pack_browsers = self.selected_browsers()
        self._cancel_pack = False
        self.stop_btn.setEnabled(True)
        folders, drive, password = self.selected_folders(), self.current_drive(), self.pw1.text()
        import tempfile
        self._browser_staging = Path(tempfile.mkdtemp(prefix="penguinport-browsers-"))
        folders = folders + browser_folders(self._pack_browsers, staging=self._browser_staging)
        extra = {"apps": self._app_records(), "install": self.chosen_apps(),
                 "extra_folders": [f.name for f in folders if f.extra],
                 "browsers": browser_records(self._pack_browsers),
                 "hardware": self.hw or {}}
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

    def _clean_browser_staging(self):
        staging = getattr(self, "_browser_staging", None)
        if staging:
            import shutil
            shutil.rmtree(staging, ignore_errors=True)
            self._browser_staging = None

    def pack_done(self, result):
        self._clean_browser_staging()
        self.result = result
        text = (f"<b>{plural(result.files, 'file')}</b> ({human_size(result.bytes)}) packed and locked "
                f"with your password in:<br><b>{result.folder}</b>")
        if result.skipped:
            text += (f"<br><br>{len(result.skipped):,} file(s) couldn't be read (for example, "
                     "open in another program) and were left out.")
        self.done_summary.setText(text)
        self.go(self.DONE)

    def pack_failed(self, err):
        self._clean_browser_staging()
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
        QMessageBox.warning(self, "Something went wrong", f"PenguinPort hit a problem:\n{err}")


def build_window() -> QWidget:
    return Wizard()


def main() -> int:
    app = make_app()
    return run_window(app, build_window())
