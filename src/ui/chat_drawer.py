import os
import datetime
import markdown
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextBrowser, QLineEdit, QFileDialog, QGraphicsOpacityEffect
)
from src.core.vector_store import VectorStoreManager
from src.core.searxng_client import SearxngClient
from src.core.llm_client import LLMClient
from src.workers.rag_worker import RagQueryWorker, GeneralQueryWorker
from src.workers.searxng_worker import SearxngQueryWorker

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "icons"

class FloatingChatDrawer(QFrame):
    """
    Floating Pikachu AI assistant drawer featuring:
    - Smooth Anime.js-inspired fluid slide and fade animations (QEasingCurve.OutCubic).
    - Multi-mode intelligence: Page Context RAG, Deep Web Research (SearXNG + Tavily Backup), and Agent Chat.
    - Automatic fallback to Tavily Search whenever SearXNG is unavailable.
    - Clickable citations that navigate the parent browser directly.
    """
    close_requested = Signal()
    url_navigation_requested = Signal(str)
    
    def __init__(self, parent=None, vector_store=None, searxng_client=None, llm_client=None, get_current_url_cb=None):
        super().__init__(parent)
        self.setObjectName("pikachuDrawer")
        self.vector_store = vector_store or VectorStoreManager()
        self.searxng_client = searxng_client or SearxngClient()
        self.llm_client = llm_client or LLMClient()
        self.get_current_url = get_current_url_cb

        self.current_mode = "page_rag"  # Options: "page_rag", "searxng", "general"
        self.active_animation = None

        # Setup opacity effect for smooth fade transitions
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        self._init_ui()
        self.update_search_engine_badge()

    def _get_icon(self, name: str) -> QIcon:
        icon_path = ASSETS_DIR / name
        if icon_path.exists():
            return QIcon(str(icon_path))
        return QIcon()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. Header Bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Agent Identity
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_label = QLabel("PIKACHU AI")
        title_label.setObjectName("drawerTitle")
        
        subtitle_label = QLabel("Research Agent")
        subtitle_label.setObjectName("drawerSubtitle")
        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Live Search Engine & Backup Status Badge
        self.engine_badge = QLabel("SearXNG · Tavily Ready")
        self.engine_badge.setObjectName("drawerEngineBadge")
        header_layout.addWidget(self.engine_badge)

        # Close Button
        self.btn_close = QPushButton()
        self.btn_close.setObjectName("drawerCloseBtn")
        self.btn_close.setIcon(self._get_icon("x.svg"))
        self.btn_close.setToolTip("Close Assistant")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(self.btn_close)

        layout.addLayout(header_layout)

        # 2. Mode Selector Segment Bar
        mode_frame = QFrame()
        mode_frame.setObjectName("modeSelectorFrame")
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(3, 3, 3, 3)
        mode_layout.setSpacing(4)

        self.btn_page_rag = QPushButton("Page Context")
        self.btn_page_rag.setObjectName("modeBtn")
        self.btn_page_rag.setIcon(self._get_icon("file-text.svg"))
        self.btn_page_rag.setProperty("active", "true")
        self.btn_page_rag.clicked.connect(lambda: self.set_mode("page_rag"))

        self.btn_searxng = QPushButton("Deep Research")
        self.btn_searxng.setObjectName("modeBtn")
        self.btn_searxng.setIcon(self._get_icon("globe.svg"))
        self.btn_searxng.setProperty("active", "false")
        self.btn_searxng.clicked.connect(lambda: self.set_mode("searxng"))

        self.btn_general = QPushButton("Agent Chat")
        self.btn_general.setObjectName("modeBtn")
        self.btn_general.setIcon(self._get_icon("message-square.svg"))
        self.btn_general.setProperty("active", "false")
        self.btn_general.clicked.connect(lambda: self.set_mode("general"))

        mode_layout.addWidget(self.btn_page_rag)
        mode_layout.addWidget(self.btn_searxng)
        mode_layout.addWidget(self.btn_general)
        layout.addWidget(mode_frame)

        # 3. Status & Animated Hairline Progress Bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("indexingBar")
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # 4. Chat Output Area (QTextBrowser with Clickable Source Links)
        self.chat_history = QTextBrowser()
        self.chat_history.setObjectName("chatHistory")
        self.chat_history.setOpenExternalLinks(False)
        self.chat_history.anchorClicked.connect(self._handle_link_clicked)
        self._append_system_intro()
        layout.addWidget(self.chat_history, stretch=1)

        # 5. Quick Interactive Action Pills
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(6)
        
        pill_summary = QPushButton("Summarize Page")
        pill_summary.setObjectName("quickPill")
        pill_summary.clicked.connect(lambda: self.quick_prompt("Summarize the key takeaways and core concepts of this page."))

        pill_code = QPushButton("Code Excerpts")
        pill_code.setObjectName("quickPill")
        pill_code.clicked.connect(lambda: self.quick_prompt("Extract all code examples from this page and explain how to run them."))

        pill_web = QPushButton("Web Research")
        pill_web.setObjectName("quickPill")
        pill_web.clicked.connect(lambda: self.quick_web_prompt("What are the modern 2026 best practices for FastAPI?"))

        quick_layout.addWidget(pill_summary)
        quick_layout.addWidget(pill_code)
        quick_layout.addWidget(pill_web)
        quick_layout.addStretch()
        layout.addLayout(quick_layout)

        # 6. Input Field & Send Button
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.chat_input = QLineEdit()
        self.chat_input.setObjectName("chatInput")
        self.chat_input.setPlaceholderText("Ask Pikachu about this page context...")
        self.chat_input.returnPressed.connect(self.send_query)

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setIcon(self._get_icon("send.svg"))
        self.send_btn.clicked.connect(self.send_query)

        input_layout.addWidget(self.chat_input, stretch=1)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

        # 7. Action Bar (Clear & Export)
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("actionSecondaryBtn")
        clear_btn.setIcon(self._get_icon("trash.svg"))
        clear_btn.clicked.connect(self.clear_chat)

        export_btn = QPushButton("Export Transcript")
        export_btn.setObjectName("actionSecondaryBtn")
        export_btn.setIcon(self._get_icon("download.svg"))
        export_btn.clicked.connect(self.export_conversation)

        action_layout.addWidget(clear_btn)
        action_layout.addStretch()
        action_layout.addWidget(export_btn)
        layout.addLayout(action_layout)

    def _append_system_intro(self):
        intro_html = (
            "<div style='margin-bottom: 8px;'>"
            "<span style='color: #d49b35; font-weight: 700;'>Pikachu AI</span> "
            "<span style='color: #8b949e; font-size: 11px;'>Research Assistant</span>"
            "<div style='color: #c9d1d9; margin-top: 4px; font-size: 12px;'>"
            "Ready. Ask questions about the current page, execute live multi-engine web research "
            "(SearXNG with automatic Tavily backup), or converse directly."
            "</div></div>"
        )
        self.chat_history.setHtml(intro_html)

    def _handle_link_clicked(self, qurl: QUrl):
        url_str = qurl.toString()
        if url_str.startswith(("http://", "https://")):
            self.url_navigation_requested.emit(url_str)

    def update_search_engine_badge(self):
        """Reflects current search engine health: SearXNG primary vs Tavily backup."""
        # Use fast health check
        is_searxng = self.searxng_client.check_searxng_health(timeout=0.8)
        if is_searxng:
            self.engine_badge.setText("SearXNG Active")
            self.engine_badge.setStyleSheet(
                "background-color: #111e19; color: #10b981; border: 1px solid #1f3b31; "
                "border-radius: 6px; font-size: 10px; font-weight: 700; padding: 3px 8px;"
            )
        else:
            self.engine_badge.setText("Tavily Backup Active")
            self.engine_badge.setStyleSheet(
                "background-color: #1f1b13; color: #e5aa38; border: 1px solid #3d321d; "
                "border-radius: 6px; font-size: 10px; font-weight: 700; padding: 3px 8px;"
            )

    # --- ANIME.JS INSPIRED FLUID EASING ANIMATIONS ---

    def show_animated(self, target_rect: QRect):
        """Smoothly glides the drawer upward and fades in using OutCubic easing."""
        if self.active_animation and self.active_animation.state() == QParallelAnimationGroup.Running:
            self.active_animation.stop()

        start_rect = QRect(target_rect.x(), target_rect.y() + 32, target_rect.width(), target_rect.height())
        self.setGeometry(start_rect)
        self.opacity_effect.setOpacity(0.0)
        self.show()
        self.raise_()

        group = QParallelAnimationGroup(self)

        pos_anim = QPropertyAnimation(self, b"geometry")
        pos_anim.setDuration(280)
        pos_anim.setStartValue(start_rect)
        pos_anim.setEndValue(target_rect)
        pos_anim.setEasingCurve(QEasingCurve.OutCubic)

        fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_anim.setDuration(280)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QEasingCurve.OutQuad)

        group.addAnimation(pos_anim)
        group.addAnimation(fade_anim)
        self.active_animation = group
        group.start()

        self.chat_input.setFocus()
        self.update_search_engine_badge()

    def hide_animated(self, on_finished_cb=None):
        """Smoothly slides the drawer downward and fades out using InCubic easing."""
        if self.active_animation and self.active_animation.state() == QParallelAnimationGroup.Running:
            self.active_animation.stop()

        curr_rect = self.geometry()
        end_rect = QRect(curr_rect.x(), curr_rect.y() + 24, curr_rect.width(), curr_rect.height())

        group = QParallelAnimationGroup(self)

        pos_anim = QPropertyAnimation(self, b"geometry")
        pos_anim.setDuration(220)
        pos_anim.setStartValue(curr_rect)
        pos_anim.setEndValue(end_rect)
        pos_anim.setEasingCurve(QEasingCurve.InCubic)

        fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_anim.setDuration(220)
        fade_anim.setStartValue(self.opacity_effect.opacity())
        fade_anim.setEndValue(0.0)
        fade_anim.setEasingCurve(QEasingCurve.InQuad)

        group.addAnimation(pos_anim)
        group.addAnimation(fade_anim)

        def _cleanup():
            self.hide()
            if on_finished_cb:
                on_finished_cb()

        group.finished.connect(_cleanup)
        self.active_animation = group
        group.start()

    def set_mode(self, mode: str):
        self.current_mode = mode
        self.btn_page_rag.setProperty("active", "true" if mode == "page_rag" else "false")
        self.btn_searxng.setProperty("active", "true" if mode == "searxng" else "false")
        self.btn_general.setProperty("active", "true" if mode == "general" else "false")

        # Refresh styles
        for btn in [self.btn_page_rag, self.btn_searxng, self.btn_general]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if mode == "page_rag":
            self.chat_input.setPlaceholderText("Ask Pikachu about this page context...")
        elif mode == "searxng":
            self.chat_input.setPlaceholderText("Live web search (SearXNG · Tavily backup)...")
            self.update_search_engine_badge()
        else:
            self.chat_input.setPlaceholderText("Direct assistant chat...")

    def update_indexing_progress(self, val: int):
        """Smoothly interpolates progress value with OutQuad easing."""
        self.progress_bar.show()
        prog_anim = QPropertyAnimation(self.progress_bar, b"value")
        prog_anim.setDuration(220)
        prog_anim.setStartValue(self.progress_bar.value())
        prog_anim.setEndValue(val)
        prog_anim.setEasingCurve(QEasingCurve.OutQuad)
        prog_anim.start()

    def set_status(self, text: str):
        self.status_label.setText(text)

    def on_indexing_complete(self, success: bool, msg: str):
        self.status_label.setText(msg)
        if success:
            self.progress_bar.hide()

    def quick_prompt(self, query: str):
        self.set_mode("page_rag")
        self.chat_input.setText(query)
        self.send_query()

    def quick_web_prompt(self, query: str):
        self.set_mode("searxng")
        self.chat_input.setText(query)
        self.send_query()

    def send_query(self):
        query = self.chat_input.text().strip()
        if not query:
            return

        # Render user message
        user_html = (
            "<div style='margin-top: 10px; margin-bottom: 8px;'>"
            "<span style='color: #7d8590; font-weight: 700; font-size: 11px;'>You</span>"
            f"<div style='background-color: #171b24; border: 1px solid #28303f; border-radius: 6px; padding: 8px 12px; margin-top: 4px; color: #f0f6fc; font-size: 13px;'>{query}</div>"
            "</div>"
        )
        self.chat_history.append(user_html)
        self.chat_input.clear()
        self.status_label.setText("Reasoning...")

        curr_url = self.get_current_url() if self.get_current_url else None

        if self.current_mode == "page_rag":
            self.worker = RagQueryWorker(query, self.vector_store, self.llm_client, current_url=curr_url)
        elif self.current_mode == "searxng":
            self.worker = SearxngQueryWorker(query, self.searxng_client, self.llm_client)
            self.worker.status_signal.connect(self.set_status)
            self.worker.provider_signal.connect(self._on_search_provider_used)
        else:
            self.worker = GeneralQueryWorker(query, self.llm_client)

        self.worker.answer_signal.connect(self.on_answer_received)
        self.worker.start()

    def _on_search_provider_used(self, provider: str):
        if "tavily" in provider.lower():
            self.engine_badge.setText("Tavily Backup Active")
            self.engine_badge.setStyleSheet(
                "background-color: #1f1b13; color: #e5aa38; border: 1px solid #3d321d; "
                "border-radius: 6px; font-size: 10px; font-weight: 700; padding: 3px 8px;"
            )
        else:
            self.engine_badge.setText("SearXNG Active")
            self.engine_badge.setStyleSheet(
                "background-color: #111e19; color: #10b981; border: 1px solid #1f3b31; "
                "border-radius: 6px; font-size: 10px; font-weight: 700; padding: 3px 8px;"
            )

    def on_answer_received(self, answer: str):
        self.status_label.setText("Ready")
        formatted_content = markdown.markdown(answer, extensions=['fenced_code', 'codehilite', 'tables'])
        
        agent_html = (
            "<div style='margin-top: 8px; margin-bottom: 12px;'>"
            "<span style='color: #d49b35; font-weight: 700; font-size: 11px;'>Pikachu Agent</span>"
            f"<div style='background-color: #11141c; border: 1px solid #222836; border-radius: 6px; padding: 10px 12px; margin-top: 4px; color: #e6edf3; font-size: 13px;'>{formatted_content}</div>"
            "</div>"
        )
        self.chat_history.append(agent_html)

    def clear_chat(self):
        self.chat_history.clear()
        self._append_system_intro()
        self.status_label.setText("Ready")

    def export_conversation(self):
        history_text = self.chat_history.toPlainText()
        if not history_text.strip():
            self.status_label.setText("Export failed: Empty chat")
            return

        current_url = self.get_current_url() if self.get_current_url else "N/A"
        filename = f"Pikachu_Research_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Research Transcript",
            filename,
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("=== PIKACHU AI AGENTIC BROWSER RESEARCH TRANSCRIPT ===\n")
                    f.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
                    f.write(f"Active Document: {current_url}\n")
                    f.write(f"Active Mode: {self.current_mode}\n")
                    f.write("="*60 + "\n\n")
                    f.write(history_text)
                self.status_label.setText(f"Exported to {os.path.basename(file_path)}")
            except Exception as e:
                self.status_label.setText(f"Export Error: {str(e)}")
