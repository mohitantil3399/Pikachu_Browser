import httpx
import logging
from src.config import (
    SEARXNG_ENDPOINT,
    TAVILY_API_KEY,
    TAVILY_SEARCH_ENDPOINT,
    PRIMARY_SEARCH_PROVIDER,
    BACKUP_SEARCH_PROVIDER
)

logger = logging.getLogger("SearchClient")

class ResilientSearchClient:
    """
    Unified, failure-resistant search client for Pikachu AI Browser.
    - Primary Search Engine: Local SearXNG instance (http://localhost:8080/search).
    - Default Backup Search Engine: Tavily Search API (https://api.tavily.com/search).
    
    If SearXNG is offline, unreachable, rate-limited, or returns 0 results,
    the client seamlessly cascades to Tavily Search so AI Agent Pikachu
    never fails to answer web research questions.
    """

    def __init__(
        self,
        searxng_endpoint: str = SEARXNG_ENDPOINT,
        tavily_api_key: str = TAVILY_API_KEY,
        tavily_endpoint: str = TAVILY_SEARCH_ENDPOINT
    ):
        self.searxng_endpoint = searxng_endpoint
        self.tavily_api_key = tavily_api_key
        self.tavily_endpoint = tavily_endpoint
        self.primary_provider = PRIMARY_SEARCH_PROVIDER
        self.backup_provider = BACKUP_SEARCH_PROVIDER

        # Cached provider status
        self.searxng_online = None
        self.last_provider_used = "none"

    def check_searxng_health(self, timeout: float = 1.5) -> bool:
        """Quick health check to determine if local SearXNG Docker is accessible."""
        try:
            base_url = self.searxng_endpoint.rsplit("/search", 1)[0] if "/search" in self.searxng_endpoint else self.searxng_endpoint
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(base_url)
                self.searxng_online = (resp.status_code in (200, 301, 302))
                return self.searxng_online
        except Exception:
            self.searxng_online = False
            return False

    def search_searxng(self, query: str, num_results: int = 5, timeout: float = 2.8) -> dict:
        """Executes search on local SearXNG instance."""
        try:
            params = {
                "q": query,
                "format": "json"
            }
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(self.searxng_endpoint, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_results = data.get("results", [])[:num_results]
                    if not raw_results:
                        return {
                            "success": False,
                            "error": "SearXNG returned 0 results"
                        }

                    formatted_results = []
                    for item in raw_results:
                        formatted_results.append({
                            "title": item.get("title", "No Title"),
                            "url": item.get("url", ""),
                            "content": item.get("content", ""),
                            "engine": item.get("engine", "searxng"),
                            "provider": "SearXNG"
                        })
                    self.searxng_online = True
                    return {
                        "success": True,
                        "provider": "SearXNG",
                        "query": query,
                        "results": formatted_results
                    }
                else:
                    return {
                        "success": False,
                        "error": f"SearXNG returned HTTP {resp.status_code}"
                    }
        except Exception as e:
            self.searxng_online = False
            return {
                "success": False,
                "error": f"SearXNG connection error: {str(e)}"
            }

    def search_tavily(self, query: str, num_results: int = 5, timeout: float = 10.0) -> dict:
        """Executes search via Tavily Search API as reliable cloud backup."""
        if not self.tavily_api_key:
            return {
                "success": False,
                "provider": "Tavily",
                "error": "TAVILY_API_KEY is not configured in environment"
            }

        try:
            payload = {
                "api_key": self.tavily_api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": num_results,
                "include_answer": False
            }
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(self.tavily_endpoint, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_results = data.get("results", [])[:num_results]
                    formatted_results = []
                    for item in raw_results:
                        formatted_results.append({
                            "title": item.get("title", "No Title"),
                            "url": item.get("url", ""),
                            "content": item.get("content", ""),
                            "engine": "tavily",
                            "provider": "Tavily"
                        })
                    return {
                        "success": True,
                        "provider": "Tavily (Backup)",
                        "query": query,
                        "results": formatted_results
                    }
                else:
                    return {
                        "success": False,
                        "provider": "Tavily",
                        "error": f"Tavily returned HTTP {resp.status_code}: {resp.text[:100]}"
                    }
        except Exception as e:
            return {
                "success": False,
                "provider": "Tavily",
                "error": f"Tavily API request error: {str(e)}"
            }

    def verify_with_tavily(self, query: str, max_results: int = 5, max_chars_per_summary: int = 250, timeout: float = 8.0) -> dict:
        """
        Fetches top 5 results from Tavily with strictly 250-character summaries
        for cross-verifying pre-digested intelligence before Pikachu AI answers.
        """
        if not self.tavily_api_key:
            return {
                "success": False,
                "error": "TAVILY_API_KEY not configured",
                "results": []
            }

        try:
            payload = {
                "api_key": self.tavily_api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_answer": False
            }
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(self.tavily_endpoint, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_results = data.get("results", [])[:max_results]
                    verified = []
                    for item in raw_results:
                        full_content = item.get("content", "") or ""
                        # Strict 250 characters summary per user specification
                        truncated_summary = full_content[:max_chars_per_summary].strip()
                        verified.append({
                            "title": item.get("title", "No Title"),
                            "url": item.get("url", ""),
                            "summary": truncated_summary,
                            "score": item.get("score", 0.0)
                        })
                    return {
                        "success": True,
                        "query": query,
                        "results": verified
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Tavily HTTP {resp.status_code}",
                        "results": []
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    def format_verification_context(self, tavily_res: dict) -> str:
        """Formats the top 5 Tavily results (250-char summaries) into structured verification context."""
        if not tavily_res.get("success") or not tavily_res.get("results"):
            return "No Tavily verification results available."

        lines = ["Live Tavily Verification Feed (Top 5 Results · 250 Chars Summary):"]
        for i, item in enumerate(tavily_res["results"], 1):
            lines.append(
                f"[{i}] {item.get('title')}\n"
                f"    Summary: {item.get('summary')}\n"
                f"    Source URL: {item.get('url')}\n"
            )
        return "\n".join(lines)

    def search(self, query: str, num_results: int = 5) -> dict:
        """
        Executes search with automatic failover:
        1. Attempt SearXNG (Primary Local Engine)
        2. If SearXNG is down, unreachable, or returns 0 results -> Seamlessly fallback to Tavily
        """
        searxng_err = None

        # Step 1: Attempt Primary (SearXNG)
        res = self.search_searxng(query, num_results=num_results)
        if res.get("success") and res.get("results"):
            self.last_provider_used = "SearXNG"
            return res

        searxng_err = res.get("error", "SearXNG search returned no results")
        print(f"[SearchClient] Primary SearXNG unavailable ({searxng_err}). Seamlessly activating Tavily Backup Search...")

        # Step 2: Attempt Default Backup (Tavily)
        tavily_res = self.search_tavily(query, num_results=num_results)
        if tavily_res.get("success") and tavily_res.get("results"):
            self.last_provider_used = "Tavily (Backup)"
            tavily_res["backup_activated"] = True
            tavily_res["primary_error"] = searxng_err
            return tavily_res

        # Step 3: Both failed
        tavily_err = tavily_res.get("error", "Tavily returned no results")
        return {
            "success": False,
            "error": f"Search failed on both engines:\n- SearXNG: {searxng_err}\n- Tavily Backup: {tavily_err}"
        }

    def format_results_as_context(self, search_res: dict) -> str:
        """Formats search output into structured context for Pikachu AI prompt."""
        if not search_res.get("success") or not search_res.get("results"):
            return "No web search results available."

        provider = search_res.get("provider", "Web")
        header = "Web Search Context Excerpts:\n"

        context_parts = [header]
        for i, item in enumerate(search_res["results"], 1):
            source_engine = item.get("engine") or provider
            context_parts.append(
                f"[{i}] Title: {item.get('title', 'No Title')}\n"
                f"    URL: {item.get('url', '')}\n"
                f"    Engine/Source: {source_engine}\n"
                f"    Excerpt: {item.get('content', '')}\n"
            )
        return "\n".join(context_parts)

# Alias for backward compatibility across all modules
SearxngClient = ResilientSearchClient
UnifiedSearchClient = ResilientSearchClient
