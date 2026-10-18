"""Shared building blocks so the Windows and Linux wizards look exactly alike."""
from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QGraphicsDropShadowEffect,
                               QHBoxLayout, QLabel, QLayout, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from landfall import __version__
from landfall.theme import DATA, FONT, STYLE

ICON = DATA / "landfall.png"
ICONS = DATA / "icons"


# --- app setup -------------------------------------------------------------
def load_fonts() -> str:
    """Load the bundled Inter font so text looks the same on every computer."""
    family = None
    for ttf in sorted((DATA / "fonts").glob("*.ttf")):
        fid = QFontDatabase.addApplicationFont(str(ttf))
        fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        family = family or (fams[0] if fams else None)
    return family or FONT


def make_app(argv=None) -> QApplication:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setStyle("Fusion")
    family = load_fonts()
    font = QFont(family, 10)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app.setFont(font)
    app.setStyleSheet(STYLE.replace(f'"{FONT}"', f'"{family}"'))
    app.setWindowIcon(QIcon(str(ICON)))
    app.setApplicationName("Landfall")
    app.setDesktopFileName("landfall")
    return app


def run_window(app: QApplication, window: QWidget) -> int:
    """Show the window, run the app, then tear down in a safe order (window before app)."""
    import shiboken6

    window.show()
    code = app.exec()
    for thread, _task in getattr(window, "_tasks", []):
        thread.quit()
        thread.wait(3000)
    shiboken6.delete(window)
    return code


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
        except BaseException as err:  # shown to the user, never silently lost
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


# --- small widgets ---------------------------------------------------------
def label(text: str, name: str | None = None, wrap: bool = True) -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(wrap)
    if name:
        lab.setObjectName(name)
    return lab


def set_role(widget: QWidget, role: str):
    """Switch a label between styles (Good / Warn / Muted) and repaint it."""
    widget.setObjectName(role)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def text_field(placeholder: str = "", password: bool = False):
    """A text box sized from the real font height, so text never gets cut off at any
    Windows or Linux display scaling."""
    from PySide6.QtWidgets import QLineEdit
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    if password:
        field.setEchoMode(QLineEdit.EchoMode.Password)
    field.setMinimumHeight(field.fontMetrics().height() + 20)
    return field


def picture(path, size: int) -> QLabel:
    lab = QLabel()
    lab.setPixmap(QIcon(str(path)).pixmap(size, size))
    lab.setFixedSize(size, size)
    lab.setStyleSheet("background: transparent; border: none;")
    return lab


def logo(size: int) -> QLabel:
    lab = QLabel()
    lab.setPixmap(QPixmap(str(ICON)).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))
    lab.setStyleSheet("background: transparent;")
    return lab


def folder_icon(name: str):
    path = ICONS / f"{name}.svg"
    return path if path.exists() else ICONS / "Documents.svg"


def card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    shadow = QGraphicsDropShadowEffect(frame)
    shadow.setBlurRadius(24)
    shadow.setOffset(0, 3)
    shadow.setColor(QColor(20, 50, 100, 28))
    frame.setGraphicsEffect(shadow)
    box = QVBoxLayout(frame)
    box.setContentsMargins(20, 18, 20, 18)
    box.setSpacing(10)
    return frame, box


class ChoiceRow(QFrame):
    """A rounded row: checkbox, icon, name, and a detail line. Clicking anywhere toggles it."""

    def __init__(self, icon_path, title: str, detail: str = "", checked=True, enabled=True):
        super().__init__()
        self.setObjectName("Row")
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(12)
        self.box = QCheckBox()
        self.box.setChecked(checked)
        self.box.setEnabled(enabled)
        row.addWidget(self.box)
        row.addWidget(picture(icon_path, 28))
        text = QVBoxLayout()
        text.setSpacing(1)
        self.title = label(f"<b>{title}</b>", wrap=False)
        self.detail = label(detail, "Muted", wrap=False)
        text.addWidget(self.title)
        text.addWidget(self.detail)
        row.addLayout(text, 1)
        self.side = QHBoxLayout()
        row.addLayout(self.side)
        if not enabled:
            self.title.setStyleSheet("color: #9AA6B8;")

    def mousePressEvent(self, event):
        if self.box.isEnabled():
            self.box.toggle()
        super().mousePressEvent(event)


# --- the wizard frame ------------------------------------------------------
class Page(QWidget):
    """A step: big title, short subtitle, then whatever the step needs."""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("Content")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 26, 32, 18)
        outer.setSpacing(4)
        outer.addWidget(label(title, "PageTitle"))
        if subtitle:
            outer.addWidget(label(subtitle, "PageSub"))
        outer.addSpacing(14)
        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        outer.addLayout(self.body, 1)


class HeroPage(Page):
    """Welcome and finish pages: a big centred logo above a card."""

    def __init__(self, title: str, subtitle: str = ""):
        super().__init__("", "")
        self.layout().itemAt(0).widget().hide()
        top = QHBoxLayout()
        top.addWidget(logo(84))
        top.addSpacing(16)
        words = QVBoxLayout()
        words.addStretch(1)
        words.addWidget(label(title, "Hero"))
        if subtitle:
            words.addWidget(label(subtitle, "PageSub"))
        words.addStretch(1)
        top.addLayout(words, 1)
        self.body.addLayout(top)
        self.body.addSpacing(8)


class Shell(QWidget):
    """Window with a blue step list on the left, pages on the right, buttons at the bottom."""

    def __init__(self, steps: list[str], tagline: str):
        super().__init__()
        self.setObjectName("Root")
        self.setWindowTitle("Landfall")
        self.resize(940, 660)
        self.steps = steps

        root = QHBoxLayout(self)
        root.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)  # never squash pages
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(250)
        s = QVBoxLayout(side)
        s.setContentsMargins(18, 22, 18, 18)
        s.setSpacing(4)
        brand = QHBoxLayout()
        brand.addWidget(logo(40))
        brand.addSpacing(6)
        words = QVBoxLayout()
        words.setSpacing(0)
        words.addWidget(label("Landfall", "Brand"))
        words.addWidget(label(tagline, "BrandSub"))
        brand.addLayout(words, 1)
        s.addLayout(brand)
        s.addSpacing(22)
        self._step_rows = []
        for name in steps:
            row = QHBoxLayout()
            row.setSpacing(0)
            dot = QLabel()
            dot.setFixedSize(22, 22)
            dot.setStyleSheet("background: transparent;")
            text = label(name, "Step", wrap=False)
            row.addWidget(dot)
            row.addSpacing(4)
            row.addWidget(text, 1)
            s.addLayout(row)
            self._step_rows.append((dot, text))
        s.addStretch(1)
        s.addWidget(label(f"Version {__version__}  \u00b7  Open source", "SideFoot", wrap=False))
        root.addWidget(side)

        right = QVBoxLayout()
        right.setSpacing(0)
        self.stack = QStackedWidget()
        right.addWidget(self.stack, 1)
        footer = QFrame()
        footer.setObjectName("Footer")
        f = QHBoxLayout(footer)
        f.setContentsMargins(24, 12, 24, 12)
        self.cancel_btn = QPushButton("Cancel")
        self.back_btn = QPushButton("Back")
        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("Primary")
        f.addWidget(self.cancel_btn)
        f.addStretch(1)
        f.addWidget(self.back_btn)
        f.addSpacing(8)
        f.addWidget(self.next_btn)
        right.addWidget(footer)
        root.addLayout(right, 1)
        self.cancel_btn.clicked.connect(self.close)

    def set_step(self, index: int):
        for i, (dot, text) in enumerate(self._step_rows):
            state = "done" if i < index else "now" if i == index else "todo"
            dot.setPixmap(QIcon(str(ICONS / f"step-{state}.svg")).pixmap(20, 20))
            set_role(text, {"done": "StepDone", "now": "StepNow", "todo": "Step"}[state])


def fit_list(widget, rows_min: int = 2, rows_max: int = 4):
    """Size a list to its rows so it never steals room the rest of the page needs."""
    rows = max(rows_min, min(rows_max, widget.count()))
    row_h = widget.sizeHintForRow(0) if widget.count() else widget.fontMetrics().height() + 14
    widget.setFixedHeight(rows * row_h + 2 * widget.frameWidth() + 10)


def plural(n: int, word: str) -> str:
    """'1 file', '2 files', '1,234 files'."""
    return f"{n:,} {word}" + ("" if n == 1 else "s")
