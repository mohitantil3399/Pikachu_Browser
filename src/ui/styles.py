# src/ui/styles.py
"""
Bespoke Design System for Pikachu AI Agentic Browser.
Strictly complies with basictoadv.md standards:
- Atmospheric dark slate / obsidian foundation (no generic AI purple or harsh neon).
- Pikachu signature warm golden amber (#d49b35) accent with editorial restraint.
- Crisp 1px geometric borders without dirty drop shadows.
- Refined typography hierarchy with balanced tracking and padding.
"""

DARK_THEME_STYLESHEET = """
/* --- GLOBAL CANVAS & BASE SURFACES --- */
QMainWindow, QWidget#centralWidget {
    background-color: #0c0d12;
    color: #e6edf3;
    font-family: 'Segoe UI', 'Inter', -apple-system, system-ui, sans-serif;
    font-size: 13px;
}

/* --- BROWSER NAVIGATION TOOLBAR --- */
QToolBar#navToolbar {
    background-color: #12151c;
    border-bottom: 1px solid #222733;
    spacing: 8px;
    padding: 7px 14px;
}

/* Navigation Buttons (Back, Forward, Reload, Home) */
QPushButton#navBtn {
    background-color: #181c25;
    border: 1px solid #282f3d;
    border-radius: 7px;
    color: #c9d1d9;
    font-weight: 500;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0px;
}

QPushButton#navBtn:hover {
    background-color: #222836;
    border: 1px solid #3b465b;
    color: #ffffff;
}

QPushButton#navBtn:pressed {
    background-color: #141720;
    border: 1px solid #222836;
}

/* URL & Address Bar */
QLineEdit#urlBar {
    background-color: #161922;
    border: 1px solid #282f3d;
    border-radius: 8px;
    padding: 7px 14px;
    color: #f0f6fc;
    font-family: 'Segoe UI', 'Inter', monospace;
    font-size: 13px;
    selection-background-color: #d49b35;
    selection-color: #0c0d12;
}

QLineEdit#urlBar:focus {
    border: 1px solid #3b82f6;
    background-color: #191d27;
}

/* Dedicated Web Search Input Box */
QLineEdit#webSearchBox {
    background-color: #161922;
    border: 1px solid #282f3d;
    border-radius: 8px;
    padding: 7px 12px;
    color: #f0f6fc;
    font-size: 13px;
    min-width: 200px;
    max-width: 320px;
    selection-background-color: #d49b35;
    selection-color: #0c0d12;
}

QLineEdit#webSearchBox:focus {
    border: 1px solid #d49b35;
    background-color: #191d27;
}


/* Pikachu AI Assistant Toggle Button */
QPushButton#pikachuToggleBtn {
    background-color: #d49b35;
    color: #0c0d12;
    border: 1px solid #e5ad45;
    border-radius: 8px;
    font-weight: 700;
    font-size: 13px;
    padding: 7px 16px;
    letter-spacing: 0.3px;
}

QPushButton#pikachuToggleBtn:hover {
    background-color: #e0a73e;
    border: 1px solid #f0bc55;
}

QPushButton#pikachuToggleBtn:pressed {
    background-color: #bf8928;
}

/* --- FLOATING PIKACHU AI DRAWER --- */
QFrame#pikachuDrawer {
    background-color: #13161f;
    border: 1px solid #282e3c;
    border-radius: 12px;
    color: #e6edf3;
}

/* Drawer Header Elements */
QLabel#drawerTitle {
    color: #f0f6fc;
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.4px;
}

QLabel#drawerSubtitle {
    color: #8b949e;
    font-size: 11px;
    font-weight: 500;
}


QPushButton#drawerCloseBtn {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: #8b949e;
    font-size: 13px;
    font-weight: bold;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
}

QPushButton#drawerCloseBtn:hover {
    background-color: #222734;
    border: 1px solid #333a4d;
    color: #ffffff;
}

/* Mode Selector Segment Tabs */
QFrame#modeSelectorFrame {
    background-color: #10121a;
    border: 1px solid #222734;
    border-radius: 8px;
    padding: 3px;
}

QPushButton#modeBtn {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: #8b949e;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 10px;
}

QPushButton#modeBtn:hover {
    background-color: #191d27;
    color: #c9d1d9;
}

QPushButton#modeBtn[active="true"] {
    background-color: #242a38;
    border: 1px solid #384357;
    color: #f0f6fc;
    font-weight: 700;
}

/* Interactive Quick Action Pills */
QPushButton#quickPill {
    background-color: #161a23;
    border: 1px solid #262c3b;
    border-radius: 12px;
    color: #8b949e;
    font-size: 11px;
    font-weight: 500;
    padding: 4px 11px;
}

QPushButton#quickPill:hover {
    background-color: #202633;
    border: 1px solid #384357;
    color: #d49b35;
}

/* Status & Animated Hairline Progress Bar */
QLabel#statusLabel {
    color: #8b949e;
    font-size: 11px;
    font-weight: 500;
}

QProgressBar#indexingBar {
    border: none;
    border-radius: 2px;
    text-align: center;
    background-color: #181c25;
    max-height: 4px;
    min-height: 4px;
}

QProgressBar#indexingBar::chunk {
    background-color: #d49b35;
    border-radius: 2px;
}

/* Chat History Display Area */
QTextBrowser#chatHistory, QTextEdit#chatHistory {
    background-color: #0e1017;
    border: 1px solid #202633;
    border-radius: 8px;
    color: #e6edf3;
    padding: 12px;
    font-size: 13px;
    line-height: 1.5;
}

/* Chat Input Field */
QLineEdit#chatInput {
    background-color: #161922;
    border: 1px solid #282f3d;
    border-radius: 8px;
    padding: 9px 14px;
    color: #ffffff;
    font-size: 13px;
}

QLineEdit#chatInput:focus {
    border: 1px solid #d49b35;
    background-color: #1a1e28;
}

/* Send & Action Buttons */
QPushButton#sendBtn {
    background-color: #d49b35;
    color: #0c0d12;
    border: 1px solid #e5ad45;
    border-radius: 8px;
    font-weight: 700;
    font-size: 12px;
    padding: 8px 16px;
    min-width: 60px;
}

QPushButton#sendBtn:hover {
    background-color: #e0a73e;
    border: 1px solid #f0bc55;
}

QPushButton#sendBtn:pressed {
    background-color: #bf8928;
}

QPushButton#actionSecondaryBtn {
    background-color: #161a23;
    border: 1px solid #272d3b;
    border-radius: 6px;
    color: #8b949e;
    font-size: 11px;
    font-weight: 600;
    padding: 5px 11px;
}

QPushButton#actionSecondaryBtn:hover {
    background-color: #212634;
    border: 1px solid #363e52;
    color: #e6edf3;
}

/* Clean Refined Scrollbars */
QScrollBar:vertical {
    background: #0e1017;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #2b3242;
    min-height: 24px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #3e485e;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
