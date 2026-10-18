"""Landfall's look: modern and Windows-friendly. Original styling, no Microsoft assets."""
from pathlib import Path

DATA = Path(__file__).parent / "data"
_ICONS = (DATA / "icons").as_posix()
FONT = "Inter"

BLUE, BLUE_DARK, GREEN, TEXT, MUTED = "#2F7DF6", "#1450B8", "#2BA84A", "#1B2433", "#5B6B82"

STYLE = f"""
* {{ font-family: "{FONT}"; font-size: 10.5pt; color: {TEXT}; }}
QWidget#Root, QWidget#Content {{ background: #EEF3FA; }}

/* Left side: brand and the list of steps */
QFrame#Sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2A74EC, stop:1 {BLUE_DARK});
}}
QLabel#Brand {{ color: white; font-size: 17pt; font-weight: 700; background: transparent; }}
QLabel#BrandSub {{ color: #D6E6FF; font-size: 9.5pt; background: transparent; }}
QLabel#Step {{ color: #DCE8FF; background: transparent; padding: 7px 10px; border-radius: 8px; }}
QLabel#StepNow {{ color: white; font-weight: 600; background: rgba(255,255,255,0.18);
    padding: 7px 10px; border-radius: 8px; }}
QLabel#StepDone {{ color: white; background: transparent; padding: 7px 10px; border-radius: 8px; }}
QLabel#SideFoot {{ color: #BFD6FF; font-size: 9pt; background: transparent; }}

/* Page heading and white cards */
QLabel#PageTitle {{ font-size: 18pt; font-weight: 700; background: transparent; }}
QLabel#PageSub {{ color: {MUTED}; font-size: 11pt; background: transparent; }}
QFrame#Card {{ background: white; border: 1px solid #DCE4F0; border-radius: 12px; }}
QFrame#Card QLabel, QFrame#Card QCheckBox {{ background: transparent; }}
QFrame#Row {{ background: white; border: 1px solid #E3E9F3; border-radius: 10px; }}
QFrame#Row:hover {{ border: 1px solid #A9C8FB; }}
QFrame#Row QLabel, QFrame#Row QCheckBox {{ background: transparent; border: none; }}
QFrame#Row QLabel#Pill {{ color: #1450B8; background: #E3EEFF; border-radius: 9px;
    padding: 3px 10px; font-size: 9pt; font-weight: 600; }}
QFrame#Row QLabel#PillNew {{ color: #8A4B00; background: #FFF0CC; border-radius: 9px;
    padding: 3px 10px; font-size: 9pt; font-weight: 600; }}
QFrame#Row QLabel#Good {{ color: #1E7E3A; background: #E2F6E8; border-radius: 9px;
    padding: 3px 10px; font-size: 9pt; font-weight: 600; }}
QFrame#Row QLabel#Muted {{ color: #5B6B82; }}

QLabel#Hero {{ font-size: 22pt; font-weight: 700; }}
QLabel#Section {{ font-size: 11.5pt; font-weight: 600; }}
QLabel#Muted {{ color: {MUTED}; }}
QLabel#Warn {{ color: #B4410E; font-weight: 600; }}
QLabel#Good {{ color: #1E7E3A; font-weight: 600; }}
QLabel#Pill {{ color: #1450B8; background: #E3EEFF; border-radius: 9px; padding: 2px 9px;
    font-size: 9pt; font-weight: 600; }}
QLabel#PillNew {{ color: #8A4B00; background: #FFF0CC; border-radius: 9px; padding: 2px 9px;
    font-size: 9pt; font-weight: 600; }}

/* Footer and buttons */
QFrame#Footer {{ background: white; border-top: 1px solid #DCE4F0; }}
QPushButton {{
    min-width: 92px; min-height: 34px; padding: 0 18px; border-radius: 8px;
    border: 1px solid #C9D3E3; background: white; font-weight: 500;
}}
QPushButton:hover {{ border-color: {BLUE}; background: #F5F9FF; }}
QPushButton:pressed {{ background: #E6EFFD; }}
QPushButton:disabled {{ color: #A3AEC0; border-color: #E1E6EE; background: #F7F9FC; }}
QPushButton#Primary {{
    color: white; font-weight: 600; border: none;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3BC062, stop:1 #24963F);
}}
QPushButton#Primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 #45CB6C, stop:1 #279E44); }}
QPushButton#Primary:disabled {{ color: #F0F6F1; background: #A9D9B6; }}

/* Lists, trees, inputs, tabs */
QTreeWidget, QListWidget {{
    background: white; border: 1px solid #DCE4F0; border-radius: 10px; padding: 4px;
    selection-background-color: #DCEAFF; selection-color: {TEXT}; outline: none;
}}
QTreeWidget::item, QListWidget::item {{ padding: 6px 4px; border-radius: 6px; }}
QListWidget::item:selected {{ background: #DCEAFF; color: {TEXT}; }}
QHeaderView::section {{ background: white; border: none; border-bottom: 1px solid #E3E9F3;
    padding: 6px; color: {MUTED}; font-weight: 600; }}
QLineEdit {{ background: white; border: 1px solid #C9D3E3; border-radius: 8px;
    padding: 0 10px; }}
QLineEdit:focus {{ border: 2px solid {BLUE}; padding: 0 9px; }}
QComboBox {{ background: white; border: 1px solid #C9D3E3; border-radius: 8px; padding: 0 10px;
    font-weight: 600; }}
QComboBox:hover {{ border-color: {BLUE}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url({_ICONS}/chevron.svg); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{ background: white; border: 1px solid #C9D3E3; border-radius: 8px;
    padding: 4px; selection-background-color: #DCEAFF; selection-color: {TEXT}; outline: none; }}
QTabWidget::pane {{ border: none; top: 0; }}
QTabBar::tab {{ background: transparent; border: none; padding: 8px 16px; margin-right: 4px;
    color: {MUTED}; font-weight: 600; border-bottom: 3px solid transparent; }}
QTabBar::tab:selected {{ color: {BLUE}; border-bottom: 3px solid {BLUE}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #C3CFE0; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #9FB0C8; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #C3CFE0; border-radius: 4px; min-width: 30px; }}

QProgressBar {{ border: none; border-radius: 7px; background: #DDE6F3; height: 14px;
    text-align: center; color: transparent; }}
QProgressBar::chunk {{ border-radius: 7px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 {BLUE}, stop:1 #4FA0FF); }}

QCheckBox {{ spacing: 10px; }}
QCheckBox:disabled {{ color: #9AA6B8; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1.5px solid #9FB0C8;
    background: white; }}
QCheckBox::indicator:hover {{ border-color: {BLUE}; }}
QCheckBox::indicator:checked {{ background: {BLUE}; border-color: {BLUE};
    image: url({_ICONS}/check-white.svg); }}
QCheckBox::indicator:disabled {{ background: #F1F4F9; border-color: #D5DCE6; }}
QCheckBox::indicator:checked:disabled {{ background: #A9C3EE; border-color: #A9C3EE; }}
QToolTip {{ background: {TEXT}; color: white; border: none; padding: 6px; border-radius: 6px; }}
"""
