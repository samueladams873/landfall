"""A classic, early-2000s Windows-inspired look (original styling, no Microsoft assets)."""
from pathlib import Path

_DATA = (Path(__file__).parent / "data").as_posix()

FONT_FAMILY = "Tahoma, Verdana, 'DejaVu Sans', sans-serif"

STYLE = f"""
* {{ font-family: {FONT_FAMILY}; font-size: 10pt; color: #000; }}
QWidget#Root {{ background: #ECE9D8; }}

/* Blue banner across the top */
QFrame#Banner {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3A80F3, stop:0.08 #2B6FE6, stop:0.5 #0F5BD8, stop:0.92 #0A50C8, stop:1 #08389E);
    border-bottom: 2px solid #F0A030;
}}
QLabel#BannerTitle {{ color: white; font-size: 16pt; font-weight: bold; background: transparent; }}
QLabel#BannerSub {{ color: #DCE8FF; font-size: 10pt; background: transparent; }}

/* White page header, like a classic setup wizard */
QFrame#PageHeader {{ background: white; border-bottom: 1px solid #ACA899; }}
QLabel#PageTitle {{ font-weight: bold; font-size: 11pt; background: transparent; }}
QLabel#PageSub {{ color: #333; background: transparent; padding-left: 14px; }}

/* Left side panel on the welcome and finish pages */
QFrame#SidePanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7BA2E7, stop:1 #4A63C9);
}}
QLabel#SideText {{ color: white; font-size: 22pt; font-weight: bold; background: transparent; }}
QLabel#SideSmall {{ color: #E8EEFF; background: transparent; }}

QLabel#BigTitle {{ font-size: 15pt; font-weight: bold; }}
QLabel#Muted {{ color: #555; }}
QLabel#Warn {{ color: #A03000; font-weight: bold; }}
QLabel#Good {{ color: #1E7B1E; font-weight: bold; }}

/* Rounded classic buttons with an orange hover glow */
QPushButton {{
    min-width: 84px; min-height: 26px; padding: 2px 14px;
    border: 1px solid #003C74; border-radius: 3px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:0.85 #ECEBE6, stop:1 #D6D0C5);
}}
QPushButton:hover {{ border: 2px solid #F8B330; padding: 1px 13px; }}
QPushButton:pressed {{ background: #E3E2DA; }}
QPushButton:disabled {{ color: #A0A0A0; border-color: #C9C7BA; background: #F4F3EE; }}

/* The green "go" button */
QPushButton#Primary {{
    color: white; font-weight: bold; border: 1px solid #1E5E1E;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #5FCB5F, stop:0.45 #3AA83A, stop:1 #237D23);
}}
QPushButton#Primary:hover {{ border: 2px solid #F8B330; }}
QPushButton#Primary:disabled {{ color: #E0E0E0; border-color: #9DBF9D;
    background: #A7CFA7; }}

QFrame#Footer {{ border-top: 1px solid #ACA899; background: #ECE9D8; }}

QTreeWidget, QListWidget, QLineEdit {{
    background: white; border: 1px solid #7F9DB9; selection-background-color: #316AC5;
}}
QTreeWidget::item, QListWidget::item {{ padding: 2px; }}
QHeaderView::section {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #EBEADB);
    border: none; border-right: 1px solid #D6D2C2; border-bottom: 2px solid #D6D2C2; padding: 3px 6px;
}}
QLineEdit {{ padding: 4px; min-height: 20px; }}

QTabWidget::pane {{ border: 1px solid #919B9C; background: white; top: -1px; }}
QTabBar::tab {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #ECEBE6);
    border: 1px solid #919B9C; border-bottom: none; padding: 4px 14px; margin-right: 1px;
    border-top-left-radius: 3px; border-top-right-radius: 3px;
}}
QTabBar::tab:selected {{ background: white; border-top: 3px solid #F8B330; }}

QProgressBar {{
    border: 1px solid #7F9DB9; border-radius: 3px; background: white; height: 20px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8EE58E, stop:0.5 #37C437, stop:1 #2BA02B);
    margin: 1px; border-radius: 2px;
}}

QCheckBox, QRadioButton {{ spacing: 8px; padding: 3px 0; }}
QCheckBox:disabled, QRadioButton:disabled {{ color: #8A8A8A; }}
QCheckBox::indicator {{
    width: 13px; height: 13px; border: 1px solid #1C5180; border-radius: 1px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #DCDCD7, stop:1 #FFFFFF);
}}
QCheckBox::indicator:hover {{ border: 1px solid #F8B330; }}
QCheckBox::indicator:checked {{ image: url({_DATA}/check.svg); }}
QCheckBox::indicator:disabled {{ border-color: #CAC8BB; background: #F4F3EE; }}
QCheckBox::indicator:checked:disabled {{ image: url({_DATA}/check-off.svg); }}
"""
