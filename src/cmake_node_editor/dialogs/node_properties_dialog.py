"""
Node Properties Dialog — **strategy-driven** layout.

The Build System combo populates the ``QStackedWidget`` dynamically from
the strategy registry.  Each strategy provides its own form widget via
:meth:`BuildStrategy.create_properties_form`, so adding a new build
system requires **zero changes** in this file.
"""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QWidget,
    QLabel, QLineEdit, QPlainTextEdit,
    QDialogButtonBox, QMessageBox, QComboBox, QSizePolicy,
    QGroupBox, QScrollArea, QFrame, QPushButton, QTabWidget,
)

from ..views.graphics_items import NodeItem
from ..services.build_strategies import get_strategy, STRATEGY_NAMES, STRATEGY_LABELS

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
_BG         = "#1e1e2e"
_BG_PANEL   = "#2a2a3e"
_BG_INPUT   = "#313145"
_BORDER     = "#44445a"
_ACCENT     = "#7c9ef8"
_ACCENT2    = "#56d4c8"
_TEXT       = "#cdd6f4"
_TEXT_DIM   = "#6c7086"
_TEXT_ERR   = "#f38ba8"
_RADIUS     = "6px"

_DIALOG_QSS = f"""
/* ── Dialog background ─────────────────────────────────────── */
QDialog {{
    background: {_BG};
    color: {_TEXT};
}}

/* ── Scroll area ────────────────────────────────────────────── */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
    background: {_BG_PANEL}; width: 8px; border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {_BORDER}; border-radius: 4px; min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Labels ─────────────────────────────────────────────────── */
QLabel {{ color: {_TEXT}; background: transparent; }}

/* ── Line edits ─────────────────────────────────────────────── */
QLineEdit {{
    background: {_BG_INPUT};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: {_RADIUS};
    padding: 5px 8px;
    selection-background-color: {_ACCENT};
}}
QLineEdit:focus {{
    border-color: {_ACCENT};
}}
QLineEdit:hover {{
    border-color: #5a5a76;
}}

/* ── Plain text edits ───────────────────────────────────────── */
QPlainTextEdit {{
    background: {_BG_INPUT};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: {_RADIUS};
    padding: 4px 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    selection-background-color: {_ACCENT};
}}
QPlainTextEdit:focus {{
    border-color: {_ACCENT};
}}

/* ── Combo boxes ────────────────────────────────────────────── */
QComboBox {{
    background: {_BG_INPUT};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: {_RADIUS};
    padding: 5px 8px;
    min-width: 140px;
}}
QComboBox:focus {{
    border-color: {_ACCENT};
}}
QComboBox::drop-down {{
    border: none; width: 24px;
}}
QComboBox::down-arrow {{
    width: 10px; height: 10px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid {_TEXT_DIM};
}}
QComboBox QAbstractItemView {{
    background: {_BG_PANEL};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 4px;
    selection-background-color: {_ACCENT};
    outline: none;
}}

/* ── Group boxes ────────────────────────────────────────────── */
QGroupBox {{
    background: {_BG_PANEL};
    border: 1px solid {_BORDER};
    border-radius: {_RADIUS};
    margin-top: 12px;
    padding: 8px 10px;
    font-weight: bold;
    color: {_ACCENT};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 4px;
    background: {_BG_PANEL};
}}

/* ── Buttons ────────────────────────────────────────────────── */
QPushButton {{
    background: {_BG_PANEL};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: {_RADIUS};
    padding: 6px 18px;
    font-weight: 500;
    min-width: 80px;
}}
QPushButton:hover {{
    background: #35355a;
    border-color: {_ACCENT};
}}
QPushButton:pressed {{
    background: #28283e;
}}
QPushButton[text="OK"] {{
    background: {_ACCENT};
    color: #1e1e2e;
    border-color: {_ACCENT};
    font-weight: bold;
}}
QPushButton[text="OK"]:hover {{
    background: #9db0fa;
    border-color: #9db0fa;
}}
QPushButton[text="Cancel"] {{
    background: transparent;
}}

/* ── Dialog button box ──────────────────────────────────────── */
QDialogButtonBox {{
    background: transparent;
}}
"""


def _section_header(text: str) -> QLabel:
    """Return a styled section-header label with an accent left border."""
    lbl = QLabel(text)
    font = lbl.font()
    font.setPointSize(font.pointSize() + 1)
    font.setBold(True)
    lbl.setFont(font)
    lbl.setStyleSheet(
        f"color: {_ACCENT};"
        f"border-left: 3px solid {_ACCENT2};"
        f"padding-left: 8px;"
        f"background: transparent;"
    )
    return lbl


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {_BORDER}; background: {_BORDER}; border: none; max-height: 1px;")
    return line




class NodePropertiesDialog(QDialog):
    """Modal dialog for editing a single :class:`NodeItem`'s properties."""

    def __init__(self, node_item: NodeItem, parent=None):
        super().__init__(parent)
        self.node_item = node_item
        self.setWindowTitle(f"Node Properties — {node_item.title()}")
        self.resize(720, 680)
        self.setMinimumWidth(620)
        self.setStyleSheet(_DIALOG_QSS)

        # maps strategy name → form widget
        self._form_map: dict[str, QWidget] = {}
        self._current_strategy_form: QWidget | None = None

        self._buildUI()
        self.loadFromNode(node_item)
        QTimer.singleShot(0, self._fitToContent)

    # ------------------------------------------------------------------
    def _buildUI(self):
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # ── Title bar strip ──────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setFixedHeight(48)
        title_bar.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f"  stop:0 #2b2d4a, stop:1 {_BG});"
            f"border-bottom: 1px solid {_BORDER};"
        )
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(16, 0, 16, 0)
        tb_title = QLabel("Node Properties")
        tb_title.setStyleSheet(
            f"color: {_TEXT}; font-size: 14px; font-weight: bold;"
            f" background: transparent; border: none;"
        )
        self._subtitle_lbl = QLabel()
        self._subtitle_lbl.setStyleSheet(
            f"color: {_ACCENT}; font-size: 14px; background: transparent; border: none;"
        )
        tb_layout.addWidget(tb_title)
        tb_layout.addWidget(QLabel("—", styleSheet=f"color:{_BORDER};background:transparent;border:none;"))
        tb_layout.addWidget(self._subtitle_lbl)
        tb_layout.addStretch()
        root_layout.addWidget(title_bar)

        # ── Scrollable body ──────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        inner.setStyleSheet(f"background: {_BG};")
        layout = QVBoxLayout(inner)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)
        scroll.setWidget(inner)
        root_layout.addWidget(scroll, 1)
        self._scroll = scroll
        self._scroll_inner = inner

        # ── Section: Identity ────────────────────────────────────────
        layout.addWidget(_section_header("Identity"))
        id_card = QGroupBox()
        id_card.setTitle("")
        id_form = QFormLayout(id_card)
        id_form.setSpacing(8)
        id_form.setContentsMargins(10, 10, 10, 10)
        id_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.edit_node_name = QLineEdit()
        self.edit_node_name.setPlaceholderText("Unique node name…")
        id_form.addRow("Node Name:", self.edit_node_name)
        self.edit_node_project_path = QLineEdit()
        self.edit_node_project_path.setPlaceholderText("Absolute or relative path to project root")
        id_form.addRow("Project Path:", self.edit_node_project_path)
        self.combo_build_system = QComboBox()
        for name in STRATEGY_NAMES:
            self.combo_build_system.addItem(STRATEGY_LABELS[name], name)
        self.combo_build_system.currentIndexChanged.connect(self._onBuildSystemChanged)
        id_form.addRow("Build System:", self.combo_build_system)
        layout.addWidget(id_card)

        # ── Tab widget: Build Strategy / Scripts ─────────────────────
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background: {_BG_PANEL};
                border: 1px solid {_BORDER};
                border-radius: {_RADIUS};
                border-top-left-radius: 0;
            }}
            QTabBar::tab {{
                background: {_BG};
                color: {_TEXT_DIM};
                border: 1px solid {_BORDER};
                border-bottom: none;
                border-top-left-radius: {_RADIUS};
                border-top-right-radius: {_RADIUS};
                padding: 6px 18px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {_BG_PANEL};
                color: {_TEXT};
                border-bottom: 1px solid {_BG_PANEL};
            }}
            QTabBar::tab:hover:!selected {{
                background: #2e2e44;
                color: {_TEXT};
            }}
        """)

        # ── Tab 0: Build Strategy ────────────────────────────────────
        tab_strategy = QWidget()
        tab_strategy.setStyleSheet("background: transparent;")
        ts_layout = QVBoxLayout(tab_strategy)
        ts_layout.setContentsMargins(8, 8, 8, 8)
        ts_layout.setSpacing(0)

        # Container that holds exactly one strategy form at a time.
        # Swapping is done by removeWidget + addWidget so Qt always sees
        # the true content size — no QStackedWidget sizing quirks.
        self._strategy_host = QWidget()
        self._strategy_host.setStyleSheet("background: transparent;")
        self._strategy_host_layout = QVBoxLayout(self._strategy_host)
        self._strategy_host_layout.setContentsMargins(0, 0, 0, 0)
        self._strategy_host_layout.setSpacing(1)

        for name in STRATEGY_NAMES:
            strategy = get_strategy(name)
            form = strategy.create_properties_form()
            form.setStyleSheet("background: transparent;")
            self._form_map[name] = form

        # Show the first strategy form initially
        first_form = self._form_map[STRATEGY_NAMES[0]]
        self._strategy_host_layout.addWidget(first_form)
        self._current_strategy_form = first_form

        ts_layout.addWidget(self._strategy_host)
        tabs.addTab(tab_strategy, "Build Strategy")

        # ── Tab 1: Scripts ───────────────────────────────────────────
        tab_scripts = QWidget()
        tab_scripts.setStyleSheet("background: transparent;")
        sc_layout = QVBoxLayout(tab_scripts)
        sc_layout.setContentsMargins(12, 12, 12, 12)
        sc_layout.setSpacing(10)

        pre_hdr = QLabel("Pre-Build  <span style='color:%s;font-family:monospace;font-size:11px;'>py_code_before_build</span>" % _TEXT_DIM)
        pre_hdr.setTextFormat(Qt.TextFormat.RichText)
        pre_hdr.setStyleSheet(f"color: {_TEXT}; background: transparent;")
        sc_layout.addWidget(pre_hdr)
        self.edit_py_before = QPlainTextEdit()
        self.edit_py_before.setMinimumHeight(100)
        self.edit_py_before.setPlaceholderText("# Python code executed before the build step…")
        sc_layout.addWidget(self.edit_py_before)

        post_hdr = QLabel("Post-Install  <span style='color:%s;font-family:monospace;font-size:11px;'>py_code_after_install</span>" % _TEXT_DIM)
        post_hdr.setTextFormat(Qt.TextFormat.RichText)
        post_hdr.setStyleSheet(f"color: {_TEXT}; background: transparent;")
        sc_layout.addWidget(post_hdr)
        self.edit_py_after = QPlainTextEdit()
        self.edit_py_after.setMinimumHeight(100)
        self.edit_py_after.setPlaceholderText("# Python code executed after the install step…")
        sc_layout.addWidget(self.edit_py_after)
        sc_layout.addStretch(0)
        tabs.addTab(tab_scripts, "Scripts")

        tabs.setCurrentIndex(0)
        layout.addWidget(tabs)
        layout.addStretch(0)

        # ── Button bar (outside scroll) ───────────────────────────────
        btn_bar = QWidget()
        btn_bar.setStyleSheet(
            f"background: {_BG_PANEL}; border-top: 1px solid {_BORDER};"
        )
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(16, 10, 16, 10)
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_ok = QPushButton("OK")
        btn_ok.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._onAccept)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addSpacing(8)
        btn_layout.addWidget(btn_ok)
        root_layout.addWidget(btn_bar)

    # ------------------------------------------------------------------
    # Auto-fit height
    # ------------------------------------------------------------------

    def _fitToContent(self):
        """Resize dialog height to fit all content; capped at available screen height."""
        inner_h = self._scroll_inner.sizeHint().height()

        # Sum heights of non-scroll widgets in the root layout (title bar + button bar)
        root = self.layout()
        chrome_h = root.contentsMargins().top() + root.contentsMargins().bottom()
        for i in range(root.count()):
            item = root.itemAt(i)
            w = item.widget() if item else None
            if w and w is not self._scroll:
                chrome_h += w.sizeHint().height()

        ideal_h = inner_h + chrome_h + 40

        screen = self.screen()
        max_h = (screen.availableGeometry().height() - 40) if screen else 960
        new_h = min(ideal_h, max_h)

        self.resize(self.width(), new_h)

        # Re-center after resize
        if screen:
            avail = screen.availableGeometry()
            self.move(
                avail.x() + (avail.width()  - self.width())  // 2,
                avail.y() + (avail.height() - new_h) // 2,
            )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _onBuildSystemChanged(self, _index: int):
        bs_name = self.combo_build_system.currentData()
        if bs_name not in self._form_map:
            return
        new_form = self._form_map[bs_name]
        if new_form is self._current_strategy_form:
            return
        if self._current_strategy_form is not None:
            self._strategy_host_layout.removeWidget(self._current_strategy_form)
            self._current_strategy_form.setParent(None)  # detach; _form_map keeps it alive
        self._strategy_host_layout.addWidget(new_form)
        self._current_strategy_form = new_form

    def _onAccept(self):
        form = self._currentForm()
        if hasattr(form, "validate"):
            err = form.validate()
            if err:
                QMessageBox.warning(self, "Validation Error", err)
                return
        self.accept()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _currentBuildSystem(self) -> str:
        return self.combo_build_system.currentData()

    def _currentForm(self) -> QWidget:
        return self._form_map[self._currentBuildSystem()]

    # ------------------------------------------------------------------
    def loadFromNode(self, node: NodeItem):
        self.edit_node_name.setText(node.title())
        self._subtitle_lbl.setText(node.title())
        self.edit_node_project_path.setText(node.projectPath())

        # Build system combo
        bs_key = node.buildSystem()
        for i in range(self.combo_build_system.count()):
            if self.combo_build_system.itemData(i) == bs_key:
                self.combo_build_system.setCurrentIndex(i)
                break

        # Load ALL forms so switching build system keeps data intact
        for name, form in self._form_map.items():
            if hasattr(form, "load_from_node"):
                form.load_from_node(node)

        self.edit_py_before.setPlainText(node.codeBeforeBuild())
        self.edit_py_after.setPlainText(node.codeAfterInstall())

    # ------------------------------------------------------------------
    def applyToNode(self) -> bool:
        node = self.node_item

        new_title = self.edit_node_name.text().strip()
        if not new_title:
            new_title = f"Node_{node.id()}"
        elif any(n.title() == new_title and n != node for n in node.scene().nodes):
            QMessageBox.warning(self, "Warning", f"Node name '{new_title}' already exists.")
            return False

        node.updateTitle(new_title)
        node.setProjectPath(self.edit_node_project_path.text().strip())
        node.setBuildSystem(self._currentBuildSystem())

        # Delegate to the active strategy form
        form = self._currentForm()
        if hasattr(form, "apply_to_node"):
            form.apply_to_node(node)

        node.setCodeBeforeBuild(self.edit_py_before.toPlainText())
        node.setCodeAfterInstall(self.edit_py_after.toPlainText())
        return True
