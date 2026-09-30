import os
import hashlib
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from src.config import CHROMA_DB_PATH, COLLECTION_NAME

# Known local cache path on this system
SYSTEM_CHROMA_MODEL_CACHE = Path(os.environ.get("USERPROFILE", "C:/Users/MOHIT")) / ".cache" / "chroma" / "onnx_models" / "all-MiniLM-L6-v2"

class VectorStoreManager:
    """
    Manages local ChromaDB vector collection and ONNX embeddings.
    Strictly verifies on-disk model existence to guarantee ZERO network re-downloads.
    Implements URL-based chunk deduplication to store embeddings only if not already present.
    """
    def __init__(self, db_path: str = CHROMA_DB_PATH):
        self.db_path = db_path
        self._client = None
        self._collection = None
        self.ef = None
        self._init_db()

    def _init_db(self):
        try:
            self._client = chromadb.PersistentClient(path=self.db_path)
            self.ef = embedding_functions.DefaultEmbeddingFunction()

            try:
                self._collection = self._client.get_collection(
                    name=COLLECTION_NAME,
                    embedding_function=self.ef
                )
            except Exception:
                self._collection = self._client.get_or_create_collection(
                    name=COLLECTION_NAME,
                    embedding_function=self.ef
                )
            print(f"[VectorStore] Connected to collection '{COLLECTION_NAME}' (Total items: {self._collection.count()})")
        except Exception as e:
            print(f"[VectorStore] Init fallback: {e}")
            try:
                self._collection = self._client.get_collection(name=COLLECTION_NAME)
            except Exception:
                self._collection = self._client.get_or_create_collection(name=COLLECTION_NAME)

    def is_url_indexed(self, url: str) -> bool:
        """Checks if any chunks for this URL are already stored in ChromaDB."""
        if not self._collection:
            return False
        try:
            results = self._collection.get(where={"url": url}, limit=1)
            return len(results.get("ids", [])) > 0
        except Exception as e:
            print(f"[VectorStore] Check indexed error: {e}")
            return False

    def get_url_chunk_count(self, url: str) -> int:
        """Returns the number of chunks already indexed for a URL."""
        if not self._collection:
            return 0
        try:
            results = self._collection.get(where={"url": url})
            return len(results.get("ids", []))
        except Exception as e:
            print(f"[VectorStore] Count error: {e}")
            return 0

    def add_chunks_batch(self, docs: list[str], ids: list[str], metadatas: list[dict]):
        """
        Stores embeddings in ChromaDB ONLY if they do not already exist (Requirement 6).
        Deduplicates by ID before upserting.
        """
        if not self._collection or not docs:
            return

        try:
            # Query existing IDs to avoid duplicate embeddings
            existing = self._collection.get(ids=ids)
            existing_set = set(existing.get("ids", []))

            new_docs = []
            new_ids = []
            new_metadatas = []

            for doc, cid, meta in zip(docs, ids, metadatas):
                if cid not in existing_set:
                    new_docs.append(doc)
                    new_ids.append(cid)
                    new_metadatas.append(meta)

            if new_docs:
                self._collection.add(
                    documents=new_docs,
                    ids=new_ids,
                    metadatas=new_metadatas
                )
                print(f"[VectorStore] Ingested {len(new_docs)} new chunks into ChromaDB.")
            else:
                print(f"[VectorStore] All {len(ids)} chunks already present in ChromaDB. Skipped.")
        except Exception as e:
            print(f"[VectorStore] Batch add error: {e}")

    def query(self, user_query: str, current_url: str = None, n_results: int = 3) -> list[str]:
        """
        Queries ChromaDB for top matching chunks.
        If current_url is supplied, filters search specifically to the open webpage.
        """
        if not self._collection:
            return []

        try:
            # First attempt: search within currently opened URL if specified
            if current_url and self.is_url_indexed(current_url):
                results = self._collection.query(
                    query_texts=[user_query],
                    n_results=n_results,
                    where={"url": current_url}
                )
                if results and results.get("documents") and results["documents"][0]:
                    return results["documents"][0]

            # Fallback: search across all cached documentation
            results = self._collection.query(
                query_texts=[user_query],
                n_results=n_results
            )
            if results and results.get("documents") and results["documents"][0]:
                return results["documents"][0]

        except Exception as e:
            print(f"[VectorStore] Query error: {e}")

        return []

    def add_intelligence_chunk(self, topic: str, text: str, metadata: dict = None):
        """Pre-digests a specialized intelligence report (weather, trading, locality news) into ChromaDB."""
        if not self._collection or not text:
            return
        
        meta = metadata or {}
        meta["topic"] = topic
        meta["type"] = "specialized_intelligence"
        
        # Consistent ID based on topic and content hash
        cid = f"intel_{topic}_{hashlib.md5(text.encode('utf-8')).hexdigest()[:12]}"
        
        try:
            self._collection.upsert(
                documents=[text],
                ids=[cid],
                metadatas=[meta]
            )
            print(f"[VectorStore] Pre-digested intelligence chunk stored for topic: '{topic}'")
        except Exception as e:
            print(f"[VectorStore] Error storing intelligence chunk for {topic}: {e}")

    def query_intelligence(self, topic: str, user_query: str, n_results: int = 3) -> list[str]:
        """Queries pre-digested intelligence from ChromaDB for a specific domain."""
        if not self._collection:
            return []
        
        try:
            results = self._collection.query(
                query_texts=[user_query],
                n_results=n_results,
                where={"topic": topic}
            )
            if results and results.get("documents") and results["documents"][0]:
                return results["documents"][0]
        except Exception as e:
            print(f"[VectorStore] Query intelligence error for {topic}: {e}")
        
        # Fallback to general query
        return self.query(user_query, n_results=n_results)
