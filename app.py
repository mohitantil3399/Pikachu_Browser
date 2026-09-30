import sys
import os
from PySide6.QtWidgets import QApplication
from src.ui.main_window import AgenticDocBrowser

def main():
    # Set high DPI scaling policies for PySide6
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setApplicationName("Pikachu AI - Agentic Web Browser")
    
    window = AgenticDocBrowser()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
