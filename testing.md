# 🧪 Pikachu AI Agentic Browser - Comprehensive Testing & Demonstration Guide

This guide provides step-by-step instructions to test every feature of the **Pikachu AI Agentic Browser**, verify zero-download embeddings, confirm ChromaDB deduplication, test SearXNG multi-engine web research, and demonstrate the platform live.

---

## 🌐 Demonstration Website
* **Target Website**: `https://fastapi.tiangolo.com/tutorial/first-steps/`
* **Why this page**: Clean typography, rich technical content, code examples (`from fastapi import FastAPI`), and clear structure. Ideal for both automated testing and live executive demos.

---

## 🚀 Pre-Flight Checklist

1. **Verify SearXNG Docker Container is Running**:
   ```powershell
   docker ps
   ```
   *Expected Output*: Container `searxng` running on `0.0.0.0:8080->8080/tcp`.

2. **Launch Pikachu AI Browser**:
   ```powershell
   d:\softwares\SearXNG\.venv\Scripts\python.exe d:\softwares\SearXNG\app.py
   ```
   *Expected Result*: Modern Catppuccin Mocha dark mode window opens with the FastAPI documentation and the floating Pikachu AI Assistant drawer in the bottom-right corner.

---

## 📋 Test Matrix & Demonstration Scenarios

### Test 1: Batch Ingestion & Local ONNX Embedding (Zero Downloads)
* **Action**: Observe the Pikachu AI drawer as `https://fastapi.tiangolo.com/tutorial/first-steps/` loads.
* **What Happens**:
  1. The `IndexerWorker` fetches the webpage text using `trafilatura`.
  2. The text is split into sliding window chunks (approx. 500 characters, 100 character overlap).
  3. The local ONNX model (`all-MiniLM-L6-v2`) in your cache generates 384-dimensional embeddings in batches of 16 chunks.
  4. The progress bar updates incrementally until reaching **100%**.
  5. The status displays: `Indexed X chunks in ChromaDB!`.
* **Verification**: No Hugging Face models are downloaded over the internet; it loads directly from `C:\Users\MOHIT\.cache\chroma\onnx_models\all-MiniLM-L6-v2`.

---

### Test 2: ChromaDB Caching & Deduplication (Requirement 6)
* **Goal**: Confirm that ChromaDB stores embeddings **ONLY** if it does not already contain them.
* **Action**:
  1. In the address bar, type `https://fastapi.tiangolo.com/` (or press **🔄 Reload**).
  2. Then navigate back to `https://fastapi.tiangolo.com/tutorial/first-steps/`.
* **Expected Result**:
  * Instead of re-extracting and re-embedding, the drawer immediately displays:
    `⚡ VectorDB Cache Hit (X chunks)`
  * Progress bar snaps to **100%** instantly.
  * No CPU-intensive embedding calculations are repeated.

---

### Test 3: Page Context RAG Mode
* **Goal**: Ask questions answered strictly by the current documentation page.
* **Mode**: Ensure `📄 Page RAG` is selected in the drawer.
* **Demo Prompt**:
  > *"What are the 5 first steps to create and run a minimal FastAPI app with uvicorn?"*
* **Expected Answer**:
  * Step 1: Import FastAPI (`from fastapi import FastAPI`).
  * Step 2: Create a `FastAPI` instance (`app = FastAPI()`).
  * Step 3: Define a path operation decorator (`@app.get("/")`).
  * Step 4: Define the path operation function (`async def root(): return {"message": "Hello World"}`).
  * Step 5: Run the development server (`uvicorn main:app --reload`).
  * Response footer displays provider info (e.g., `⚡ Powered by OpenRouter (google/gemma-4-26b-a4b-it:free)` or `Groq`).

---

### Test 4: SearXNG Multi-Engine Deep Web Research
* **Goal**: Test live private multi-engine web search through local Docker SearXNG on port 8080.
* **Action**:
  1. Click the **`🌐 SearXNG Deep Search`** mode button in the drawer.
  2. The input placeholder changes to *"Search web via local SearXNG engine..."*.
* **Demo Prompt**:
  > *"What are the best practices for structuring large FastAPI microservices in 2026?"*
* **Expected Result**:
  * `SearxngWorker` queries `http://localhost:8080/search?q=...&format=json`.
  * Multi-engine search results from Google, DuckDuckGo, Bing, etc. are aggregated.
  * Pikachu AI synthesizes a clear research summary with numbered citations `[1]`, `[2]` linking back to source URLs.

---

### Test 5: General AI Mode
* **Goal**: Test conversational general assistance without web or page context constraints.
* **Action**:
  1. Click **`💬 General AI`**.
* **Demo Prompt**:
  > *"Compare Python typing with Pydantic v2 in 3 short bullet points."*
* **Expected Result**:
  * Concise, formatted explanation formatted in clean Markdown.

---

### Test 6: Multi-Tier Failover Resilience (Groq ➔ Mistral ➔ OpenRouter)
* **Goal**: Verify that if an API key expires, gets rate-limited, or encounters restrictions, the app does not crash.
* **How It Works**:
  1. The client first tries **Groq** models (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`).
  2. If Groq encounters restricted organization / 400 error, it immediately cascades to **Mistral AI** (`mistral-small-latest`, `open-mistral-7b`).
  3. If Mistral returns 401 invalid key, it automatically routes to **OpenRouter Free Tier** (`google/gemma-4-26b-a4b-it:free`, `qwen/qwen3.8-27b:free`, `liquid/lfm-2.5-2.6b:free`).
  4. The request succeeds seamlessly without throwing errors to the user interface.

---

### Test 7: Export Conversation (.txt)
* **Action**:
  1. Click **`💾 Export (.txt)`** in the bottom-right corner of the drawer.
  2. Choose a destination folder and filename.
* **Expected Result**:
  * A structured `.txt` file is generated containing:
    * Export timestamp
    * Source URL (`https://fastapi.tiangolo.com/tutorial/first-steps/`)
    * Active mode used
    * Complete dialogue transcript
  * The status bar displays: `Exported to Pikachu_Session_YYYYMMDD_HHMMSS.txt`.
