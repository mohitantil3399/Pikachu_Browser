from PySide6.QtCore import QThread, Signal
from src.core.searxng_client import SearxngClient
from src.core.llm_client import LLMClient

class SearxngQueryWorker(QThread):
    answer_signal = Signal(str)
    chunk_signal = Signal(str)
    status_signal = Signal(str)
    provider_signal = Signal(str)

    def __init__(self, user_query: str, searxng_client: SearxngClient, llm_client: LLMClient):
        super().__init__()
        self.user_query = user_query
        self.searxng_client = searxng_client
        self.llm_client = llm_client

    def run(self):
        try:
            self.status_signal.emit("Searching the web...")
            # Execute web search with automatic Tavily backup
            search_res = self.searxng_client.search(self.user_query, num_results=5)
            
            if not search_res.get("success"):
                err_msg = search_res.get("error", "Web search failed")
                self.chunk_signal.emit(f"⚠️ Search Error: {err_msg}")
                self.answer_signal.emit(f"⚠️ Search Error: {err_msg}")
                return

            provider = search_res.get("provider", "Web Search")
            self.provider_signal.emit(provider)
            self.status_signal.emit("Synthesizing research results with live streaming...")

            # Format search results into context
            web_context = self.searxng_client.format_results_as_context(search_res)
            
            # Answer query via LLM using web context with real-time streaming
            answer = self.llm_client.answer_searxng_query(
                self.user_query,
                web_context,
                search_provider=provider,
                chunk_callback=self.chunk_signal.emit
            )
            
            # Clean citation note
            citation_note = "\n\n<small style='color:#7d8590;'>• Live Web Research</small>"
            answer += citation_note
            self.chunk_signal.emit(citation_note)

            self.answer_signal.emit(answer)
            self.status_signal.emit("Ready")
            
        except Exception as e:
            err_msg = f"Error querying web research: {str(e)}"
            self.chunk_signal.emit(err_msg)
            self.answer_signal.emit(err_msg)
            self.status_signal.emit("Error")
