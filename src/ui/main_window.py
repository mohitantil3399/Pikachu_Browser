from PySide6.QtCore import QUrl, QRect, Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QToolBar
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from src.config import APP_TITLE, DEFAULT_DOC_URL, SEARXNG_ENDPOINT
from src.ui.styles import DARK_THEME_STYLESHEET
from src.ui.chat_drawer import FloatingChatDrawer
from src.core.vector_store import VectorStoreManager
from src.core.searxng_client import SearxngClient
from src.core.llm_client import LLMClient
from src.workers.indexer_worker import IndexerWorker

class AgenticDocBrowser(QMainWindow):
    """Main Application Window with Integrated QWebEngineView and Floating Pikachu AI Drawer."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setGeometry(100, 100, 1360, 860)

        # Apply global stylesheet
        self.setStyleSheet(DARK_THEME_STYLESHEET)

        # Core Backend Services
        self.vector_store = VectorStoreManager()
        self.searxng_client = SearxngClient()
        self.llm_client = LLMClient()
        self.indexer_worker = None

        # Build UI Components
        self._init_ui()

        # Trigger Initial Page Ingestion
        self.trigger_indexing(DEFAULT_DOC_URL)

    def _init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Navigation & Address Toolbar
        self.toolbar = QToolBar("Navigation Toolbar")
        self.addToolBar(self.toolbar)

        self.btn_back = QPushButton("◀")
        self.btn_back.setObjectName("navBtn")
        self.btn_back.clicked.connect(self.navigate_back)

        self.btn_forward = QPushButton("▶")
        self.btn_forward.setObjectName("navBtn")
        self.btn_forward.clicked.connect(self.navigate_forward)

        self.btn_reload = QPushButton("🔄")
        self.btn_reload.setObjectName("navBtn")
        self.btn_reload.clicked.connect(self.reload_page)

        self.url_bar = QLineEdit(DEFAULT_DOC_URL)
        self.url_bar.setObjectName("urlBar")
        self.url_bar.returnPressed.connect(self.load_url)

        self.btn_searxng_quick = QPushButton("🔍 SearXNG")
        self.btn_searxng_quick.setObjectName("navBtn")
        self.btn_searxng_quick.clicked.connect(self.open_searxng_home)

        self.btn_toggle_drawer = QPushButton("⚡ Pikachu AI Assistant")
        self.btn_toggle_drawer.setObjectName("pikachuToggleBtn")
        self.btn_toggle_drawer.clicked.connect(self.toggle_drawer)

        self.toolbar.addWidget(self.btn_back)
        self.toolbar.addWidget(self.btn_forward)
        self.toolbar.addWidget(self.btn_reload)
        self.toolbar.addWidget(self.url_bar)
        self.toolbar.addWidget(self.btn_searxng_quick)
        self.toolbar.addWidget(self.btn_toggle_drawer)

        # 2. Browser View Frame
        self.browser_frame = QWidget()
        self.browser_layout = QVBoxLayout(self.browser_frame)
        self.browser_layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl(DEFAULT_DOC_URL))
        self.web_view.urlChanged.connect(self.on_url_changed)
        self.browser_layout.addWidget(self.web_view)

        self.main_layout.addWidget(self.browser_frame, stretch=1)

        # 3. Floating AI Drawer Widget
        self.drawer = FloatingChatDrawer(
            parent=self.browser_frame,
            vector_store=self.vector_store,
            searxng_client=self.searxng_client,
            llm_client=self.llm_client,
            get_current_url_cb=self.get_current_url
        )
        self.drawer_visible = False
        self.drawer.hide()
        self.drawer.close_requested.connect(self.hide_drawer)

    def get_current_url(self) -> str:
        return self.url_bar.text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position floating drawer at bottom right corner overlaying browser frame
        w, h = 460, 480
        margin = 20
        x = self.browser_frame.width() - w - margin
        y = self.browser_frame.height() - h - margin
        self.drawer_target_rect = QRect(x, y, w, h)
        if self.drawer_visible:
            self.drawer.setGeometry(self.drawer_target_rect)
            self.drawer.raise_()

    def hide_drawer(self):
        self.drawer.hide()
        self.drawer_visible = False

    def show_drawer(self):
        w, h = 460, 480
        margin = 20
        x = self.browser_frame.width() - w - margin
        y = self.browser_frame.height() - h - margin
        self.drawer_target_rect = QRect(x, y, w, h)
        self.drawer.setGeometry(self.drawer_target_rect)
        self.drawer.show()
        self.drawer.raise_()
        self.drawer_visible = True

    def toggle_drawer(self):
        if self.drawer_visible:
            self.hide_drawer()
        else:
            self.show_drawer()

    def navigate_back(self):
        self.web_view.back()

    def navigate_forward(self):
        self.web_view.forward()

    def reload_page(self):
        self.web_view.reload()

    def open_searxng_home(self):
        searxng_home = "http://localhost:8080"
        self.url_bar.setText(searxng_home)
        self.web_view.setUrl(QUrl(searxng_home))

    def load_url(self):
        target = self.url_bar.text().strip()
        if not target.startswith(("http://", "https://")):
            target = "https://" + target
        self.web_view.setUrl(QUrl(target))

    def on_url_changed(self, qurl):
        url = qurl.toString()
        self.url_bar.setText(url)
        self.trigger_indexing(url)

    def trigger_indexing(self, url: str):
        # Don't index local searxng homepage
        if "localhost:8080" in url:
            self.drawer.set_status("SearXNG Web Search Engine active.")
            return

        if self.indexer_worker and self.indexer_worker.isRunning():
            self.indexer_worker.terminate()
            self.indexer_worker.wait()

        self.indexer_worker = IndexerWorker(url, self.vector_store)
        self.indexer_worker.progress_signal.connect(self.drawer.update_indexing_progress)
        self.indexer_worker.status_signal.connect(self.drawer.set_status)
        self.indexer_worker.completed_signal.connect(self.drawer.on_indexing_complete)
        self.indexer_worker.start()
