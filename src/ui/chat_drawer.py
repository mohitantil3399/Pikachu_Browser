import os
import datetime
import markdown
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QLineEdit, QFileDialog
)
from src.core.vector_store import VectorStoreManager
from src.core.searxng_client import SearxngClient
from src.core.llm_client import LLMClient
from src.workers.rag_worker import RagQueryWorker, GeneralQueryWorker
from src.workers.searxng_worker import SearxngQueryWorker

class FloatingChatDrawer(QFrame):
    """
    Floating Pikachu AI assistant drawer with multi-mode intelligence,
    automatic cascading LLM failover, and ChromaDB vector caching.
    """
    close_requested = Signal()
    
    def __init__(self, parent=None, vector_store=None, searxng_client=None, llm_client=None, get_current_url_cb=None):
        super().__init__(parent)
        self.setObjectName("pikachuDrawer")
        self.vector_store = vector_store or VectorStoreManager()
        self.searxng_client = searxng_client or SearxngClient()
        self.llm_client = llm_client or LLMClient()
        self.get_current_url = get_current_url_cb

        self.current_mode = "page_rag"  # Options: "page_rag", "searxng", "general"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 1. Header Bar
        header_layout = QHBoxLayout()
        title_label = QLabel("⚡ Pikachu AI")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #f9e2af;")
        
        self.mode_badge = QLabel("📄 Page RAG")
        self.mode_badge.setStyleSheet("background-color: #313244; color: #a6e3a1; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;")

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("drawerCloseBtn")
        self.btn_close.setToolTip("Close Chat (✕)")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.close_requested.emit)

        header_layout.addWidget(title_label)
        header_layout.addWidget(self.mode_badge)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_close)

        layout.addLayout(header_layout)

        # 2. Mode Selector Toolbar
        mode_layout = QHBoxLayout()
        self.btn_page_rag = QPushButton("📄 Page RAG")
        self.btn_page_rag.setObjectName("modeBtn")
        self.btn_page_rag.setProperty("active", "true")
        self.btn_page_rag.clicked.connect(lambda: self.set_mode("page_rag"))

        self.btn_searxng = QPushButton("🌐 SearXNG Deep Search")
        self.btn_searxng.setObjectName("modeBtn")
        self.btn_searxng.setProperty("active", "false")
        self.btn_searxng.clicked.connect(lambda: self.set_mode("searxng"))

        self.btn_general = QPushButton("💬 General AI")
        self.btn_general.setObjectName("modeBtn")
        self.btn_general.setProperty("active", "false")
        self.btn_general.clicked.connect(lambda: self.set_mode("general"))

        mode_layout.addWidget(self.btn_page_rag)
        mode_layout.addWidget(self.btn_searxng)
        mode_layout.addWidget(self.btn_general)
        layout.addLayout(mode_layout)

        # 3. Status & Indexing Progress Bar
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("indexingBar")
        self.progress_bar.setValue(0)
        self.progress_bar.hide()

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

        # 4. Chat Output Area
        self.chat_history = QTextEdit()
        self.chat_history.setObjectName("chatHistory")
        self.chat_history.setReadOnly(True)
        self.chat_history.append("<b>⚡ Pikachu:</b> Ready! Ask questions about the current page, query live web results via SearXNG, or chat directly.<br>")
        layout.addWidget(self.chat_history, stretch=1)

        # 5. Input Field & Send Button
        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setObjectName("chatInput")
        self.chat_input.setPlaceholderText("Ask Pikachu about this page...")
        self.chat_input.returnPressed.connect(self.send_query)

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.clicked.connect(self.send_query)

        input_layout.addWidget(self.chat_input, stretch=1)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

        # 6. Action Bar (Clear & Export)
        action_layout = QHBoxLayout()
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setStyleSheet("background-color: #313244; color: #a6adc8; border-radius: 4px; font-size: 11px; padding: 4px 8px;")
        clear_btn.clicked.connect(self.clear_chat)

        export_btn = QPushButton("💾 Export (.txt)")
        export_btn.setObjectName("exportBtn")
        export_btn.clicked.connect(self.export_conversation)

        action_layout.addWidget(clear_btn)
        action_layout.addStretch()
        action_layout.addWidget(export_btn)
        layout.addLayout(action_layout)

    def set_mode(self, mode: str):
        self.current_mode = mode
        self.btn_page_rag.setProperty("active", "true" if mode == "page_rag" else "false")
        self.btn_searxng.setProperty("active", "true" if mode == "searxng" else "false")
        self.btn_general.setProperty("active", "true" if mode == "general" else "false")

        # Refresh button style states
        for btn in [self.btn_page_rag, self.btn_searxng, self.btn_general]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if mode == "page_rag":
            self.mode_badge.setText("📄 Page RAG")
            self.mode_badge.setStyleSheet("background-color: #313244; color: #a6e3a1; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
            self.chat_input.setPlaceholderText("Ask Pikachu about this page context...")
        elif mode == "searxng":
            self.mode_badge.setText("🌐 SearXNG Search")
            self.mode_badge.setStyleSheet("background-color: #313244; color: #89b4fa; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
            self.chat_input.setPlaceholderText("Search web via local SearXNG engine...")
        else:
            self.mode_badge.setText("💬 General AI")
            self.mode_badge.setStyleSheet("background-color: #313244; color: #cba6f7; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
            self.chat_input.setPlaceholderText("Ask any general question...")

    def update_indexing_progress(self, val: int):
        self.progress_bar.show()
        self.progress_bar.setValue(val)

    def set_status(self, text: str):
        self.status_label.setText(text)

    def on_indexing_complete(self, success: bool, msg: str):
        self.status_label.setText(msg)
        if success:
            self.progress_bar.hide()

    def send_query(self):
        query = self.chat_input.text().strip()
        if not query:
            return

        self.chat_history.append(f"<b style='color:#89b4fa;'>You:</b> {query}")
        self.chat_input.clear()
        self.status_label.setText("Thinking...")

        curr_url = self.get_current_url() if self.get_current_url else None

        if self.current_mode == "page_rag":
            self.worker = RagQueryWorker(query, self.vector_store, self.llm_client, current_url=curr_url)
        elif self.current_mode == "searxng":
            self.worker = SearxngQueryWorker(query, self.searxng_client, self.llm_client)
        else:
            self.worker = GeneralQueryWorker(query, self.llm_client)

        self.worker.answer_signal.connect(self.on_answer_received)
        self.worker.start()

    def on_answer_received(self, answer: str):
        self.status_label.setText("Ready")
        formatted_html = markdown.markdown(answer, extensions=['fenced_code', 'codehilite'])
        self.chat_history.append(f"<b style='color:#f9e2af;'>⚡ Pikachu:</b><br>{formatted_html}<br>")

    def clear_chat(self):
        self.chat_history.clear()
        self.chat_history.append("<b>⚡ Pikachu:</b> Conversation cleared.<br>")

    def export_conversation(self):
        history_text = self.chat_history.toPlainText()
        if not history_text.strip():
            self.status_label.setText("Export failed: Empty chat.")
            return

        current_url = self.get_current_url() if self.get_current_url else "N/A"
        filename = f"Pikachu_Session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Conversation",
            filename,
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("=== PIKACHU AI AGENTIC BROWSER CONVERSATION EXPORT ===\n")
                    f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
                    f.write(f"Source URL: {current_url}\n")
                    f.write(f"Active Mode: {self.current_mode}\n")
                    f.write("="*50 + "\n\n")
                    f.write(history_text)
                self.status_label.setText(f"Exported to {os.path.basename(file_path)}")
            except Exception as e:
                self.status_label.setText(f"Export Error: {str(e)}")
