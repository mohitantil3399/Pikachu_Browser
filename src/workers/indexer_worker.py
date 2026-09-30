import hashlib
import trafilatura
from PySide6.QtCore import QThread, Signal
from src.core.vector_store import VectorStoreManager
from src.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP

class IndexerWorker(QThread):
    """
    Worker thread that extracts text from the active webpage,
    checks ChromaDB cache to store embeddings ONLY if not already present,
    and batch processes chunks to prevent embedding breaks.
    """
    progress_signal = Signal(int)
    status_signal = Signal(str)
    completed_signal = Signal(bool, str)

    def __init__(self, url: str, vector_store: VectorStoreManager, force_reindex: bool = False):
        super().__init__()
        self.url = url
        self.vector_store = vector_store
        self.force_reindex = force_reindex

    def run(self):
        try:
            # 1. Check if page is already indexed in ChromaDB (Requirement 6)
            if not self.force_reindex and self.vector_store.is_url_indexed(self.url):
                count = self.vector_store.get_url_chunk_count(self.url)
                self.status_signal.emit(f"⚡ VectorDB Cache Hit ({count} chunks)")
                self.progress_signal.emit(100)
                self.completed_signal.emit(True, f"Loaded {count} chunks from local ChromaDB cache (no re-embedding).")
                return

            # 2. Extract webpage text
            self.status_signal.emit("Fetching webpage text...")
            downloaded = trafilatura.fetch_url(self.url)
            text = trafilatura.extract(downloaded) if downloaded else ""

            if not text or len(text) < 60:
                self.completed_signal.emit(False, "Could not extract clean documentation text from page.")
                return

            # 3. Chunk text (Requirement 4)
            self.status_signal.emit("Chunking extracted text...")
            chunk_size = DEFAULT_CHUNK_SIZE
            overlap = DEFAULT_CHUNK_OVERLAP
            chunks = []
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunks.append(text[start:end])
                start += (chunk_size - overlap)

            total_chunks = len(chunks)
            self.status_signal.emit(f"Batch embedding {total_chunks} chunks locally...")

            # 4. Safe Batch Processing (e.g. 16 chunks per write) to prevent memory or API breaks
            batch_size = 16
            url_hash = hashlib.md5(self.url.encode("utf-8")).hexdigest()[:10]

            for i in range(0, total_chunks, batch_size):
                batch_docs = chunks[i : i + batch_size]
                batch_ids = [f"{url_hash}_chunk_{j}" for j in range(i, i + len(batch_docs))]
                batch_metas = [{"url": self.url, "chunk_index": j} for j in range(i, i + len(batch_docs))]

                try:
                    self.vector_store.add_chunks_batch(batch_docs, batch_ids, batch_metas)
                except Exception as batch_err:
                    print(f"[IndexerWorker] Warning on batch {i}: {batch_err}")

                progress = int(((i + len(batch_docs)) / total_chunks) * 100)
                self.progress_signal.emit(min(progress, 100))

            self.completed_signal.emit(True, f"Indexed {total_chunks} chunks in ChromaDB!")

        except Exception as e:
            self.completed_signal.emit(False, f"Indexing Error: {str(e)}")
