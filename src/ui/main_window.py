from pathlib import Path
from PySide6.QtCore import QUrl, QRect, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QToolBar, QLabel
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from src.config import APP_TITLE, DEFAULT_DOC_URL, SEARXNG_ENDPOINT
from src.ui.styles import DARK_THEME_STYLESHEET
from src.ui.chat_drawer import FloatingChatDrawer
from src.core.vector_store import VectorStoreManager
from src.core.searxng_client import SearxngClient
from src.core.llm_client import LLMClient
from src.workers.indexer_worker import IndexerWorker

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "icons"

class AgenticDocBrowser(QMainWindow):
    """
    Main Web & Research Browser featuring:
    - Bespoke editorial dark aesthetic compliant with basictoadv standards.
    - Anime.js-inspired fluid animated floating AI Assistant drawer.
    - Dual search infrastructure: Local SearXNG engine with default Tavily Search backup.
    - Real-time clickable citation links routing directly into the active browser engine.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setGeometry(100, 100, 1380, 880)

        # Apply bespoke stylesheet
        self.setStyleSheet(DARK_THEME_STYLESHEET)

        # Core Backend Services
        self.vector_store = VectorStoreManager()
        self.searxng_client = SearxngClient()
        self.llm_client = LLMClient()
        self.indexer_worker = None

        # Build UI Components
        self._init_ui()

        # Check search engine health and update badges
        QTimer.singleShot(500, self.update_search_engine_health)

        # Trigger Initial Page Ingestion
        self.trigger_indexing(DEFAULT_DOC_URL)

    def _get_icon(self, name: str) -> QIcon:
        icon_path = ASSETS_DIR / name
        if icon_path.exists():
            return QIcon(str(icon_path))
        return QIcon()

    def _init_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Navigation & Address Toolbar
        self.toolbar = QToolBar("Navigation Toolbar")
        self.toolbar.setObjectName("navToolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        # Navigation Controls (Back, Forward, Reload, Home)
        self.btn_back = QPushButton()
        self.btn_back.setObjectName("navBtn")
        self.btn_back.setIcon(self._get_icon("arrow-left.svg"))
        self.btn_back.setToolTip("Back (Alt+Left)")
        self.btn_back.clicked.connect(self.navigate_back)

        self.btn_forward = QPushButton()
        self.btn_forward.setObjectName("navBtn")
        self.btn_forward.setIcon(self._get_icon("arrow-right.svg"))
        self.btn_forward.setToolTip("Forward (Alt+Right)")
        self.btn_forward.clicked.connect(self.navigate_forward)

        self.btn_reload = QPushButton()
        self.btn_reload.setObjectName("navBtn")
        self.btn_reload.setIcon(self._get_icon("rotate-cw.svg"))
        self.btn_reload.setToolTip("Reload Page (Ctrl+R)")
        self.btn_reload.clicked.connect(self.reload_page)

        self.btn_home = QPushButton()
        self.btn_home.setObjectName("navBtn")
        self.btn_home.setIcon(self._get_icon("home.svg"))
        self.btn_home.setToolTip("Documentation Home")
        self.btn_home.clicked.connect(self.navigate_home)

        # URL Bar
        self.url_bar = QLineEdit(DEFAULT_DOC_URL)
        self.url_bar.setObjectName("urlBar")
        self.url_bar.returnPressed.connect(self.load_url)

        # Search Engine Quick Action
        self.btn_search_quick = QPushButton("Web Search")
        self.btn_search_quick.setObjectName("searchQuickBtn")
        self.btn_search_quick.setIcon(self._get_icon("search.svg"))
        self.btn_search_quick.setToolTip("Open SearXNG / Web Search")
        self.btn_search_quick.clicked.connect(self.open_search_engine)

        # Live Health Badge (SearXNG vs Tavily Backup)
        self.search_health_badge = QLabel("SearXNG · Tavily Ready")
        self.search_health_badge.setObjectName("searchHealthBadge")

        # Pikachu Assistant Drawer Toggle
        self.btn_toggle_drawer = QPushButton("Pikachu AI Assistant")
        self.btn_toggle_drawer.setObjectName("pikachuToggleBtn")
        self.btn_toggle_drawer.setIcon(self._get_icon("agent.svg"))
        self.btn_toggle_drawer.clicked.connect(self.toggle_drawer)

        # Assemble Toolbar
        self.toolbar.addWidget(self.btn_back)
        self.toolbar.addWidget(self.btn_forward)
        self.toolbar.addWidget(self.btn_reload)
        self.toolbar.addWidget(self.btn_home)
        self.toolbar.addWidget(self.url_bar)
        self.toolbar.addWidget(self.btn_search_quick)
        self.toolbar.addWidget(self.search_health_badge)
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

        # 3. Floating AI Drawer Widget (Animated Overlay)
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
        self.drawer.url_navigation_requested.connect(self.navigate_to_url)

    def get_current_url(self) -> str:
        return self.url_bar.text()

    def update_search_engine_health(self):
        """Checks if local SearXNG is up; if not, indicates Tavily backup is active."""
        is_searxng = self.searxng_client.check_searxng_health(timeout=1.0)
        if is_searxng:
            self.search_health_badge.setText("SearXNG Active")
            self.search_health_badge.setProperty("status", "searxng")
        else:
            self.search_health_badge.setText("Tavily Backup Active")
            self.search_health_badge.setProperty("status", "tavily")

        self.search_health_badge.style().unpolish(self.search_health_badge)
        self.search_health_badge.style().polish(self.search_health_badge)
        self.drawer.update_search_engine_badge()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Position floating drawer at bottom right corner overlaying browser frame
        w, h = 480, 520
        margin = 20
        x = max(20, self.browser_frame.width() - w - margin)
        y = max(20, self.browser_frame.height() - h - margin)
        self.drawer_target_rect = QRect(x, y, w, h)
        if self.drawer_visible:
            self.drawer.setGeometry(self.drawer_target_rect)
            self.drawer.raise_()

    def hide_drawer(self):
        if self.drawer_visible:
            self.drawer.hide_animated()
            self.drawer_visible = False

    def show_drawer(self):
        w, h = 480, 520
        margin = 20
        x = max(20, self.browser_frame.width() - w - margin)
        y = max(20, self.browser_frame.height() - h - margin)
        self.drawer_target_rect = QRect(x, y, w, h)
        self.drawer.show_animated(self.drawer_target_rect)
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

    def navigate_home(self):
        self.navigate_to_url(DEFAULT_DOC_URL)

    def navigate_to_url(self, target_url: str):
        target = target_url.strip()
        if not target.startswith(("http://", "https://")):
            target = "https://" + target
        self.url_bar.setText(target)
        self.web_view.setUrl(QUrl(target))

    def open_search_engine(self):
        # If SearXNG is online, open local homepage, otherwise search with Tavily
        if self.searxng_client.searxng_online:
            searxng_home = "http://localhost:8080"
            self.navigate_to_url(searxng_home)
        else:
            # Switch Pikachu to Deep Research mode and open drawer
            self.drawer.set_mode("searxng")
            self.show_drawer()
            self.drawer.set_status("SearXNG offline · Tavily Search Backup Ready")

    def load_url(self):
        self.navigate_to_url(self.url_bar.text())

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
