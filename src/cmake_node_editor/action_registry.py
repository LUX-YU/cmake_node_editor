"""
Action registry — declarative menu and shortcut management.

Instead of hard-coding menu items inside ``_initMenu()``, each feature
registers its actions via :meth:`ActionRegistry.register`.  The registry
then materialises them into a ``QMenuBar`` and (optionally) into a
context menu.  New features only need to call ``register()`` — the main
window never needs editing.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QMenuBar, QMenu, QWidget


class ActionDef:
    """Lightweight descriptor for a registered action."""

    __slots__ = ("action_id", "text", "menu_path", "callback",
                 "shortcut", "enabled", "checkable", "checked",
                 "context_menu", "context_filter", "order")

    def __init__(
        self,
        action_id: str,
        text: str,
        menu_path: str,
        callback: Callable,
        shortcut: QKeySequence | QKeySequence.StandardKey | str | None = None,
        enabled: bool = True,
        checkable: bool = False,
        checked: bool = False,
        context_menu: bool = False,
        context_filter: str = "",      # "node" | "canvas" | ""
        order: int = 100,
    ):
        self.action_id = action_id
        self.text = text
        self.menu_path = menu_path
        self.callback = callback
        self.shortcut = shortcut
        self.enabled = enabled
        self.checkable = checkable
        self.checked = checked
        self.context_menu = context_menu
        self.context_filter = context_filter
        self.order = order


class ActionRegistry:
    """
    Central store of all application actions.

    Usage::

        reg = ActionRegistry()
        reg.register("file.save", "Save", "File", callback=..., shortcut=QKeySequence.StandardKey.Save)
        reg.register("file.save_as", "Save As...", "File", callback=..., order=110)
        ...
        reg.build_menubar(menubar, parent_widget)
    """

    SEPARATOR = "---"  # pseudo action_id for separators

    def __init__(self):
        self._defs: dict[str, ActionDef] = {}
        self._actions: dict[str, QAction] = {}
        self._separator_counter = 0

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        action_id: str,
        text: str,
        menu_path: str,
        callback: Callable,
        *,
        shortcut: QKeySequence | QKeySequence.StandardKey | str | None = None,
        enabled: bool = True,
        checkable: bool = False,
        checked: bool = False,
        context_menu: bool = False,
        context_filter: str = "",
        order: int = 100,
    ) -> None:
        self._defs[action_id] = ActionDef(
            action_id=action_id,
            text=text,
            menu_path=menu_path,
            callback=callback,
            shortcut=shortcut,
            enabled=enabled,
            checkable=checkable,
            checked=checked,
            context_menu=context_menu,
            context_filter=context_filter,
            order=order,
        )

    def add_separator(self, menu_path: str, *, order: int = 100) -> None:
        """Insert a visual separator at the given *order* in *menu_path*."""
        self._separator_counter += 1
        sep_id = f"{self.SEPARATOR}.{self._separator_counter}"
        self._defs[sep_id] = ActionDef(
            action_id=sep_id,
            text="",
            menu_path=menu_path,
            callback=lambda: None,
            order=order,
        )

    # ------------------------------------------------------------------
    # QAction accessor
    # ------------------------------------------------------------------

    def get(self, action_id: str) -> QAction | None:
        """Return the live :class:`QAction` for *action_id*, or ``None``."""
        return self._actions.get(action_id)

    def set_enabled(self, action_id: str, enabled: bool) -> None:
        act = self._actions.get(action_id)
        if act:
            act.setEnabled(enabled)

    def set_checked(self, action_id: str, checked: bool) -> None:
        act = self._actions.get(action_id)
        if act:
            act.setChecked(checked)

    # ------------------------------------------------------------------
    # Build the menu bar
    # ------------------------------------------------------------------

    def build_menubar(self, menubar: QMenuBar, parent: QWidget | None = None) -> None:
        """
        Populate *menubar* from all registered actions, grouped by
        ``menu_path`` and sorted by ``order``.
        """
        grouped: dict[str, list[ActionDef]] = defaultdict(list)
        for d in self._defs.values():
            grouped[d.menu_path].append(d)

        # Stable-sort each group by order, then by registration order
        menu_order = list(dict.fromkeys(d.menu_path for d in self._defs.values()))

        for menu_name in menu_order:
            menu = menubar.addMenu(menu_name)
            items = sorted(grouped[menu_name], key=lambda d: d.order)
            for d in items:
                if d.action_id.startswith(self.SEPARATOR):
                    menu.addSeparator()
                    continue
                act = QAction(d.text, parent)
                if d.shortcut is not None:
                    act.setShortcut(QKeySequence(d.shortcut) if isinstance(d.shortcut, str) else d.shortcut)
                act.setEnabled(d.enabled)
                if d.checkable:
                    act.setCheckable(True)
                    act.setChecked(d.checked)
                act.triggered.connect(d.callback)
                menu.addAction(act)
                self._actions[d.action_id] = act

    # ------------------------------------------------------------------
    # Context menu builder
    # ------------------------------------------------------------------

    def build_context_menu(
        self,
        parent: QWidget,
        filter_tag: str = "",
    ) -> QMenu:
        """
        Build a :class:`QMenu` from actions whose ``context_menu`` flag is
        *True* and whose ``context_filter`` matches *filter_tag* (or is empty).
        """
        menu = QMenu(parent)
        candidates = [
            d for d in self._defs.values()
            if d.context_menu
            and (not d.context_filter or d.context_filter == filter_tag)
            and not d.action_id.startswith(self.SEPARATOR)
        ]
        candidates.sort(key=lambda d: d.order)

        last_was_sep = True
        for d in candidates:
            # Reuse live QAction if available so enabled/checked state is current
            act = self._actions.get(d.action_id)
            if act is None:
                act = QAction(d.text, parent)
                act.triggered.connect(d.callback)
            menu.addAction(act)
            last_was_sep = False

        return menu
