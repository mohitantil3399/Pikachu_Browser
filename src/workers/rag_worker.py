from PySide6.QtCore import QThread, Signal
from src.core.vector_store import VectorStoreManager
from src.core.llm_client import LLMClient

class RagQueryWorker(QThread):
    answer_signal = Signal(str)

    def __init__(self, user_query: str, vector_store: VectorStoreManager, llm_client: LLMClient, current_url: str = None):
        super().__init__()
        self.user_query = user_query
        self.vector_store = vector_store
        self.llm_client = llm_client
        self.current_url = current_url

    def run(self):
        try:
            # Query vector store specifically for the active URL context
            relevant_chunks = self.vector_store.query(self.user_query, current_url=self.current_url, n_results=3)
            context = "\n---\n".join(relevant_chunks) if relevant_chunks else "No specific page context found."
            
            # Answer query via resilient LLM client
            answer = self.llm_client.answer_doc_query(self.user_query, context)
            self.answer_signal.emit(answer)
        except Exception as e:
            self.answer_signal.emit(f"Error querying page RAG: {str(e)}")


class GeneralQueryWorker(QThread):
    answer_signal = Signal(str)

    def __init__(self, user_query: str, llm_client: LLMClient):
        super().__init__()
        self.user_query = user_query
        self.llm_client = llm_client

    def run(self):
        try:
            answer = self.llm_client.answer_general_query(self.user_query)
            self.answer_signal.emit(answer)
        except Exception as e:
            self.answer_signal.emit(f"Error calling AI Assistant: {str(e)}")
