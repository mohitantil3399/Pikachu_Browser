import os
import httpx
from groq import Groq
from openai import OpenAI
from src.config import (
    GROQ_API_KEY, GROQ_BASE_URL,
    MISTRAL_API_KEY, MISTRAL_BASE_URL,
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_FREE_MODEL,
    PRIMARY_LLM_PROVIDER
)

class ResilientLLMClient:
    """
    Production-grade failure-resistant LLM client following 2026 provider specifications.
    Features:
    - Smart circuit-breakers to detect account-level restrictions or invalid keys and stop redundant model hammering.
    - Default priority routing via PRIMARY_LLM_PROVIDER (defaults to 'openrouter').
    - Official OpenRouter Free Models Router ('openrouter/free') with runtime dynamic model discovery.
    """

    # Official Groq Production Lineup (2026) - 131,072 (131K) context window
    GROQ_MODELS = [
        {"id": "llama-3.3-70b-versatile", "context": 131072},
        {"id": "llama-3.1-8b-instant", "context": 131072},
        {"id": "qwen/qwen3.8-27b", "context": 131072},
        {"id": "openai/gpt-oss-120b", "context": 131072},
        {"id": "openai/gpt-oss-20b", "context": 131072}
    ]

    # Official Mistral AI Production Lineup (2026) - 128K-256K context window
    MISTRAL_MODELS = [
        {"id": "mistral-small-latest", "context": 256000},
        {"id": "mistral-medium-latest", "context": 256000},
        {"id": "mistral-large-latest", "context": 256000},
        {"id": "codestral-latest", "context": 128000}
    ]

    def __init__(self):
        self.groq_key = GROQ_API_KEY
        self.mistral_key = MISTRAL_API_KEY
        self.openrouter_key = OPENROUTER_API_KEY
        self.openrouter_base_url = OPENROUTER_BASE_URL
        self.openrouter_free_model = OPENROUTER_FREE_MODEL
        self.primary_provider = PRIMARY_LLM_PROVIDER

        # Provider health circuit-breakers
        self.groq_disabled = False
        self.mistral_disabled = False

        # Initialize OpenAI-compatible OpenRouter client pointing directly to base URL
        self._openrouter_client = None
        if self.openrouter_key:
            try:
                self._openrouter_client = OpenAI(
                    api_key=self.openrouter_key,
                    base_url=self.openrouter_base_url,
                    default_headers={
                        "HTTP-Referer": "http://localhost:8080",
                        "X-Title": "Pikachu AI Browser"
                    }
                )
            except Exception as e:
                print(f"[LLMClient] OpenRouter client init error: {e}")

    def _call_groq(self, system_prompt: str, user_query: str) -> str | None:
        """Attempts completion across official Groq production models with circuit-breaker."""
        if self.groq_disabled or not self.groq_key or self.groq_key == "your-groq-api-key":
            return None

        try:
            client = Groq(api_key=self.groq_key)
            for m in self.GROQ_MODELS:
                model_id = m["id"]
                try:
                    resp = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_query}
                        ],
                        model=model_id,
                        max_tokens=800,
                        temperature=0.2,
                        timeout=8.0
                    )
                    content = resp.choices[0].message.content
                    if content and content.strip():
                        return f"{content.strip()}\n\n<span style='color:#7d8590; font-size:11px;'>Engine: Groq ({model_id} · {m['context'] // 1024}K context)</span>"
                except Exception as e:
                    err_msg = str(e).lower()
                    if "organization_restricted" in err_msg or "invalid_api_key" in err_msg or "deactivated" in err_msg:
                        print(f"[LLMClient] Groq account restricted or key invalid ({e}). Circuit breaker active: disabling Groq.")
                        self.groq_disabled = True
                        break  # Stop trying other Groq models immediately!
                    print(f"[LLMClient] Groq {model_id} error: {e}")
                    continue
        except Exception as e:
            print(f"[LLMClient] Groq client error: {e}")
            self.groq_disabled = True
        return None

    def _call_mistral(self, system_prompt: str, user_query: str) -> str | None:
        """Attempts completion across official Mistral AI models with circuit-breaker."""
        if self.mistral_disabled or not self.mistral_key:
            return None

        headers = {
            "Authorization": f"Bearer {self.mistral_key}",
            "Content-Type": "application/json"
        }

        for m in self.MISTRAL_MODELS:
            model_id = m["id"]
            try:
                payload = {
                    "model": model_id,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    "max_tokens": 800,
                    "temperature": 0.2
                }
                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(f"{MISTRAL_BASE_URL}/chat/completions", headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        if content and content.strip():
                            return f"{content.strip()}\n\n<span style='color:#7d8590; font-size:11px;'>Engine: Mistral AI ({model_id} · {m['context'] // 1024}K context)</span>"
                    elif resp.status_code in (401, 403):
                        print(f"[LLMClient] Mistral API Key unauthorized/invalid (HTTP {resp.status_code}). Circuit breaker active: disabling Mistral.")
                        self.mistral_disabled = True
                        break  # Stop trying other Mistral models immediately!
                    else:
                        print(f"[LLMClient] Mistral {model_id} HTTP {resp.status_code}: {resp.text[:80]}")
            except Exception as e:
                print(f"[LLMClient] Mistral {model_id} exception: {e}")
                continue
        return None

    def _call_openrouter_free_router(self, system_prompt: str, user_query: str) -> str | None:
        """
        Calls OpenRouter's official Free Router endpoint ('openrouter/free').
        OpenRouter automatically selects the best currently active free model.
        """
        if not self._openrouter_client:
            return None

        try:
            print(f"[LLMClient] Querying OpenRouter Free Models Router ({self.openrouter_free_model})...")
            resp = self._openrouter_client.chat.completions.create(
                model=self.openrouter_free_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                max_tokens=800,
                temperature=0.2,
                timeout=16.0
            )
            msg = resp.choices[0].message
            content = msg.content
            if not content or not content.strip():
                content = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)

            if content and content.strip() and not content.strip().startswith("User Safety:"):
                chosen_model = getattr(resp, "model", self.openrouter_free_model)
                return f"{content.strip()}\n\n<span style='color:#7d8590; font-size:11px;'>Engine: OpenRouter ({chosen_model})</span>"
            else:
                print(f"[LLMClient] Free router returned safety/empty message, falling back to dynamic model discovery...")
        except Exception as e:
            print(f"[LLMClient] OpenRouter free router exception: {e}")

        # Fallback: Dynamically query GET /models to discover all currently active free models at runtime
        return self._call_openrouter_dynamic_discovery(system_prompt, user_query)

    def _call_openrouter_dynamic_discovery(self, system_prompt: str, user_query: str) -> str | None:
        """
        Dynamically discovers real-time available free models and their context limits
        from OpenRouter API at runtime. Automatically adapts as models update each month.
        """
        try:
            print("[LLMClient] Dynamically fetching real-time active free models from OpenRouter...")
            with httpx.Client(timeout=4.0) as client:
                r = client.get(f"{self.openrouter_base_url}/models")
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    discovered_models = [
                        m for m in data 
                        if ":free" in m.get("id", "") and "safety" not in m.get("id", "").lower()
                    ]
                    discovered_models.sort(key=lambda x: x.get("context_length", 0), reverse=True)

                    headers = {
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "HTTP-Referer": "http://localhost:8080",
                        "X-Title": "Pikachu AI Browser",
                        "Content-Type": "application/json"
                    }

                    for m in discovered_models[:8]:
                        model_id = m["id"]
                        ctx_len = m.get("context_length", 0)
                        try:
                            payload = {
                                "model": model_id,
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_query}
                                ],
                                "max_tokens": 800,
                                "temperature": 0.2
                            }
                            with httpx.Client(timeout=14.0) as req_client:
                                resp = req_client.post(
                                    f"{self.openrouter_base_url}/chat/completions",
                                    headers=headers,
                                    json=payload
                                )
                                if resp.status_code == 200:
                                    res_data = resp.json()
                                    msg = res_data.get("choices", [{}])[0].get("message", {})
                                    content = msg.get("content") or msg.get("reasoning")
                                    if content and content.strip() and not content.strip().startswith("User Safety:"):
                                        ctx_str = f" · {ctx_len // 1024}K context" if ctx_len else ""
                                        return f"{content.strip()}\n\n<span style='color:#7d8590; font-size:11px;'>Engine: OpenRouter ({model_id}{ctx_str})</span>"
                                elif resp.status_code == 429:
                                    print(f"[LLMClient] Model {model_id} busy (429), trying next dynamically discovered model...")
                        except Exception as req_err:
                            print(f"[LLMClient] Error with dynamic model {model_id}: {req_err}")
                            continue

        except Exception as disc_err:
            print(f"[LLMClient] Dynamic discovery error: {disc_err}")

        return None

    def query(self, system_prompt: str, user_query: str) -> str:
        """
        Executes cascade failover based on PRIMARY_LLM_PROVIDER priority:
        Default: OpenRouter Free Models Router -> Groq -> Mistral
        """
        providers = ["openrouter", "groq", "mistral"]
        if self.primary_provider in providers:
            # Move primary provider to front of queue
            providers.remove(self.primary_provider)
            providers.insert(0, self.primary_provider)

        for provider in providers:
            if provider == "openrouter":
                answer = self._call_openrouter_free_router(system_prompt, user_query)
                if answer:
                    return answer
            elif provider == "groq" and not self.groq_disabled:
                answer = self._call_groq(system_prompt, user_query)
                if answer:
                    return answer
            elif provider == "mistral" and not self.mistral_disabled:
                answer = self._call_mistral(system_prompt, user_query)
                if answer:
                    return answer

        return (
            "⚠️ **All LLM API Providers Failed or Rate-Limited.**\n\n"
            "- **Groq**: Organization restricted or inactive API key.\n"
            "- **Mistral AI**: Invalid or expired `MISTRAL_API_KEY`.\n"
            "- **OpenRouter Free Tier**: All active upstream free models are currently at capacity. Please try again shortly."
        )

    def answer_doc_query(self, user_query: str, context: str) -> str:
        bounded_context = context[:8000] if len(context) > 8000 else context
        system_prompt = (
            "You are Pikachu AI, an embedded intelligent assistant reviewing the current web documentation page.\n"
            "Answer the user's question accurately based ONLY on the provided context excerpts.\n"
            "Format your answer cleanly with Markdown headings, bullet points, and code blocks where applicable.\n\n"
            f"Context Excerpts:\n{bounded_context}"
        )
        return self.query(system_prompt, user_query)

    def answer_searxng_query(self, user_query: str, web_context: str, search_provider: str = "SearXNG") -> str:
        bounded_web = web_context[:8000] if len(web_context) > 8000 else web_context
        system_prompt = (
            "You are Pikachu AI, an agentic deep web research assistant.\n"
            f"The user query was researched using live multi-engine web search via {search_provider}.\n"
            "Summarize and answer the user's query comprehensively using the web search excerpts provided below.\n"
            "Cite web sources with numbers [1], [2] referencing URLs in the excerpts, and format cleanly in Markdown.\n\n"
            f"Web Search Results:\n{bounded_web}"
        )
        return self.query(system_prompt, user_query)

    def answer_general_query(self, user_query: str) -> str:
        system_prompt = (
            "You are Pikachu AI, a helpful agentic web assistant.\n"
            "Answer the user's prompt helpfully, concisely, and accurately using rich Markdown formatting."
        )
        return self.query(system_prompt, user_query)

LLMClient = ResilientLLMClient
