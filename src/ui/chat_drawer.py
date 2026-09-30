import os
import datetime
import markdown
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QUrl
from PySide6.QtGui import QIcon, QTextCursor
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextBrowser, QLineEdit, QFileDialog, QGraphicsOpacityEffect
)
from src.core.vector_store import VectorStoreManager
from src.core.searxng_client import SearxngClient
from src.core.llm_client import LLMClient
from src.workers.specialized_worker import SpecializedQueryWorker
from src.workers.digest_worker import IntelligenceDigestWorker

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "icons"

class FloatingChatDrawer(QFrame):
    """
    Floating Pikachu AI assistant specialized exclusively for:
    1. Locality News (Regional, civic & community updates)
    2. Trading Summary of the Week (Markets, indices, crypto, commodities)
    3. Weather Update (Meteorological conditions, OpenWeatherMap telemetry)

    Core Capabilities:
    - Pre-digests all 3 domains into local ChromaDB beforehand on a separate thread.
    - Strictly verifies baseline facts against live Tavily results (top 5 sources, 250-character summary).
    - Real-time token streaming with fluid UI rendering.
    - Anime.js-inspired fluid easing transitions (QEasingCurve.OutCubic).
    - Gatekeeper enforcing only the 3 specialized domains.
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

        # Modes: "page_context", "locality_news", "trading_summary", "weather"
        self.current_mode = "page_context"
        self.active_animation = None
        self.active_query_worker = None
        self.digest_worker = None

        # Streaming state variables
        self.stream_start_pos = 0
        self.pending_sources = []

        # Setup opacity effect for smooth fade transitions
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        self._init_ui()

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

        subtitle_label = QLabel("Research & Specialized Intelligence Agent")
        subtitle_label.setObjectName("drawerSubtitle")
        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # ChromaDB Sync Button
        self.btn_sync = QPushButton("↻ Sync ChromaDB")
        self.btn_sync.setObjectName("actionSecondaryBtn")
        self.btn_sync.setToolTip("Pre-digest News, Trading & Weather into ChromaDB (separate thread)")
        self.btn_sync.setCursor(Qt.PointingHandCursor)
        self.btn_sync.clicked.connect(self.trigger_background_digest)
        header_layout.addWidget(self.btn_sync)

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

        self.btn_page = QPushButton("📄 Page Context")
        self.btn_page.setObjectName("modeBtn")
        self.btn_page.setProperty("active", "true")
        self.btn_page.clicked.connect(lambda: self.set_mode("page_context"))

        self.btn_locality = QPushButton("📍 Locality News")
        self.btn_locality.setObjectName("modeBtn")
        self.btn_locality.setProperty("active", "false")
        self.btn_locality.clicked.connect(lambda: self.set_mode("locality_news"))

        self.btn_trading = QPushButton("📈 Trading Summary")
        self.btn_trading.setObjectName("modeBtn")
        self.btn_trading.setProperty("active", "false")
        self.btn_trading.clicked.connect(lambda: self.set_mode("trading_summary"))

        self.btn_weather = QPushButton("⛅ Weather Update")
        self.btn_weather.setObjectName("modeBtn")
        self.btn_weather.setProperty("active", "false")
        self.btn_weather.clicked.connect(lambda: self.set_mode("weather"))

        mode_layout.addWidget(self.btn_page)
        mode_layout.addWidget(self.btn_locality)
        mode_layout.addWidget(self.btn_trading)
        mode_layout.addWidget(self.btn_weather)
        layout.addWidget(mode_frame)

        # 3. Status & Animated Hairline Progress Bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready · Active page indexed in ChromaDB")
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
        # Default text removed per user specification
        layout.addWidget(self.chat_history, stretch=1)

        # 5. Quick Interactive Action Pills
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(6)

        pill_page = QPushButton("📄 Summarize Page")
        pill_page.setObjectName("quickPill")
        pill_page.clicked.connect(lambda: self.quick_prompt("Provide a comprehensive summary and key takeaways of this page."))

        pill_news = QPushButton("📍 Sonipat Civic News")
        pill_news.setObjectName("quickPill")
        pill_news.clicked.connect(lambda: self.quick_prompt("What are the latest civic and regional news updates for Sonipat?"))

        pill_trading = QPushButton("📈 Weekly Trading Summary")
        pill_trading.setObjectName("quickPill")
        pill_trading.clicked.connect(lambda: self.quick_prompt("Give me the weekly trading summary for Nifty, Sensex, and global markets."))

        pill_weather = QPushButton("⛅ Live Weather Telemetry")
        pill_weather.setObjectName("quickPill")
        pill_weather.clicked.connect(lambda: self.quick_prompt("What is the current live weather and temperature forecast for Sonipat?"))

        quick_layout.addWidget(pill_page)
        quick_layout.addWidget(pill_news)
        quick_layout.addWidget(pill_trading)
        quick_layout.addWidget(pill_weather)
        quick_layout.addStretch()
        layout.addLayout(quick_layout)

        # 6. Input Field & Send Button
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.chat_input = QLineEdit()
        self.chat_input.setObjectName("chatInput")
        self.chat_input.setPlaceholderText("Ask questions or request summaries of the active page...")
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
        """No-op: default intro text removed from chat body per user request."""
        pass

    def _handle_link_clicked(self, qurl: QUrl):
        url_str = qurl.toString()
        if url_str.startswith(("http://", "https://")):
            self.url_navigation_requested.emit(url_str)

    def set_mode(self, mode: str):
        self.current_mode = mode
        self.btn_page.setProperty("active", "true" if mode == "page_context" else "false")
        self.btn_locality.setProperty("active", "true" if mode == "locality_news" else "false")
        self.btn_trading.setProperty("active", "true" if mode == "trading_summary" else "false")
        self.btn_weather.setProperty("active", "true" if mode == "weather" else "false")

        for btn in [self.btn_page, self.btn_locality, self.btn_trading, self.btn_weather]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if mode == "page_context":
            self.chat_input.setPlaceholderText("Ask questions or request summaries of the active page...")
        elif mode == "locality_news":
            self.chat_input.setPlaceholderText("Ask about regional news, civic developments in Sonipat...")
        elif mode == "trading_summary":
            self.chat_input.setPlaceholderText("Ask about this week's market recap, Nifty, Sensex, commodities...")
        else:
            self.chat_input.setPlaceholderText("Ask about live weather telemetry, temperature, forecasts...")

    def trigger_background_digest(self):
        """Launches pre-digestion pass on a dedicated background QThread."""
        if self.digest_worker and self.digest_worker.isRunning():
            self.status_label.setText("ChromaDB pre-digestion already in progress...")
            return

        self.progress_bar.setValue(5)
        self.progress_bar.show()
        self.status_label.setText("Pre-digesting News, Markets & Weather into ChromaDB (separate thread)...")

        self.digest_worker = IntelligenceDigestWorker(self.vector_store)
        self.digest_worker.status_signal.connect(self.set_status)
        self.digest_worker.progress_signal.connect(self.update_indexing_progress)
        self.digest_worker.finished_signal.connect(self.on_digest_complete)
        self.digest_worker.start()

    def on_digest_complete(self, success: bool, msg: str):
        self.status_label.setText(msg)
        self.progress_bar.hide()

    def on_indexing_complete(self, success: bool, msg: str):
        """Handler for webpage indexing completion from main window."""
        if success:
            self.progress_bar.hide()


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

    def update_indexing_progress(self, val: int):
        self.progress_bar.show()
        prog_anim = QPropertyAnimation(self.progress_bar, b"value")
        prog_anim.setDuration(200)
        prog_anim.setStartValue(self.progress_bar.value())
        prog_anim.setEndValue(val)
        prog_anim.setEasingCurve(QEasingCurve.OutQuad)
        prog_anim.start()

    def set_status(self, text: str):
        self.status_label.setText(text)

    def quick_prompt(self, query: str):
        self.chat_input.setText(query)
        self.send_query()

    def send_query(self):
        query = self.chat_input.text().strip()
        if not query:
            return

        # Render user message bubble
        user_html = (
            "<div style='margin-top: 10px; margin-bottom: 8px;'>"
            "<span style='color: #7d8590; font-weight: 700; font-size: 11px;'>You</span>"
            f"<div style='background-color: #171b24; border: 1px solid #28303f; border-radius: 6px; padding: 8px 12px; margin-top: 4px; color: #f0f6fc; font-size: 13px;'>{query}</div>"
            "</div>"
        )
        self.chat_history.append(user_html)
        self.chat_input.clear()
        self.status_label.setText("Analyzing domain scope...")

        # Setup streaming cursor in chat history
        self.chat_history.append(
            "<div style='margin-top: 8px; margin-bottom: 2px;'>"
            "<span style='color: #d49b35; font-weight: 700; font-size: 11px;'>Pikachu Agent</span> "
            "<span style='color: #7d8590; font-size: 10px;'>· Verified Intelligence Stream</span>"
            "</div>"
        )

        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.stream_start_pos = cursor.position()
        self.pending_sources = []

        # Get active document URL if available
        active_url = self.get_current_url() if callable(self.get_current_url) else None

        # Spawn specialized worker handling page context or specialized domains
        self.active_query_worker = SpecializedQueryWorker(
            query=query,
            active_tab=self.current_mode,
            current_url=active_url,
            vector_store=self.vector_store,
            searxng_client=self.searxng_client,
            llm_client=self.llm_client
        )
        self.active_query_worker.status_signal.connect(self.set_status)
        self.active_query_worker.chunk_signal.connect(self._on_chunk_received)
        self.active_query_worker.sources_signal.connect(self._on_sources_received)
        self.active_query_worker.finished_signal.connect(self._on_finished_received)
        self.active_query_worker.start()

    def _on_chunk_received(self, chunk: str):
        """Streams text chunks in real-time directly into QTextBrowser."""
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(chunk)
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible()

    def _on_sources_received(self, sources: list):
        """Stores verified sources for citation card rendering."""
        self.pending_sources = sources

    def _on_finished_received(self, full_text: str):
        """Cleans streamed text buffer and replaces it with rendered Markdown and Source/Verification Card."""
        cursor = self.chat_history.textCursor()
        cursor.setPosition(self.stream_start_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()

        # Format full markdown
        formatted_md = markdown.markdown(full_text, extensions=['fenced_code', 'codehilite', 'tables'])

        # Build Source or Tavily Verification Card
        verification_card_html = ""
        if self.pending_sources:
            is_page_doc = any("Active Web Document" in s.get("title", "") for s in self.pending_sources)
            if is_page_doc:
                src_item = self.pending_sources[0]
                url = src_item.get("url", "#")
                summary = src_item.get("summary", "")
                verification_card_html = (
                    "<div style='margin-top: 10px; margin-bottom: 4px; padding: 10px 12px; "
                    "background-color: #0d1117; border: 1px solid #28303f; border-radius: 6px;'>"
                    "<div style='display: flex; align-items: center; margin-bottom: 4px;'>"
                    "<span style='color: #58a6ff; font-weight: 700; font-size: 11px;'>📄 Active Document Source</span>"
                    "</div>"
                    f"<div style='font-size: 11px;'>"
                    f"<a href='{url}' style='color: #58a6ff; text-decoration: none; font-weight: 600;'>{url}</a>"
                    f"</div>"
                    f"<div style='color: #8b949e; font-size: 11px; margin-top: 4px; line-height: 1.4;'>{summary}</div>"
                    "</div>"
                )
            else:
                verification_card_html = (
                    "<div style='margin-top: 10px; margin-bottom: 4px; padding: 10px 12px; "
                    "background-color: #0d1117; border: 1px solid #28303f; border-radius: 6px;'>"
                    "<div style='display: flex; align-items: center; margin-bottom: 6px;'>"
                    "<span style='color: #d49b35; font-weight: 700; font-size: 11px;'>✓ Verified against Tavily</span> "
                    "<span style='color: #7d8590; font-size: 11px; margin-left: 6px;'>(Top 5 results · 250-character summary)</span>"
                    "</div>"
                )
                for i, item in enumerate(self.pending_sources[:5], 1):
                    title = item.get("title", "Source")
                    url = item.get("url", "#")
                    summary = item.get("summary", "")[:250]
                    verification_card_html += (
                        f"<div style='margin-top: 6px; padding-top: 6px; border-top: 1px solid #1c212c;'>"
                        f"<div style='font-size: 11px;'>"
                        f"<span style='color: #d49b35; font-weight: 600;'>[{i}]</span> "
                        f"<a href='{url}' style='color: #58a6ff; text-decoration: none; font-weight: 600;'>{title}</a>"
                        f"</div>"
                        f"<div style='color: #8b949e; font-size: 11px; margin-top: 3px; line-height: 1.4;'>{summary}</div>"
                        f"<div style='color: #484f58; font-size: 10px; margin-top: 2px;'>{url}</div>"
                        f"</div>"
                    )
                verification_card_html += "</div>"

        final_bubble_html = (
            f"<div style='background-color: #11141c; border: 1px solid #222836; border-radius: 6px; "
            f"padding: 10px 12px; margin-top: 4px; color: #e6edf3; font-size: 13px; line-height: 1.5;'>"
            f"{formatted_md}"
            f"{verification_card_html}"
            f"</div>"
        )
        cursor.insertHtml(final_bubble_html)
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible()
        self.status_label.setText("Ready")

    def clear_chat(self):
        self.chat_history.clear()
        self._append_system_intro()
        self.status_label.setText("Ready")

    def export_conversation(self):
        history_text = self.chat_history.toPlainText()
        if not history_text.strip():
            self.status_label.setText("Export failed: Empty chat")
            return

        filename = f"Pikachu_Intelligence_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Intelligence Transcript",
            filename,
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("=== PIKACHU AI VERIFIED INTELLIGENCE TRANSCRIPT ===\n")
                    f.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
                    f.write(f"Active Domain: {self.current_mode}\n")
                    f.write("="*60 + "\n\n")
                    f.write(history_text)
                self.status_label.setText(f"Exported to {os.path.basename(file_path)}")
            except Exception as e:
                self.status_label.setText(f"Export Error: {str(e)}")
