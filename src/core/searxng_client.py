import httpx
from src.config import SEARXNG_ENDPOINT

class SearxngClient:
    """Client for local SearXNG Docker container (http://localhost:8080)."""
    def __init__(self, endpoint: str = SEARXNG_ENDPOINT):
        self.endpoint = endpoint

    def search(self, query: str, num_results: int = 5) -> dict:
        """
        Executes search on local SearXNG instance and returns structured results.
        """
        try:
            params = {
                "q": query,
                "format": "json"
            }
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(self.endpoint, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_results = data.get("results", [])[:num_results]
                    formatted_results = []
                    for item in raw_results:
                        formatted_results.append({
                            "title": item.get("title", "No Title"),
                            "url": item.get("url", ""),
                            "content": item.get("content", ""),
                            "engine": item.get("engine", "searxng")
                        })
                    return {
                        "success": True,
                        "query": query,
                        "results": formatted_results
                    }
                else:
                    return {
                        "success": False,
                        "error": f"SearXNG returned status code {resp.status_code}"
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Could not reach SearXNG at {self.endpoint}: {str(e)}"
            }

    def format_results_as_context(self, search_res: dict) -> str:
        """Formats SearXNG search output into structured context for LLM prompt."""
        if not search_res.get("success") or not search_res.get("results"):
            return "No web search results available."
        
        context_parts = []
        for i, item in enumerate(search_res["results"], 1):
            context_parts.append(
                f"[{i}] Title: {item['title']}\n"
                f"    URL: {item['url']}\n"
                f"    Excerpt: {item['content']}\n"
            )
        return "\n".join(context_parts)
