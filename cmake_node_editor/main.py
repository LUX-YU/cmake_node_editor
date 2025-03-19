# main.py

import sys
from PyQt6.QtWidgets import QApplication
from .node_editor_window import NodeEditorWindow

def main():
    app = QApplication(sys.argv)
    window = NodeEditorWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
