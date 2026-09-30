# src/ui/styles.py

DARK_THEME_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #11111b;
    color: #cdd6f4;
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
}

/* --- TOOLBAR & NAVIGATION BAR --- */
QToolBar {
    background-color: #181825;
    border-bottom: 1px solid #313244;
    spacing: 8px;
    padding: 6px 12px;
}

QLineEdit#urlBar {
    background-color: #1e1e2e;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 7px 14px;
    color: #f5e0dc;
    font-size: 13px;
    selection-background-color: #89b4fa;
}

QLineEdit#urlBar:focus {
    border: 1px solid #89b4fa;
    background-color: #181825;
}

QPushButton#navBtn {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    color: #cdd6f4;
    font-weight: bold;
    padding: 6px 12px;
}

QPushButton#navBtn:hover {
    background-color: #45475a;
    color: #ffffff;
}

QPushButton#pikachuToggleBtn {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f9e2af, stop:1 #fab387);
    color: #11111b;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    font-size: 13px;
    padding: 7px 16px;
}

QPushButton#pikachuToggleBtn:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f5e0dc, stop:1 #f9e2af);
}

/* --- FLOATING PIKACHU AI DRAWER --- */
QFrame#pikachuDrawer {
    background-color: rgba(24, 24, 37, 0.95);
    border: 1px solid #45475a;
    border-radius: 14px;
    color: #cdd6f4;
}

QPushButton#drawerCloseBtn {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    color: #a6adc8;
    font-size: 13px;
    font-weight: bold;
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
    padding: 0px;
}

QPushButton#drawerCloseBtn:hover {
    background-color: #f38ba8;
    color: #11111b;
}

/* Mode Selector Tab Buttons */
QPushButton#modeBtn {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 6px;
    color: #a6adc8;
    font-size: 11px;
    font-weight: bold;
    padding: 5px 10px;
}

QPushButton#modeBtn:hover {
    background-color: #313244;
    color: #cdd6f4;
}

QPushButton#modeBtn[active="true"] {
    background-color: #89b4fa;
    border: 1px solid #89b4fa;
    color: #11111b;
}

/* Status & Progress Bar */
QLabel#statusLabel {
    color: #a6adc8;
    font-size: 11px;
}

QProgressBar#indexingBar {
    border: 1px solid #313244;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
    font-size: 10px;
    background-color: #1e1e2e;
    max-height: 8px;
}

QProgressBar#indexingBar::chunk {
    background-color: #a6e3a1;
    border-radius: 3px;
}

/* Chat History Display */
QTextEdit#chatHistory {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
    color: #cdd6f4;
    padding: 8px;
    font-size: 13px;
    line-height: 1.4;
}

/* Chat Input Field */
QLineEdit#chatInput {
    background-color: #1e1e2e;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
    font-size: 13px;
}

QLineEdit#chatInput:focus {
    border: 1px solid #89b4fa;
}

/* Send & Action Buttons */
QPushButton#sendBtn {
    background-color: #89b4fa;
    color: #11111b;
    border-radius: 8px;
    font-weight: bold;
    padding: 8px 16px;
}

QPushButton#sendBtn:hover {
    background-color: #b4befe;
}

QPushButton#exportBtn {
    background-color: #313244;
    color: #f38ba8;
    border: 1px solid #f38ba8;
    border-radius: 6px;
    font-weight: bold;
    font-size: 11px;
    padding: 4px 10px;
}

QPushButton#exportBtn:hover {
    background-color: #f38ba8;
    color: #11111b;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #181825;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #45475a;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #585b70;
}
"""
