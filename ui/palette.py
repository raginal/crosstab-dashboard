"""
Global colour palette and application stylesheet.

Analysts can modify the constants in this file to change every colour in the
application without touching any panel code.  All colour strings must be valid
CSS hex values.
"""

# ── Neutral greys (Tailwind CSS "Slate" scale) ─────────────────────────────────
GREY_50  = "#F8FAFC"   # page / panel background
GREY_100 = "#F1F5F9"   # subtle element backgrounds
GREY_200 = "#E2E8F0"   # borders, dividers
GREY_400 = "#94A3B8"   # placeholder text, icon tint
GREY_500 = "#64748B"   # secondary text
GREY_700 = "#334155"   # primary text
GREY_900 = "#0F172A"   # near-black headings

# ── Primary action colour ─────────────────────────────────────────────────────
PRIMARY       = "#2563EB"   # buttons, focus rings, active tabs
PRIMARY_HOVER = "#1D4ED8"
PRIMARY_LIGHT = "#EFF6FF"   # light-blue tint for totals / active rows
PRIMARY_TEXT  = "#FFFFFF"

# ── Semantic colours ───────────────────────────────────────────────────────────
SIG_TRUE  = "#15803D"   # significant result (green)
SIG_FALSE = "#DC2626"   # not significant   (red)
WARN_BG   = "#FEFCE8"   # warning row background
WARN_TEXT = "#92400E"

# ── Crosstab table cell colours ───────────────────────────────────────────────
TABLE_N_BG      = "#FFFFFF"   # count (N) rows
TABLE_PCT_BG    = "#F1F5F9"   # percentage rows
TABLE_PCT_FG    = "#64748B"   # percentage text (dimmed)
TABLE_TOTAL_BG  = "#EFF6FF"   # Total row / Total column
TABLE_HEADER_BG = "#334155"   # column header band  ← dark slate
TABLE_HEADER_FG = "#FFFFFF"

# ── Effect-size label colours ─────────────────────────────────────────────────
EFFECT_LABEL_COLORS: dict[str, str] = {
    "Negligible": "#94A3B8",
    "Small":      "#64748B",
    "Medium":     "#334155",
    "Large":      "#0F172A",
    "N/A":        "#94A3B8",
}

# ── Matplotlib / Seaborn palette (used in chart_panel) ────────────────────────
MPL_PALETTE = "Blues_d"   # seaborn named palette for distribution charts
MPL_SCATTER = "#2563EB"   # scatter point colour
MPL_TREND   = "#DC2626"   # regression / trend line colour

# ── Application-wide Qt Style Sheet ──────────────────────────────────────────
# Flat design: no gradients, subtle borders, consistent border-radius.
APP_STYLESHEET = f"""
/* ── Base ── */
QMainWindow, QDialog {{
    background-color: {GREY_50};
    color: {GREY_700};
}}

QWidget {{
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: {GREY_700};
}}

/* ── Group boxes ── */
QGroupBox {{
    font-weight: 600;
    border: 1px solid {GREY_200};
    border-radius: 6px;
    margin-top: 12px;
    padding: 6px 8px 8px 8px;
    background-color: #FFFFFF;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: {GREY_500};
    background-color: {GREY_50};
    font-size: 12px;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {GREY_100};
    color: {GREY_700};
    border: 1px solid {GREY_200};
    border-radius: 4px;
    padding: 4px 14px;
    min-height: 26px;
}}
QPushButton:hover {{
    background-color: {GREY_200};
    border-color: {GREY_400};
}}
QPushButton:pressed {{
    background-color: {GREY_200};
}}
QPushButton:disabled {{
    color: {GREY_400};
    background-color: {GREY_100};
    border-color: {GREY_200};
}}

/* Run Analysis button — uses objectName="run_btn" */
QPushButton#run_btn {{
    background-color: {PRIMARY};
    color: {PRIMARY_TEXT};
    border: none;
    border-radius: 5px;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.3px;
}}
QPushButton#run_btn:hover {{
    background-color: {PRIMARY_HOVER};
}}
QPushButton#run_btn:disabled {{
    background-color: {GREY_400};
    color: {GREY_100};
}}

/* ── Dropdowns ── */
QComboBox {{
    border: 1px solid {GREY_200};
    border-radius: 4px;
    padding: 3px 8px;
    background-color: #FFFFFF;
    min-height: 26px;
    selection-background-color: {PRIMARY_LIGHT};
}}
QComboBox:focus {{
    border-color: {PRIMARY};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    border: 1px solid {GREY_200};
    selection-background-color: {PRIMARY_LIGHT};
    selection-color: {PRIMARY};
}}

/* ── Line edits ── */
QLineEdit {{
    border: 1px solid {GREY_200};
    border-radius: 4px;
    padding: 3px 8px;
    background-color: #FFFFFF;
    min-height: 26px;
}}
QLineEdit:focus {{
    border-color: {PRIMARY};
}}
QLineEdit[readOnly="true"] {{
    background-color: {GREY_100};
    color: {GREY_500};
}}

/* ── Tabs ── */
QTabWidget::pane {{
    border: 1px solid {GREY_200};
    border-radius: 0 6px 6px 6px;
    background-color: #FFFFFF;
}}
QTabBar::tab {{
    background-color: {GREY_100};
    color: {GREY_500};
    border: 1px solid {GREY_200};
    border-bottom: none;
    border-radius: 5px 5px 0 0;
    padding: 6px 18px;
    margin-right: 2px;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    background-color: #FFFFFF;
    color: {PRIMARY};
    border-bottom: 2px solid {PRIMARY};
    font-weight: 700;
}}
QTabBar::tab:hover:!selected {{
    background-color: {GREY_200};
    color: {GREY_700};
}}

/* ── Table ── */
QTableWidget {{
    border: 1px solid {GREY_200};
    gridline-color: {GREY_200};
    background-color: #FFFFFF;
    alternate-background-color: {GREY_50};
}}
QHeaderView::section {{
    background-color: {GREY_100};
    border: 1px solid {GREY_200};
    padding: 4px 8px;
    font-weight: 600;
    color: {GREY_700};
}}

/* ── Scroll area ── */
QScrollArea {{
    border: none;
    background-color: {GREY_50};
}}

/* ── Scroll bars (flat — overrides Fusion gradient) ── */
QScrollBar:vertical {{
    border: none;
    background-color: {GREY_100};
    width: 10px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background-color: {GREY_200};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {GREY_400};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    border: none;
    background-color: {GREY_100};
    height: 10px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background-color: {GREY_200};
    border-radius: 5px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {GREY_400};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
}}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* ── Status bar ── */
QStatusBar {{
    background-color: {GREY_100};
    color: {GREY_500};
    font-size: 11px;
    border-top: 1px solid {GREY_200};
}}

/* ── Checkboxes ── */
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1.5px solid {GREY_400};
    border-radius: 3px;
    background-color: #FFFFFF;
}}
QCheckBox::indicator:checked {{
    background-color: {PRIMARY};
    border-color: {PRIMARY};
}}

/* ── Radio buttons ── */
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 1.5px solid {GREY_400};
    border-radius: 7px;
    background-color: #FFFFFF;
}}
QRadioButton::indicator:checked {{
    border-color: {PRIMARY};
    background-color: {PRIMARY};
}}

/* ── Text edit ── */
QTextEdit {{
    border: 1px solid {GREY_200};
    border-radius: 4px;
    background-color: #FFFFFF;
    padding: 4px;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {GREY_200};
    width: 1px;
}}

/* ── Label (plain) ── */
QLabel {{
    background-color: transparent;
}}
"""
