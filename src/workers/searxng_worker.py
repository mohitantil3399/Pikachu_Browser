from PySide6.QtCore import QThread, Signal
from src.core.searxng_client import SearxngClient
from src.core.llm_client import LLMClient

class SearxngQueryWorker(QThread):
    answer_signal = Signal(str)

    def __init__(self, user_query: str, searxng_client: SearxngClient, llm_client: LLMClient):
        super().__init__()
        self.user_query = user_query
        self.searxng_client = searxng_client
        self.llm_client = llm_client

    def run(self):
        try:
            # Execute web search via SearXNG local API
            search_res = self.searxng_client.search(self.user_query, num_results=5)
            
            if not search_res.get("success"):
                err_msg = search_res.get("error", "Failed web search")
                self.answer_signal.emit(f"⚠️ SearXNG Search Error: {err_msg}")
                return

            # Format search results into context
            web_context = self.searxng_client.format_results_as_context(search_res)
            
            # Answer query via LLM using web context
            answer = self.llm_client.answer_searxng_query(self.user_query, web_context)
            self.answer_signal.emit(answer)
            
        except Exception as e:
            self.answer_signal.emit(f"Error querying SearXNG: {str(e)}")
