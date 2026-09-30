import time
import trafilatura
from PySide6.QtCore import QThread, Signal
from src.core.vector_store import VectorStoreManager
from src.core.searxng_client import SearxngClient
from src.core.llm_client import LLMClient

class SpecializedQueryWorker(QThread):
    """
    Dedicated worker handling both:
    1. Active Page Context (RAG for the currently open web document / page)
    2. The 3 Specialized Intelligence Domains:
       - Locality News (Sonipat, Haryana)
       - Trading Summary of the Week
       - Weather Update

    Execution Pipeline:
    - Topic Classification (Scope Gatekeeper & Intelligent Router)
    - If Page Context:
      1. Queries ChromaDB for top matching chunks of the active webpage URL.
      2. Streams grounded answer token-by-token using answer_doc_query.
      3. Emits active page citation card.
    - If Specialized Domain (Locality / Trading / Weather):
      1. Retrieves pre-digested ChromaDB baseline (stored beforehand on separate thread).
      2. Verifies against Tavily live search (Top 5 results, 250-character summary).
      3. Streams verified response token-by-token.
      4. Emits verified sources for citation card display.
    """
    status_signal = Signal(str)
    chunk_signal = Signal(str)
    finished_signal = Signal(str)
    sources_signal = Signal(list)
    domain_signal = Signal(str)

    WEATHER_KEYWORDS = [
        "weather", "temp", "temperature", "forecast", "rain", "rainy", "climate",
        "humidity", "sunny", "wind", "storm", "celsius", "fahrenheit", "aqi",
        "air quality", "cold", "hot", "clouds", "cloudy", "hail", "breeze"
    ]

    TRADING_KEYWORDS = [
        "trading", "trade", "market", "markets", "stock", "stocks", "nifty",
        "sensex", "share", "shares", "crypto", "bitcoin", "btc", "nasdaq",
        "s&p", "sp500", "dow", "crude", "oil", "gold", "forex", "invest",
        "commodity", "commodities", "bull", "bear", "rally", "equities",
        "weekly summary", "trading summary"
    ]

    LOCALITY_KEYWORDS = [
        "sonipat", "rohtak", "haryana", "civic", "municipal", "municipality",
        "roads", "transit", "district", "panchayat", "local news", "locality news",
        "regional news", "civic news"
    ]

    PAGE_KEYWORDS = [
        "page", "document", "doc", "article", "guide", "summary", "summarize",
        "code", "function", "class", "method", "syntax", "example", "explain",
        "tutorial", "concept", "section", "paragraph", "author", "website",
        "kotlin", "python", "collections", "map", "list", "set", "array",
        "start", "starting", "startup", "overview", "what is", "how to"
    ]

    OUT_OF_SCOPE_MESSAGE = (
        "### ⚡ Pikachu AI · Research & Intelligence Assistant\n\n"
        "I can help you with:\n\n"
        "1. **📄 Active Webpage Context** — Ask questions, request summaries, or explain concepts from the current webpage.\n"
        "2. **📍 Locality News** — Regional, civic, municipal, and community updates (*Sonipat, Haryana*).\n"
        "3. **📈 Trading Summary of the Week** — Financial markets recap, global indices (Nifty, Sensex, S&P 500, Nasdaq), commodities (Gold, Crude Oil), and digital assets.\n"
        "4. **⛅ Weather Update** — Live meteorological telemetry, temperature, humidity, atmospheric pressure, and regional forecasts.\n\n"
        "*Please submit a question related to your active webpage or one of the 3 specialized intelligence domains above!*"
    )

    def __init__(
        self,
        query: str,
        active_tab: str = "page_context",
        current_url: str = None,
        vector_store: VectorStoreManager = None,
        searxng_client: SearxngClient = None,
        llm_client: LLMClient = None
    ):
        super().__init__()
        self.query = query.strip()
        self.active_tab = active_tab
        self.current_url = current_url
        self.vector_store = vector_store or VectorStoreManager()
        self.searxng_client = searxng_client or SearxngClient()
        self.llm_client = llm_client or LLMClient()

    def _classify_topic(self) -> str:
        """Classifies the query into 'page_context', 'weather', 'trading_summary', 'locality_news', or 'out_of_scope'."""
        q_lower = self.query.lower()

        # If user explicitly selected Page Context tab
        if self.active_tab == "page_context":
            if any(k in q_lower for k in self.WEATHER_KEYWORDS):
                return "weather"
            if any(k in q_lower for k in self.TRADING_KEYWORDS):
                return "trading_summary"
            if any(k in q_lower for k in self.LOCALITY_KEYWORDS):
                return "locality_news"
            return "page_context"

        # If user selected Locality News tab
        if self.active_tab == "locality_news":
            if any(k in q_lower for k in self.WEATHER_KEYWORDS):
                return "weather"
            if any(k in q_lower for k in self.TRADING_KEYWORDS):
                return "trading_summary"
            # Reroute to page context if query clearly asks about document/code/page without locality terms
            if any(k in q_lower for k in self.PAGE_KEYWORDS) and not any(k in q_lower for k in self.LOCALITY_KEYWORDS):
                return "page_context"
            return "locality_news"

        # If user selected Trading Summary tab
        if self.active_tab == "trading_summary":
            if any(k in q_lower for k in self.WEATHER_KEYWORDS):
                return "weather"
            if any(k in q_lower for k in self.LOCALITY_KEYWORDS):
                return "locality_news"
            if any(k in q_lower for k in self.PAGE_KEYWORDS) and not any(k in q_lower for k in self.TRADING_KEYWORDS):
                return "page_context"
            return "trading_summary"

        # If user selected Weather tab
        if self.active_tab == "weather":
            if any(k in q_lower for k in self.TRADING_KEYWORDS):
                return "trading_summary"
            if any(k in q_lower for k in self.LOCALITY_KEYWORDS):
                return "locality_news"
            if any(k in q_lower for k in self.PAGE_KEYWORDS) and not any(k in q_lower for k in self.WEATHER_KEYWORDS):
                return "page_context"
            return "weather"

        # Free-form auto classification
        if any(k in q_lower for k in self.WEATHER_KEYWORDS):
            return "weather"
        if any(k in q_lower for k in self.TRADING_KEYWORDS):
            return "trading_summary"
        if any(k in q_lower for k in self.LOCALITY_KEYWORDS):
            return "locality_news"
        if any(k in q_lower for k in self.PAGE_KEYWORDS) or self.current_url:
            return "page_context"

        return "out_of_scope"

    def run(self):
        try:
            topic = self._classify_topic()
            self.domain_signal.emit(topic)

            # --- Out-of-Scope Gating ---
            if topic == "out_of_scope":
                self.status_signal.emit("Query outside supported domains")
                words = self.OUT_OF_SCOPE_MESSAGE.split(" ")
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    self.chunk_signal.emit(chunk)
                    time.sleep(0.012)

                self.sources_signal.emit([])
                self.finished_signal.emit(self.OUT_OF_SCOPE_MESSAGE)
                self.status_signal.emit("Ready")
                return

            # --- Domain 1: Active Webpage Context (RAG) ---
            if topic == "page_context":
                self.status_signal.emit("Retrieving active webpage context from ChromaDB...")
                chunks = []
                if self.vector_store:
                    chunks = self.vector_store.query(
                        user_query=self.query,
                        current_url=self.current_url,
                        n_results=5
                    )

                if chunks:
                    doc_context = "\n---\n".join(chunks)
                elif self.current_url:
                    # Immediate on-the-fly fetch fallback if page is not yet indexed in vector store
                    try:
                        downloaded = trafilatura.fetch_url(self.current_url)
                        extracted = trafilatura.extract(downloaded) if downloaded else ""
                        doc_context = extracted[:6000] if extracted else f"Active Webpage URL: {self.current_url}"
                    except Exception:
                        doc_context = f"Active Webpage URL: {self.current_url}"
                else:
                    doc_context = "No active webpage context available."

                self.status_signal.emit("Pikachu AI analyzing page context...")
                final_answer = self.llm_client.answer_doc_query(
                    user_query=self.query,
                    context=doc_context,
                    chunk_callback=self.chunk_signal.emit
                )

                sources = []
                if self.current_url:
                    sources.append({
                        "title": "Active Web Document",
                        "url": self.current_url,
                        "summary": f"Context extracted directly from the active page ({len(chunks)} relevant chunks retrieved from ChromaDB)."
                    })

                self.sources_signal.emit(sources)
                self.finished_signal.emit(final_answer)
                self.status_signal.emit("Ready")
                return

            # --- Domains 2, 3, 4: Specialized Intelligence Domains ---
            if topic == "weather":
                domain_title = "Meteorological Telemetry & Weather Update"
                verification_query = f"{self.query} Sonipat Haryana weather temperature forecast"
            elif topic == "trading_summary":
                domain_title = "Weekly Financial Markets & Trading Summary"
                verification_query = f"{self.query} weekly market summary Nifty Sensex S&P 500 commodities crypto"
            else:  # locality_news
                domain_title = "Locality & Regional News Brief"
                verification_query = f"{self.query} Sonipat Haryana regional local news updates"

            # Step 1: Pre-digested ChromaDB Intelligence Baseline
            self.status_signal.emit("Retrieving pre-digested ChromaDB baseline...")
            chroma_chunks = self.vector_store.query_intelligence(topic, self.query, n_results=3)
            if chroma_chunks:
                chroma_context = "\n---\n".join(chroma_chunks)
            else:
                chroma_context = "No pre-digested baseline found in ChromaDB for this topic."

            # Step 2: Live Tavily Verification (Strict Top 5 · 250 Chars Summary)
            self.status_signal.emit("Verifying against Tavily (top 5 sources · 250-char summary)...")
            tavily_res = self.searxng_client.verify_with_tavily(
                verification_query,
                max_results=5,
                max_chars_per_summary=250
            )
            tavily_context = self.searxng_client.format_verification_context(tavily_res)
            verified_sources = tavily_res.get("results", [])

            # Step 3: Stream Verified Synthesis
            self.status_signal.emit("Pikachu AI streaming verified intelligence...")
            final_answer = self.llm_client.answer_verified_specialized_query(
                user_query=self.query,
                domain_title=domain_title,
                chroma_context=chroma_context,
                tavily_context=tavily_context,
                chunk_callback=self.chunk_signal.emit
            )

            # Step 4: Emit Sources & Completion
            self.sources_signal.emit(verified_sources)
            self.finished_signal.emit(final_answer)
            self.status_signal.emit("Ready")

        except Exception as e:
            err_msg = f"⚠️ **Assistant Error:** {str(e)}"
            self.chunk_signal.emit(err_msg)
            self.sources_signal.emit([])
            self.finished_signal.emit(err_msg)
            self.status_signal.emit("Error")

