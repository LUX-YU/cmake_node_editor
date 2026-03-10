# main.py

import sys
import multiprocessing
from PyQt6.QtWidgets import QApplication
from .node_editor_window import NodeEditorWindow
from .theme import STYLESHEET

def main():
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass  # already set

    app = QApplication(sys.argv)
    app.setStyle("Fusion")          # consistent cross-platform baseline
    app.setStyleSheet(STYLESHEET)
    window = NodeEditorWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
    