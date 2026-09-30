import time
from PySide6.QtCore import QThread, Signal
from src.core.vector_store import VectorStoreManager
from src.core.searxng_client import SearxngClient
from src.core.llm_client import LLMClient

class SpecializedQueryWorker(QThread):
    """
    Dedicated worker strictly enforcing the user's three specialized domains:
    1. Locality News (Sonipat, Haryana)
    2. Trading Summary of the Week
    3. Weather Update

    Execution Pipeline:
    - Topic Classification (Scope Gatekeeper)
    - If out-of-scope: Streams polite guidance reminding user of the 3 domains.
    - If in-scope:
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
        "news", "local", "locality", "sonipat", "rohtak", "haryana", "civic", "city",
        "town", "municipal", "roads", "transit", "event", "events", "district",
        "community", "regional", "administration", "police", "development",
        "municipality", "panchayat", "state news", "headline", "headlines"
    ]

    OUT_OF_SCOPE_MESSAGE = (
        "### ⚡ Pikachu AI · Specialized Domain Assistant\n\n"
        "I am specifically dedicated and restricted to **three primary intelligence domains**:\n\n"
        "1. **📍 Locality News** — Regional, civic, municipal, and community updates for your area (*Sonipat, Haryana*).\n"
        "2. **📈 Trading Summary of the Week** — Financial markets recap, global indices (Nifty, Sensex, S&P 500, Nasdaq), commodities (Gold, Crude Oil), and digital assets.\n"
        "3. **⛅ Weather Update** — Live meteorological telemetry, temperature, humidity, atmospheric pressure, and regional forecasts.\n\n"
        "*Your query is outside these three specialized domains. Please submit a question related to Locality News, Trading/Markets, or Weather, or select one of the action tabs above!*"
    )

    def __init__(
        self,
        query: str,
        active_tab: str = "auto",
        vector_store: VectorStoreManager = None,
        searxng_client: SearxngClient = None,
        llm_client: LLMClient = None
    ):
        super().__init__()
        self.query = query.strip()
        self.active_tab = active_tab
        self.vector_store = vector_store or VectorStoreManager()
        self.searxng_client = searxng_client or SearxngClient()
        self.llm_client = llm_client or LLMClient()

    def _classify_topic(self) -> str:
        """Classifies the query into 'weather', 'trading_summary', 'locality_news', or 'out_of_scope'."""
        q_lower = self.query.lower()

        # If user explicitly selected one of the 3 tabs and prompt is generic or matches
        if self.active_tab in ("weather", "trading_summary", "locality_news"):
            # Check if user explicitly asked for a different domain while on this tab
            if self.active_tab == "weather" and any(k in q_lower for k in self.TRADING_KEYWORDS):
                return "trading_summary"
            if self.active_tab == "weather" and any(k in q_lower for k in self.LOCALITY_KEYWORDS):
                return "locality_news"

            if self.active_tab == "trading_summary" and any(k in q_lower for k in self.WEATHER_KEYWORDS):
                return "weather"
            if self.active_tab == "trading_summary" and any(k in q_lower for k in self.LOCALITY_KEYWORDS):
                return "locality_news"

            if self.active_tab == "locality_news" and any(k in q_lower for k in self.WEATHER_KEYWORDS):
                return "weather"
            if self.active_tab == "locality_news" and any(k in q_lower for k in self.TRADING_KEYWORDS):
                return "trading_summary"

            # Otherwise respect the active tab
            return self.active_tab

        # Free-form classification based on query keywords
        if any(k in q_lower for k in self.WEATHER_KEYWORDS):
            return "weather"
        if any(k in q_lower for k in self.TRADING_KEYWORDS):
            return "trading_summary"
        if any(k in q_lower for k in self.LOCALITY_KEYWORDS):
            return "locality_news"

        return "out_of_scope"

    def run(self):
        try:
            topic = self._classify_topic()
            self.domain_signal.emit(topic)

            # --- Out-of-Scope Gating ---
            if topic == "out_of_scope":
                self.status_signal.emit("Query outside specialized domains")
                # Stream the polite guidance smoothly
                words = self.OUT_OF_SCOPE_MESSAGE.split(" ")
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    self.chunk_signal.emit(chunk)
                    time.sleep(0.012)

                self.sources_signal.emit([])
                self.finished_signal.emit(self.OUT_OF_SCOPE_MESSAGE)
                self.status_signal.emit("Ready")
                return

            # --- Domain-Specific Setup ---
            if topic == "weather":
                domain_title = "Meteorological Telemetry & Weather Update"
                verification_query = f"{self.query} Sonipat Haryana weather temperature forecast"
            elif topic == "trading_summary":
                domain_title = "Weekly Financial Markets & Trading Summary"
                verification_query = f"{self.query} weekly market summary Nifty Sensex S&P 500 commodities crypto"
            else:  # locality_news
                domain_title = "Locality & Regional News Brief"
                verification_query = f"{self.query} Sonipat Haryana regional local news updates"

            # --- Step 1: Pre-digested ChromaDB Intelligence ---
            self.status_signal.emit("Retrieving pre-digested ChromaDB baseline...")
            chroma_chunks = self.vector_store.query_intelligence(topic, self.query, n_results=3)
            if chroma_chunks:
                chroma_context = "\n---\n".join(chroma_chunks)
            else:
                chroma_context = "No pre-digested baseline found in ChromaDB for this topic."

            # --- Step 2: Live Tavily Verification (Strict Top 5 · 250 Chars Summary) ---
            self.status_signal.emit("Verifying against Tavily (top 5 sources · 250-char summary)...")
            tavily_res = self.searxng_client.verify_with_tavily(
                verification_query,
                max_results=5,
                max_chars_per_summary=250
            )
            tavily_context = self.searxng_client.format_verification_context(tavily_res)
            verified_sources = tavily_res.get("results", [])

            # --- Step 3: Stream Verified Synthesis ---
            self.status_signal.emit("Pikachu AI streaming verified intelligence...")
            final_answer = self.llm_client.answer_verified_specialized_query(
                user_query=self.query,
                domain_title=domain_title,
                chroma_context=chroma_context,
                tavily_context=tavily_context,
                chunk_callback=self.chunk_signal.emit
            )

            # --- Step 4: Emit Sources & Completion ---
            self.sources_signal.emit(verified_sources)
            self.finished_signal.emit(final_answer)
            self.status_signal.emit("Ready")

        except Exception as e:
            err_msg = f"⚠️ **Specialized Assistant Error:** {str(e)}"
            self.chunk_signal.emit(err_msg)
            self.sources_signal.emit([])
            self.finished_signal.emit(err_msg)
            self.status_signal.emit("Error")
