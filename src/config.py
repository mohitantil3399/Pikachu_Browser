import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# --- APP CONSTANTS ---
APP_TITLE = "Pikachu AI - Agentic Web & Research Browser"
DEFAULT_DOC_URL = "https://fastapi.tiangolo.com/tutorial/first-steps/"
SEARXNG_ENDPOINT = os.getenv("SEARXNG_ENDPOINT", "http://localhost:8080/search")

# --- LLM PROVIDER ENDPOINTS & KEYS ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("Groq_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_BASE_URL = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_FREE_MODEL = os.getenv("OPENROUTER_FREE_MODEL", "openrouter/free")

PRIMARY_LLM_PROVIDER = os.getenv("PRIMARY_LLM_PROVIDER", "openrouter").lower()

# --- VECTOR STORE CONFIG ---
CHROMA_DB_PATH = str(ROOT_DIR / "chroma_db_cache")
LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
COLLECTION_NAME = "active_doc_collection"

# --- CHUNKING CONFIG ---
DEFAULT_CHUNK_SIZE = 600
DEFAULT_CHUNK_OVERLAP = 100
BATCH_SIZE = 32
