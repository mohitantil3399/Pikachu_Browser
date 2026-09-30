from PySide6.QtCore import QThread, Signal
from src.core.vector_store import VectorStoreManager
from src.core.digest_service import IntelligenceDigestService

class IntelligenceDigestWorker(QThread):
    """
    Background worker that runs on a separate thread to pre-digest:
    1. Locality News (Sonipat, Haryana)
    2. Trading Summary of the Week
    3. Weather Update
    directly into local ChromaDB with zero UI blocking.
    """
    status_signal = Signal(str)
    progress_signal = Signal(int)
    finished_signal = Signal(bool, str)

    def __init__(self, vector_store: VectorStoreManager = None):
        super().__init__()
        self.vector_store = vector_store or VectorStoreManager()
        self.service = IntelligenceDigestService(vector_store=self.vector_store)

    def run(self):
        try:
            self.status_signal.emit("Pre-digesting intelligence into ChromaDB (separate thread)...")
            
            def _progress(pct: int, msg: str):
                self.progress_signal.emit(pct)
                self.status_signal.emit(msg)

            results = self.service.digest_all(progress_callback=_progress)
            summary_msg = f"Digested {len(results)} intelligence domains into ChromaDB (Weather, Markets, Locality News)."
            self.finished_signal.emit(True, summary_msg)
        except Exception as e:
            self.finished_signal.emit(False, f"Pre-digestion error: {str(e)}")
