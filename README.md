# ⚡ Pikachu Browser

> **Agentic Web & Research Browser with TypeScript-Engineered Privacy Shield & Local Metasearch**

![Pikachu Browser Banner](src/ui/assets/icons/pikachu-logo.svg)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20QtWebEngine-green.svg)](https://wiki.qt.io/Qt_for_Python)
[![TypeScript](https://img.shields.io/badge/TypeScript-ES2022%20Shield-3178c6.svg)](https://www.typescriptlang.org/)
[![Docker SearXNG](https://img.shields.io/badge/Metasearch-SearXNG%20Docker-orange.svg)](https://github.com/searxng/searxng)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-yellow.svg)](LICENSE)

---

## 🌟 Overview

**Pikachu Browser** is an editorial, privacy-first desktop web browser built with **Python (PySide6 / QtWebEngine)** and a high-speed **TypeScript privacy engine**. Designed specifically for deep research and ad-free browsing, Pikachu combines:

1. **Zero-Ad Experience**: Brave-grade network request filtering combined with a TypeScript-compiled procedural scriptlet that neutralizes video ads (including YouTube pre-rolls and mid-rolls) and strips tracking pixels.
2. **Ephemeral Privacy by Default ("Shred on Close")**: Every window runs in an off-the-record profile. Cookies, caches, and visited links exist only in memory and are shredded on exit. Passwords are never saved or suggested.
3. **Local Metasearch Engine**: Native integration with a self-hosted **SearXNG** Docker instance (running on port `8888`) with seamless failover to **Tavily Search API**.
4. **Integrated AI Research Assistant & Active Page RAG**: A floating assistant drawer featuring fluid cubic-bezier animations, real-time page vector indexing via **ChromaDB**, zero-download local ONNX embeddings (`all-MiniLM-L6-v2`), and multi-LLM support (Groq, Mistral, OpenRouter).
5. **Agentic Click-to-Navigate Citations**: LLM-generated sources and search citations are clickable, routing directly into the active browser engine and indexing target documents.

---

## 🛡️ Privacy & Ad-Blocking Architecture

Pikachu Browser employs a **dual-layer defense system**:

```
                         Incoming Web Traffic
                                  │
                                  ▼
      ┌────────────────────────────────────────────────────────┐
      │     Layer 1: Network Request Interceptor (Python)      │
      │   • Blocks 250+ ad exchanges, trackers, telemetry      │
      │   • Injects Sec-GPC: 1 & DNT: 1 privacy headers        │
      └───────────────────────────┬────────────────────────────┘
                                  │
                                  ▼
      ┌────────────────────────────────────────────────────────┐
      │     Layer 2: TypeScript Shield Engine (Client JS)      │
      │   • Deep JSON.parse pruning of adPlacements & adSlots  │
      │   • Raw fetch response rewriting (/youtubei/v1/player) │
      │   • 50ms video watchdog: auto-skip, mute, ended event  │
      │   • Universal cosmetic CSS hiding of ad containers     │
      └───────────────────────────┬────────────────────────────┘
                                  │
                                  ▼
                     Clean, Ad-Free Webpage
```

### 1. Layer 1 — Socket-Level Request Blocker
* Intercepts all outgoing HTTP/HTTPS requests via `QWebEngineUrlRequestInterceptor`.
* Blocks known ad networks (DoubleClick, Google AdSense, Outbrain, Taboola, Meta Pixel, TikTok Telemetry, etc.).
* Enforces `DNT: 1` (Do Not Track) and `Sec-GPC: 1` (Global Privacy Control) headers across all allowed traffic.

### 2. Layer 2 — TypeScript Procedural Scriptlet
* Source written in [src/scripts/privacy_shield.ts](src/scripts/privacy_shield.ts) and transpiled to [privacy_shield.bundle.js](src/scripts/privacy_shield.bundle.js).
* **Root Payload Sanitization**: Intercepts `JSON.parse` and YouTube's `/youtubei/v1/player` API responses, replacing `"adPlacements"` and `"adSlots"` with `"no_adPlacements"` before player deserialization.
* **Instant YouTube Video Ad Neutralizer**: A 50ms loop that detects ad states, calls native `movie_player.skipAd()`, accelerates ad streams to 16x speed with auto-mute, and fires synthetic `ended` DOM events to transition directly to content.
* **Universal Cosmetic Filtering**: Completely hides companion banners, sponsored video cards, and anti-adblock modals.

### 3. Ephemeral Sessions
* All browsing is off-the-record (`NoPersistentCookies`, `NoCache`).
* Explicit cache purging and cookie wiping on window close.
* File downloads (PDFs, images, executables) invoke native Windows Save dialogs and function normally.

---

## 🚀 Quickstart Guide

### Prerequisites
* **Python 3.10+** (64-bit)
* **Docker Desktop** (for local SearXNG metasearch)
* **Node.js v20+** (for TypeScript shield builds)
* **Windows 10 / 11**

---

### Step 1: Clone the Repository
```powershell
git clone https://github.com/mohitantil3399/Pikachu_Browser.git
cd Pikachu_Browser
```

---

### Step 2: Set Up Python Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API keys:
```powershell
copy .env.example .env
```

Edit `.env`:
```ini
# LLM Providers (at least one required for AI chat)
GROQ_API_KEY="your-groq-api-key"
MISTRAL_API_KEY="your-mistral-api-key"
OPENROUTER_API_KEY="your-openrouter-api-key"

# Backup Search Provider
TAVILY_API_KEY="your-tavily-api-key"

# Local Metasearch Endpoint
SEARXNG_ENDPOINT="http://localhost:8888/search"
```

---

### Step 4: Launch SearXNG with Docker
Start the private SearXNG Docker container on host port **`8888`**:

```powershell
docker run -d -p 8888:8080 `
  -v "${PWD}\settings.yml:/etc/searxng/settings.yml" `
  --name searxng `
  searxng/searxng
```

Verify that SearXNG is running:
```powershell
Invoke-WebRequest -Uri "http://localhost:8888/search?q=test&format=json"
```

> **Note**: Port `8888` is used by default because ports `8080` and `8081` are frequently reserved by Windows Hyper-V / WinNAT dynamic excluded port ranges.

---

### Step 5: Build the TypeScript Privacy Shield (Optional)
The pre-compiled bundle is included in the repository. If you make modifications to [src/scripts/privacy_shield.ts](src/scripts/privacy_shield.ts), compile it via:

```powershell
node src/scripts/build.mjs
```

---

### Step 6: Launch Pikachu Browser
```powershell
.\.venv\Scripts\python.exe app.py
```

---

## 📁 Project Structure

```
Pikachu_Browser/
├── app.py                      # Application launcher & Qt loop
├── settings.yml                # SearXNG configuration (port 8888, JSON API enabled)
├── requirements.txt            # Python dependencies (PySide6, ChromaDB, httpx, etc.)
├── .env.example                # Template for API keys
├── src/
│   ├── config.py               # Central application constants & endpoints
│   ├── core/
│   │   ├── privacy_shield.py   # Layer 1 Network Interceptor & Profile hardener
│   │   ├── searxng_client.py   # Resilient metasearch client with Tavily fallback
│   │   ├── llm_client.py       # Multi-provider LLM connector (Groq/Mistral/OpenRouter)
│   │   └── vector_store.py     # ChromaDB manager with local ONNX embeddings
│   ├── scripts/
│   │   ├── privacy_shield.ts   # Layer 2 TypeScript privacy & ad neutralizer
│   │   ├── tsconfig.json       # Strict TypeScript configuration
│   │   ├── build.mjs           # Node.js transpiler & bundle generator
│   │   └── privacy_shield.bundle.js # Compiled production bundle injected by Qt
│   ├── ui/
│   │   ├── main_window.py      # Primary browser frame, URL bar & navigation
│   │   ├── chat_drawer.py      # Floating animated AI assistant drawer
│   │   ├── styles.py           # Editorial dark theme QSS stylesheet
│   │   └── assets/
│   │       ├── home.html       # Bespoke local landing homepage
│   │       └── icons/          # SVG navigation & assistant icons
│   └── workers/
│       ├── indexer_worker.py   # Background webpage parser & vector chunker
│       └── digest_worker.py    # Background domain intelligence digest thread
```

---

## ⌨️ Useful Commands & Workflows

### Managing SearXNG Container
```powershell
# Stop container
docker stop searxng

# Start existing container
docker start searxng

# View container logs
docker logs searxng

# Remove container
docker rm -f searxng
```

### Checking Active Embeddings Cache
Embeddings use the local `all-MiniLM-L6-v2` ONNX model. Cached vectors and pre-digested domain intelligence are stored in:
```
chroma_db_cache/
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/mohitantil3399/Pikachu_Browser/issues).

---

## 📜 License

This project is licensed under the terms of the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.
