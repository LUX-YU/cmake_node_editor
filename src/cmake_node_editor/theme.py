"""
Visual theme for CMake Node Editor.

Cyberpunk / deep-space dark aesthetic  — neon accents on deep navy.
"""

from PyQt6.QtGui import QColor

# ── Palette ──────────────────────────────────────────────────────────────────
BG_DARK        = QColor("#0d1117")   # deepest background
BG_PANEL       = QColor("#161b22")   # panels / docks
BG_WIDGET      = QColor("#1c2333")   # inputs, buttons
BG_HOVER       = QColor("#243047")   # hover state
BG_SELECTED    = QColor("#1d3461")   # selected background

BORDER_SUBTLE  = QColor("#30363d")   # very subtle border
BORDER_DEFAULT = QColor("#3d4f6e")   # default border

ACCENT_CYAN    = QColor("#00d4ff")   # electric cyan
ACCENT_BLUE    = QColor("#3b82f6")   # vibrant blue
ACCENT_ORANGE  = QColor("#f97316")   # vivid orange
ACCENT_GREEN   = QColor("#22c55e")   # emerald green
ACCENT_PURPLE  = QColor("#a855f7")   # neon violet

TEXT_PRIMARY   = QColor("#e2e8f0")   # bright text
TEXT_SECONDARY = QColor("#94a3b8")   # muted text
TEXT_DIM       = QColor("#4b5563")   # very muted text

# ── Node visuals ──────────────────────────────────────────────────────────────
NODE_BG_TOP    = QColor("#141d32")
NODE_BG_BOT    = QColor("#0b1120")
NODE_HDR_TOP   = QColor("#0f1e38")
NODE_HDR_BOT   = QColor("#091529")
NODE_BORDER    = QColor("#1e3d6e")
NODE_BORDER_SEL= QColor("#00d4ff")
NODE_ACCENT    = QColor("#1a4080")   # header bottom line (normal)
NODE_ACCENT_SEL= QColor("#00d4ff")  # header bottom line (selected)

# ── Grid ──────────────────────────────────────────────────────────────────────
GRID_BG        = QColor("#0d1117")
GRID_MINOR     = QColor("#1c3a60")   # clearly distinguishable from bg
GRID_MAJOR     = QColor("#2a5a9a")   # noticeably bright blue

# ── Pins ──────────────────────────────────────────────────────────────────────
PIN_IN         = QColor("#22c55e")   # green  (input — receives)
PIN_OUT        = QColor("#f97316")   # orange (output — produces)

# ── Edges ─────────────────────────────────────────────────────────────────────
EDGE_NORMAL    = QColor("#3b82f6")
EDGE_SELECTED  = QColor("#00d4ff")
EDGE_TEMP      = QColor("#a855f7")

# ── Global QSS Stylesheet ─────────────────────────────────────────────────────
STYLESHEET = """
/* ============================  BASE  ============================ */
QWidget {
    background-color: #0d1117;
    color: #e2e8f0;
    font-family: "Segoe UI", "Inter", Arial, sans-serif;
    font-size: 12px;
    selection-background-color: #1d3461;
    selection-color: #00d4ff;
}
QMainWindow, QDialog {
    background-color: #0d1117;
}

/* ============================  MENU BAR  ======================== */
QMenuBar {
    background-color: #0f151e;
    border-bottom: 1px solid #1e3d6e;
    padding: 2px 4px;
    spacing: 0px;
}
QMenuBar::item {
    padding: 5px 12px;
    border-radius: 4px;
    background: transparent;
    color: #94a3b8;
}
QMenuBar::item:selected {
    background-color: #1d3461;
    color: #00d4ff;
}
QMenuBar::item:pressed {
    background-color: #243047;
    color: #00d4ff;
}

/* ============================  MENU  ============================ */
QMenu {
    background-color: #131c2e;
    border: 1px solid #1e3d6e;
    border-radius: 6px;
    padding: 4px 2px;
}
QMenu::item {
    padding: 6px 28px 6px 14px;
    border-radius: 4px;
    margin: 1px 3px;
    color: #c8d6ef;
}
QMenu::item:selected {
    background-color: #1d3461;
    color: #00d4ff;
}
QMenu::item:disabled {
    color: #3d4f6e;
}
QMenu::separator {
    height: 1px;
    background: #1e3d6e;
    margin: 4px 10px;
}
QMenu::indicator {
    width: 14px;
    height: 14px;
}

/* ============================  TOOLBAR  ========================= */
QToolBar {
    background-color: #0f151e;
    border-bottom: 1px solid #1e3d6e;
    border-top: none;
    spacing: 4px;
    padding: 3px 8px;
}
QToolBar::separator {
    width: 1px;
    background: #1e3d6e;
    margin: 4px 3px;
}
QToolBar QLabel {
    color: #94a3b8;
    font-size: 11px;
}

/* ============================  DOCK  ============================ */
QDockWidget {
    font-size: 11px;
    font-weight: 600;
    color: #64748b;
    titlebar-close-icon: none;
}
QDockWidget::title {
    background-color: #0f151e;
    padding: 6px 10px;
    border-bottom: 1px solid #1e3d6e;
    text-align: left;
    letter-spacing: 0.5px;
}
QDockWidget::close-button,
QDockWidget::float-button {
    border: none;
    background: transparent;
    padding: 2px;
    border-radius: 3px;
}
QDockWidget::close-button:hover,
QDockWidget::float-button:hover {
    background: #1d3461;
}

/* ============================  STATUS BAR  ====================== */
QStatusBar {
    background-color: #0a1020;
    border-top: 1px solid #1e3d6e;
    color: #64748b;
    font-size: 11px;
    padding: 2px 8px;
}
QStatusBar::item {
    border: none;
}

/* ============================  SCROLLBARS  ====================== */
QScrollBar:vertical {
    background: #0d1117;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #1e3d6e;
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: #3b82f6;
}
QScrollBar:horizontal {
    background: #0d1117;
    height: 8px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #1e3d6e;
    border-radius: 4px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover {
    background: #3b82f6;
}
QScrollBar::add-line,
QScrollBar::sub-line,
QScrollBar::add-page,
QScrollBar::sub-page {
    width: 0;
    height: 0;
    background: none;
}

/* ============================  GRAPHICS VIEW  =================== */
QGraphicsView {
    background-color: #0d1117;
    border: none;
}

/* ============================  PLAIN TEXT / TEXT EDIT  ========== */
QPlainTextEdit, QTextEdit {
    background-color: #090e18;
    border: 1px solid #1e3d6e;
    border-radius: 5px;
    color: #c8d6ef;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 11px;
    padding: 4px 6px;
    selection-background-color: #1d3461;
    selection-color: #00d4ff;
}
QPlainTextEdit:focus, QTextEdit:focus {
    border-color: #3b82f6;
}

/* ============================  BUTTONS  ========================= */
QPushButton {
    background-color: #131c2e;
    border: 1px solid #1e3d6e;
    border-radius: 6px;
    padding: 6px 16px;
    color: #c8d6ef;
    font-weight: 500;
    min-height: 26px;
}
QPushButton:hover {
    background-color: #1a2a4a;
    border-color: #3b82f6;
    color: #e2e8f0;
}
QPushButton:pressed {
    background-color: #1d3461;
    border-color: #00d4ff;
    color: #00d4ff;
}
QPushButton:default {
    border-color: #3b82f6;
    color: #7fbbff;
}
QPushButton:disabled {
    background-color: #0d1117;
    border-color: #1e2a3a;
    color: #3d4f6e;
}

/* ============================  COMBO BOX  ======================= */
QComboBox {
    background-color: #131c2e;
    border: 1px solid #1e3d6e;
    border-radius: 6px;
    padding: 5px 10px;
    color: #c8d6ef;
    min-height: 26px;
    selection-background-color: #1d3461;
}
QComboBox:hover {
    border-color: #3b82f6;
}
QComboBox:focus {
    border-color: #00d4ff;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 22px;
    border-left: 1px solid #1e3d6e;
    border-radius: 0 6px 6px 0;
    background: #0f151e;
}
QComboBox QAbstractItemView {
    background-color: #131c2e;
    border: 1px solid #1e3d6e;
    border-radius: 4px;
    selection-background-color: #1d3461;
    selection-color: #00d4ff;
    outline: 0;
    padding: 2px;
}

/* ============================  LINE EDIT / SPIN BOX  ============ */
QLineEdit {
    background-color: #131c2e;
    border: 1px solid #1e3d6e;
    border-radius: 6px;
    padding: 5px 10px;
    color: #c8d6ef;
    min-height: 26px;
    selection-background-color: #1d3461;
    selection-color: #00d4ff;
}
QLineEdit:hover {
    border-color: #3b82f6;
}
QLineEdit:focus {
    border-color: #00d4ff;
    background-color: #0f1829;
}
QDoubleSpinBox, QSpinBox {
    background-color: #131c2e;
    border: 1px solid #1e3d6e;
    border-radius: 6px;
    padding: 5px 10px;
    color: #c8d6ef;
    min-height: 26px;
}
QDoubleSpinBox:hover, QSpinBox:hover {
    border-color: #3b82f6;
}
QDoubleSpinBox:focus, QSpinBox:focus {
    border-color: #00d4ff;
}
QDoubleSpinBox::up-button, QSpinBox::up-button,
QDoubleSpinBox::down-button, QSpinBox::down-button {
    background: #0f151e;
    border: none;
    width: 14px;
}

/* ============================  LIST / TREE / TABLE  ============= */
QListWidget, QTreeWidget, QTableWidget {
    background-color: #090e18;
    border: 1px solid #1e3d6e;
    border-radius: 5px;
    outline: 0;
    color: #c8d6ef;
    alternate-background-color: #0d1622;
}
QListWidget::item, QTreeWidget::item {
    padding: 5px 8px;
    border-radius: 4px;
    margin: 1px 2px;
}
QListWidget::item:selected,
QTreeWidget::item:selected {
    background-color: #1d3461;
    color: #00d4ff;
}
QListWidget::item:hover,
QTreeWidget::item:hover {
    background-color: #131c2e;
}
QHeaderView::section {
    background-color: #0f151e;
    border: none;
    border-right: 1px solid #1e3d6e;
    border-bottom: 1px solid #1e3d6e;
    padding: 5px 10px;
    color: #64748b;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}

/* ============================  PROGRESS BAR  ==================== */
QProgressBar {
    background-color: #131c2e;
    border: 1px solid #1e3d6e;
    border-radius: 5px;
    height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #1d3461, stop:0.5 #3b82f6, stop:1 #00d4ff
    );
    border-radius: 5px;
}

/* ============================  CHECK BOX / RADIO  =============== */
QCheckBox {
    color: #c8d6ef;
    spacing: 7px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #1e3d6e;
    border-radius: 4px;
    background: #131c2e;
}
QCheckBox::indicator:hover {
    border-color: #3b82f6;
}
QCheckBox::indicator:checked {
    background-color: #3b82f6;
    border-color: #3b82f6;
}
QRadioButton {
    color: #c8d6ef;
    spacing: 7px;
}
QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #1e3d6e;
    border-radius: 7px;
    background: #131c2e;
}
QRadioButton::indicator:checked {
    background-color: #3b82f6;
    border-color: #00d4ff;
}

/* ============================  GROUP BOX  ======================= */
QGroupBox {
    border: 1px solid #1e3d6e;
    border-radius: 7px;
    margin-top: 10px;
    padding: 10px 6px 6px 6px;
    color: #4a6fa8;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    background-color: #0d1117;
    color: #4a6fa8;
}

/* ============================  TAB WIDGET  ====================== */
QTabWidget::pane {
    border: 1px solid #1e3d6e;
    border-radius: 6px;
    background-color: #131c2e;
    top: -1px;
}
QTabBar::tab {
    background-color: #0d1117;
    border: 1px solid #1e3d6e;
    border-bottom: none;
    padding: 7px 16px;
    color: #4a6fa8;
    border-radius: 6px 6px 0 0;
    margin-right: 2px;
    font-size: 11px;
}
QTabBar::tab:selected {
    background-color: #131c2e;
    color: #00d4ff;
    border-color: #3b82f6;
}
QTabBar::tab:hover:!selected {
    background-color: #131c2e;
    color: #7fbbff;
}

/* ============================  LABEL  =========================== */
QLabel {
    color: #94a3b8;
    background: transparent;
}

/* ============================  TOOLTIP  ========================= */
QToolTip {
    background-color: #131c2e;
    border: 1px solid #3b82f6;
    color: #e2e8f0;
    padding: 5px 10px;
    border-radius: 5px;
    font-size: 11px;
}

/* ============================  SPLITTER  ======================== */
QSplitter::handle {
    background-color: #1e3d6e;
    border-radius: 2px;
}
QSplitter::handle:hover {
    background-color: #3b82f6;
}
QSplitter::handle:horizontal {
    width: 3px;
}
QSplitter::handle:vertical {
    height: 3px;
}

/* ============================  FRAME  =========================== */
QFrame[frameShape="4"],  /* HLine */
QFrame[frameShape="5"] { /* VLine */
    color: #1e3d6e;
}

/* ============================  RUBBER BAND  ===================== */
QRubberBand {
    border: 1px solid #00d4ff;
    background-color: rgba(0, 212, 255, 25);
}

/* ============================  DIALOG BUTTON BOX  =============== */
QDialogButtonBox QPushButton {
    min-width: 80px;
}
"""

# ── Additional built-in stylesheets ──────────────────────────────────────────

_STYLESHEET_LIGHT = """
QWidget {
    background-color: #f0f4f8;
    color: #1e293b;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 12px;
    selection-background-color: #bfdbfe;
    selection-color: #1e40af;
}
QMainWindow, QDialog { background-color: #f0f4f8; }
QMenuBar {
    background-color: #e2e8f0;
    border-bottom: 1px solid #cbd5e1;
    padding: 2px 4px;
}
QMenuBar::item { padding: 5px 12px; border-radius: 4px; background: transparent; color: #475569; }
QMenuBar::item:selected { background-color: #bfdbfe; color: #1e40af; }
QMenu {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 4px 2px;
}
QMenu::item { padding: 6px 28px 6px 14px; border-radius: 4px; margin: 1px 3px; color: #1e293b; }
QMenu::item:selected { background-color: #bfdbfe; color: #1e40af; }
QMenu::item:disabled { color: #94a3b8; }
QMenu::separator { height: 1px; background: #e2e8f0; margin: 4px 10px; }
QToolBar {
    background-color: #e2e8f0;
    border-bottom: 1px solid #cbd5e1;
    spacing: 4px;
    padding: 3px 8px;
}
QToolBar QLabel { color: #64748b; font-size: 11px; }
QToolBar::separator { width: 1px; background: #cbd5e1; margin: 4px 3px; }
QDockWidget { font-size: 11px; font-weight: 600; color: #64748b; }
QDockWidget::title {
    background-color: #e2e8f0;
    padding: 6px 10px;
    border-bottom: 1px solid #cbd5e1;
}
QStatusBar { background-color: #e2e8f0; border-top: 1px solid #cbd5e1; color: #64748b; font-size: 11px; }
QScrollBar:vertical { background: #f1f5f9; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #94a3b8; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #3b82f6; }
QScrollBar:horizontal { background: #f1f5f9; height: 8px; border-radius: 4px; }
QScrollBar::handle:horizontal { background: #94a3b8; border-radius: 4px; min-width: 28px; }
QScrollBar::handle:horizontal:hover { background: #3b82f6; }
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page { width:0; height:0; background:none; }
QGraphicsView { background-color: #dce5ef; border: none; }
QPlainTextEdit, QTextEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    color: #1e293b;
    font-family: "Cascadia Code", Consolas, monospace;
    font-size: 11px;
    padding: 4px 6px;
}
QPlainTextEdit:focus, QTextEdit:focus { border-color: #3b82f6; }
QPushButton {
    background-color: #e2e8f0;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 16px;
    color: #1e293b;
    font-weight: 500;
    min-height: 26px;
}
QPushButton:hover { background-color: #bfdbfe; border-color: #3b82f6; color: #1e40af; }
QPushButton:pressed { background-color: #93c5fd; border-color: #2563eb; }
QPushButton:disabled { background-color: #f1f5f9; border-color: #e2e8f0; color: #94a3b8; }
QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 5px 10px;
    color: #1e293b;
    min-height: 26px;
}
QComboBox:hover { border-color: #3b82f6; }
QComboBox:focus { border-color: #2563eb; }
QComboBox::drop-down { background: #e2e8f0; border-left: 1px solid #cbd5e1; border-radius: 0 6px 6px 0; width: 22px; }
QComboBox QAbstractItemView { background-color: #ffffff; border: 1px solid #cbd5e1; selection-background-color: #bfdbfe; selection-color: #1e40af; }
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 5px 10px;
    color: #1e293b;
    min-height: 26px;
}
QLineEdit:hover { border-color: #3b82f6; }
QLineEdit:focus { border-color: #2563eb; }
QDoubleSpinBox, QSpinBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 5px 10px;
    color: #1e293b;
    min-height: 26px;
}
QDoubleSpinBox::up-button, QSpinBox::up-button, QDoubleSpinBox::down-button, QSpinBox::down-button {
    background: #e2e8f0; border: none; width: 14px;
}
QListWidget, QTreeWidget, QTableWidget {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    color: #1e293b;
    alternate-background-color: #f8fafc;
}
QListWidget::item { padding: 5px 8px; border-radius: 4px; margin: 1px 2px; }
QListWidget::item:selected { background-color: #bfdbfe; color: #1e40af; }
QListWidget::item:hover { background-color: #f1f5f9; }
QHeaderView::section {
    background-color: #e2e8f0;
    border: none;
    border-right: 1px solid #cbd5e1;
    border-bottom: 1px solid #cbd5e1;
    padding: 5px 10px;
    color: #64748b;
    font-size: 11px;
    font-weight: 600;
}
QProgressBar { background-color: #e2e8f0; border: 1px solid #cbd5e1; border-radius: 5px; height: 6px; color: transparent; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #93c5fd, stop:1 #3b82f6); border-radius: 5px; }
QCheckBox { color: #1e293b; spacing: 7px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #cbd5e1; border-radius: 4px; background: #ffffff; }
QCheckBox::indicator:checked { background-color: #3b82f6; border-color: #3b82f6; }
QGroupBox { border: 1px solid #cbd5e1; border-radius: 7px; margin-top: 10px; padding: 10px 6px 6px 6px; color: #64748b; font-size: 11px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 6px; background-color: #f0f4f8; color: #64748b; }
QTabWidget::pane { border: 1px solid #cbd5e1; border-radius: 6px; background-color: #ffffff; top: -1px; }
QTabBar::tab { background-color: #e2e8f0; border: 1px solid #cbd5e1; border-bottom: none; padding: 7px 16px; color: #64748b; border-radius: 6px 6px 0 0; margin-right: 2px; font-size: 11px; }
QTabBar::tab:selected { background-color: #ffffff; color: #1e40af; border-color: #3b82f6; }
QLabel { color: #475569; background: transparent; }
QToolTip { background-color: #ffffff; border: 1px solid #3b82f6; color: #1e293b; padding: 5px 10px; border-radius: 5px; font-size: 11px; }
QRubberBand { border: 1px solid #3b82f6; background-color: rgba(59,130,246,40); }
QDialogButtonBox QPushButton { min-width: 80px; }
"""

_STYLESHEET_SOLARIZED = """
QWidget {
    background-color: #002b36;
    color: #839496;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 12px;
    selection-background-color: #073642;
    selection-color: #2aa198;
}
QMainWindow, QDialog { background-color: #002b36; }
QMenuBar { background-color: #073642; border-bottom: 1px solid #586e75; padding: 2px 4px; }
QMenuBar::item { padding: 5px 12px; border-radius: 4px; background: transparent; color: #657b83; }
QMenuBar::item:selected { background-color: #073642; color: #2aa198; }
QMenu { background-color: #073642; border: 1px solid #586e75; border-radius: 6px; padding: 4px 2px; }
QMenu::item { padding: 6px 28px 6px 14px; border-radius: 4px; margin: 1px 3px; color: #93a1a1; }
QMenu::item:selected { background-color: #073642; color: #2aa198; }
QMenu::item:disabled { color: #586e75; }
QMenu::separator { height: 1px; background: #586e75; margin: 4px 10px; }
QToolBar { background-color: #073642; border-bottom: 1px solid #586e75; spacing: 4px; padding: 3px 8px; }
QToolBar QLabel { color: #657b83; font-size: 11px; }
QToolBar::separator { width: 1px; background: #586e75; margin: 4px 3px; }
QDockWidget { font-size: 11px; font-weight: 600; color: #586e75; }
QDockWidget::title { background-color: #073642; padding: 6px 10px; border-bottom: 1px solid #586e75; }
QStatusBar { background-color: #003847; border-top: 1px solid #586e75; color: #586e75; font-size: 11px; }
QScrollBar:vertical { background: #002b36; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #586e75; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #2aa198; }
QScrollBar:horizontal { background: #002b36; height: 8px; border-radius: 4px; }
QScrollBar::handle:horizontal { background: #586e75; border-radius: 4px; min-width: 28px; }
QScrollBar::handle:horizontal:hover { background: #2aa198; }
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page { width:0; height:0; background:none; }
QGraphicsView { background-color: #002b36; border: none; }
QPlainTextEdit, QTextEdit { background-color: #00212b; border: 1px solid #586e75; border-radius: 5px; color: #93a1a1; font-family: "Cascadia Code", Consolas, monospace; font-size: 11px; padding: 4px 6px; }
QPlainTextEdit:focus, QTextEdit:focus { border-color: #2aa198; }
QPushButton { background-color: #073642; border: 1px solid #586e75; border-radius: 6px; padding: 6px 16px; color: #93a1a1; font-weight: 500; min-height: 26px; }
QPushButton:hover { background-color: #0a4555; border-color: #2aa198; color: #eee8d5; }
QPushButton:pressed { background-color: #2aa198; border-color: #2aa198; color: #002b36; }
QPushButton:disabled { color: #586e75; }
QComboBox { background-color: #073642; border: 1px solid #586e75; border-radius: 6px; padding: 5px 10px; color: #93a1a1; min-height: 26px; }
QComboBox:hover { border-color: #2aa198; }
QComboBox:focus { border-color: #2aa198; }
QComboBox::drop-down { background: #003847; border-left: 1px solid #586e75; border-radius: 0 6px 6px 0; width: 22px; }
QComboBox QAbstractItemView { background-color: #073642; border: 1px solid #586e75; selection-background-color: #0a4555; selection-color: #2aa198; }
QLineEdit { background-color: #073642; border: 1px solid #586e75; border-radius: 6px; padding: 5px 10px; color: #93a1a1; min-height: 26px; }
QLineEdit:focus { border-color: #2aa198; }
QDoubleSpinBox, QSpinBox { background-color: #073642; border: 1px solid #586e75; border-radius: 6px; padding: 5px 10px; color: #93a1a1; min-height: 26px; }
QDoubleSpinBox::up-button, QSpinBox::up-button, QDoubleSpinBox::down-button, QSpinBox::down-button { background: #003847; border: none; width: 14px; }
QListWidget, QTreeWidget, QTableWidget { background-color: #00212b; border: 1px solid #586e75; border-radius: 5px; color: #93a1a1; alternate-background-color: #002b36; }
QListWidget::item { padding: 5px 8px; border-radius: 4px; margin: 1px 2px; }
QListWidget::item:selected { background-color: #073642; color: #2aa198; }
QListWidget::item:hover { background-color: #073642; }
QHeaderView::section { background-color: #073642; border: none; border-right: 1px solid #586e75; border-bottom: 1px solid #586e75; padding: 5px 10px; color: #586e75; font-size: 11px; font-weight: 600; }
QProgressBar { background-color: #073642; border: 1px solid #586e75; border-radius: 5px; height: 6px; color: transparent; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #073642, stop:1 #2aa198); border-radius: 5px; }
QCheckBox { color: #839496; spacing: 7px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #586e75; border-radius: 4px; background: #073642; }
QCheckBox::indicator:checked { background-color: #2aa198; border-color: #2aa198; }
QGroupBox { border: 1px solid #586e75; border-radius: 7px; margin-top: 10px; padding: 10px 6px 6px 6px; color: #586e75; font-size: 11px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 6px; background-color: #002b36; color: #586e75; }
QTabWidget::pane { border: 1px solid #586e75; border-radius: 6px; background-color: #073642; top: -1px; }
QTabBar::tab { background-color: #002b36; border: 1px solid #586e75; border-bottom: none; padding: 7px 16px; color: #586e75; border-radius: 6px 6px 0 0; margin-right: 2px; font-size: 11px; }
QTabBar::tab:selected { background-color: #073642; color: #2aa198; border-color: #2aa198; }
QLabel { color: #657b83; background: transparent; }
QToolTip { background-color: #073642; border: 1px solid #2aa198; color: #eee8d5; padding: 5px 10px; border-radius: 5px; font-size: 11px; }
QRubberBand { border: 1px solid #2aa198; background-color: rgba(42,161,152,30); }
QDialogButtonBox QPushButton { min-width: 80px; }
"""

# ── Node colour overrides per theme ──────────────────────────────────────────
_THEME_COLORS = {
    "Cyberpunk Dark": {
        "grid_bg": "#0d1117", "grid_minor": "#1c3a60", "grid_major": "#2a5a9a",
        "node_bg_top": "#141d32", "node_bg_bot": "#0b1120",
        "node_hdr_top": "#0f1e38", "node_hdr_bot": "#091529",
        "node_border": "#1e3d6e", "node_border_sel": "#00d4ff",
        "node_accent": "#1a4080", "node_accent_sel": "#00d4ff",
        "text_primary": "#e2e8f0", "text_secondary": "#94a3b8", "text_dim": "#4b5563",
        "pin_in": "#22c55e", "pin_out": "#f97316",
        "edge_normal": "#3b82f6", "edge_sel": "#00d4ff", "edge_temp": "#a855f7",
        "link_color": "#3b82f6",
    },
    "Light Classic": {
        "grid_bg": "#dce5ef", "grid_minor": "#c5d3e0", "grid_major": "#aab8c8",
        "node_bg_top": "#f0f8ff", "node_bg_bot": "#e0ecf8",
        "node_hdr_top": "#2563eb", "node_hdr_bot": "#1d4ed8",
        "node_border": "#93c5fd", "node_border_sel": "#2563eb",
        "node_accent": "#bfdbfe", "node_accent_sel": "#2563eb",
        "text_primary": "#1e293b", "text_secondary": "#475569", "text_dim": "#94a3b8",
        "pin_in": "#16a34a", "pin_out": "#ea580c",
        "edge_normal": "#2563eb", "edge_sel": "#0ea5e9", "edge_temp": "#7c3aed",
        "link_color": "#2563eb",
    },
    "Solarized Dark": {
        "grid_bg": "#002b36", "grid_minor": "#073642", "grid_major": "#0a4555",
        "node_bg_top": "#073642", "node_bg_bot": "#002b36",
        "node_hdr_top": "#0a4555", "node_hdr_bot": "#073642",
        "node_border": "#586e75", "node_border_sel": "#2aa198",
        "node_accent": "#586e75", "node_accent_sel": "#2aa198",
        "text_primary": "#eee8d5", "text_secondary": "#93a1a1", "text_dim": "#657b83",
        "pin_in": "#859900", "pin_out": "#cb4b16",
        "edge_normal": "#268bd2", "edge_sel": "#2aa198", "edge_temp": "#d33682",
        "link_color": "#268bd2",
    },
}

_THEME_STYLESHEETS = {
    "Cyberpunk Dark": STYLESHEET,
    "Light Classic": _STYLESHEET_LIGHT,
    "Solarized Dark": _STYLESHEET_SOLARIZED,
}


def _apply_colors(colors: dict):
    """Overwrite all module-level colour variables in-place."""
    import sys
    mod = sys.modules[__name__]
    mapping = {
        "GRID_BG": "grid_bg", "GRID_MINOR": "grid_minor", "GRID_MAJOR": "grid_major",
        "NODE_BG_TOP": "node_bg_top", "NODE_BG_BOT": "node_bg_bot",
        "NODE_HDR_TOP": "node_hdr_top", "NODE_HDR_BOT": "node_hdr_bot",
        "NODE_BORDER": "node_border", "NODE_BORDER_SEL": "node_border_sel",
        "NODE_ACCENT": "node_accent", "NODE_ACCENT_SEL": "node_accent_sel",
        "TEXT_PRIMARY": "text_primary", "TEXT_SECONDARY": "text_secondary",
        "TEXT_DIM": "text_dim",
        "PIN_IN": "pin_in", "PIN_OUT": "pin_out",
        "EDGE_NORMAL": "edge_normal", "EDGE_SELECTED": "edge_sel", "EDGE_TEMP": "edge_temp",
    }
    for var, key in mapping.items():
        if key in colors:
            setattr(mod, var, QColor(colors[key]))


class ThemeRegistry:
    """Registry of built-in and external themes."""

    _current: str = "Cyberpunk Dark"

    @classmethod
    def names(cls) -> list[str]:
        return list(_THEME_STYLESHEETS.keys())

    @classmethod
    def current_theme_name(cls) -> str:
        return cls._current

    @classmethod
    def apply(cls, name: str, app, scene=None):
        """Apply a built-in theme by name."""
        qss = _THEME_STYLESHEETS.get(name)
        colors = _THEME_COLORS.get(name)
        if qss is None:
            return
        app.setStyle("Fusion")
        app.setStyleSheet(qss)
        if colors:
            _apply_colors(colors)
        if scene is not None:
            from PyQt6.QtGui import QColor as _QColor
            from PyQt6.QtWidgets import QGraphicsScene
            scene.setLinkColor(_QColor(colors.get("link_color", "#3b82f6")))
            scene.update()
        cls._current = name

    @classmethod
    def load_external_qss(cls, path: str, app):
        """Load and apply an external .qss file (stylesheet only)."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                qss = f.read()
            app.setStyleSheet(qss)
            cls._current = ""
        except OSError:
            pass
