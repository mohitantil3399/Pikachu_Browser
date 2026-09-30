from PySide6.QtCore import QThread, Signal
from src.core.searxng_client import SearxngClient
from src.core.llm_client import LLMClient

class SearxngQueryWorker(QThread):
    answer_signal = Signal(str)
    status_signal = Signal(str)
    provider_signal = Signal(str)

    def __init__(self, user_query: str, searxng_client: SearxngClient, llm_client: LLMClient):
        super().__init__()
        self.user_query = user_query
        self.searxng_client = searxng_client
        self.llm_client = llm_client

    def run(self):
        try:
            self.status_signal.emit("Searching web (SearXNG with Tavily backup)...")
            # Execute web search with automatic Tavily backup
            search_res = self.searxng_client.search(self.user_query, num_results=5)
            
            if not search_res.get("success"):
                err_msg = search_res.get("error", "Failed web search across SearXNG and Tavily")
                self.answer_signal.emit(f"⚠️ Search Error: {err_msg}")
                return

            provider = search_res.get("provider", "Web Search")
            self.provider_signal.emit(provider)

            if search_res.get("backup_activated"):
                self.status_signal.emit("SearXNG offline · Tavily backup search active")
            else:
                self.status_signal.emit(f"Synthesizing results via {provider}...")

            # Format search results into context
            web_context = self.searxng_client.format_results_as_context(search_res)
            
            # Answer query via LLM using web context
            answer = self.llm_client.answer_searxng_query(self.user_query, web_context, search_provider=provider)
            
            # Append clean provider citation summary
            if search_res.get("backup_activated"):
                answer += "\n\n<small style='color:#d49b35;'>• Web Research powered by Tavily Search (SearXNG local backup)</small>"
            else:
                answer += f"\n\n<small style='color:#7d8590;'>• Web Research powered by {provider}</small>"

            self.answer_signal.emit(answer)
            
        except Exception as e:
            self.answer_signal.emit(f"Error querying web research: {str(e)}")
