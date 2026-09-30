import os
import re
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
    - Automatic thinking process / chain-of-thought stripping to guarantee clean, direct user responses.
    - Expanded max_tokens (2500) to prevent truncation of guides, code, and long-form analysis.
    - Official OpenRouter Free Models Router ('openrouter/free') with runtime dynamic model discovery.
    """

    # Official Groq Production Lineup (Verified Active) - 131,072 (131K) context window
    GROQ_MODELS = [
        {"id": "qwen/qwen3.8-27b", "context": 131072},
        {"id": "openai/gpt-oss-120b", "context": 131072},
        {"id": "openai/gpt-oss-20b", "context": 131072},
        {"id": "allam-2-7b", "context": 32768}
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
                        "HTTP-Referer": "http://localhost:8888",
                        "X-Title": "Pikachu AI Browser"
                    }
                )
            except Exception as e:
                print(f"[LLMClient] OpenRouter client init error: {e}")

    def _clean_response(self, text: str | None) -> str | None:
        """
        Strips internal reasoning scratchpads, thinking tokens, and metadata
        so that Pikachu AI only outputs clean, high-craft Markdown to the user.
        """
        if not text:
            return None

        cleaned = text.strip()

        # 1. Strip XML/HTML thinking tags: <think> ... </think>
        cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL).strip()

        # 2. Strip "User Safety: safe" preamble if present
        cleaned = re.sub(r'^User Safety:\s*safe\s*', '', cleaned, flags=re.IGNORECASE).strip()

        # 3. Strip raw Thinking Process / scratchpad blocks
        thinking_header = re.match(r'^(?:Here\'s a thinking process:?|Thinking Process:?|Thought Process:?)\s*\n', cleaned, flags=re.IGNORECASE)
        if thinking_header:
            # Check if there is an actual answer following the thought process
            # Match common transition boundaries: Markdown headers, bold titles, or greeting words
            match_start = re.search(r'\n\n(?=#|\*\*|[A-Z][a-z]+:|\b(?:Here|This|Welcome|Introduction|Overview|Guide|Kotlin|Python|FastAPI)\b)', cleaned)
            if match_start and len(cleaned[match_start.start():].strip()) > 40:
                cleaned = cleaned[match_start.start():].strip()
            else:
                # If only thinking lines exist (model truncated mid-thought), strip meta-reasoning lines
                lines = []
                for line in cleaned.splitlines():
                    lower = line.strip().lower()
                    if not any(lower.startswith(prefix) for prefix in [
                        'thinking process', 'analyze the request', 'analyze the context',
                        'determine the target', "let's analyze", "let's look closely",
                        'structure of the starting guide', 'structure of the guide'
                    ]):
                        lines.append(line)
                cleaned = "\n".join(lines).strip()

        if len(cleaned) < 20:
            return None

        return cleaned

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
                        max_tokens=2500,
                        temperature=0.2,
                        timeout=12.0
                    )
                    content = resp.choices[0].message.content
                    clean_content = self._clean_response(content)
                    if clean_content:
                        return f"{clean_content}\n\n<span style='color:#7d8590; font-size:11px;'>Engine: Groq ({model_id} · {m['context'] // 1024}K context)</span>"
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
                    "max_tokens": 2500,
                    "temperature=0.2": 0.2
                }
                with httpx.Client(timeout=12.0) as client:
                    resp = client.post(f"{MISTRAL_BASE_URL}/chat/completions", headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data["choices"][0]["message"]["content"]
                        clean_content = self._clean_response(content)
                        if clean_content:
                            return f"{clean_content}\n\n<span style='color:#7d8590; font-size:11px;'>Engine: Mistral AI ({model_id} · {m['context'] // 1024}K context)</span>"
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
                max_tokens=2500,
                temperature=0.2,
                timeout=18.0
            )
            msg = resp.choices[0].message
            content = msg.content
            if not content or not content.strip():
                content = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)

            clean_content = self._clean_response(content)
            if clean_content:
                chosen_model = getattr(resp, "model", self.openrouter_free_model)
                return f"{clean_content}\n\n<span style='color:#7d8590; font-size:11px;'>Engine: OpenRouter ({chosen_model})</span>"
            else:
                print(f"[LLMClient] Free router returned non-clean response, falling back to dynamic model discovery...")
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
                    # Filter out restricted, safety, or thinking-only models
                    discovered_models = [
                        m for m in data 
                        if ":free" in m.get("id", "") 
                        and "safety" not in m.get("id", "").lower()
                        and "inkling" not in m.get("id", "").lower()
                    ]
                    discovered_models.sort(key=lambda x: x.get("context_length", 0), reverse=True)

                    headers = {
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "HTTP-Referer": "http://localhost:8888",
                        "X-Title": "Pikachu AI Browser",
                        "Content-Type": "application/json"
                    }

                    for m in discovered_models[:10]:
                        model_id = m["id"]
                        ctx_len = m.get("context_length", 0)
                        try:
                            payload = {
                                "model": model_id,
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_query}
                                ],
                                "max_tokens": 2500,
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
                                    clean_content = self._clean_response(content)
                                    if clean_content:
                                        ctx_str = f" · {ctx_len // 1024}K context" if ctx_len else ""
                                        return f"{clean_content}\n\n<span style='color:#7d8590; font-size:11px;'>Engine: OpenRouter ({model_id}{ctx_str})</span>"
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
        Executes cascade failover based on strict provider priority:
        1. Groq (Primary / Default)
        2. OpenRouter (Secondary)
        3. Mistral (Tertiary)
        """
        providers = ["groq", "openrouter", "mistral"]
        if self.primary_provider in providers and self.primary_provider != "groq":
            providers.remove(self.primary_provider)
            providers.insert(0, self.primary_provider)

        for provider in providers:
            if provider == "groq" and not self.groq_disabled:
                answer = self._call_groq(system_prompt, user_query)
                if answer:
                    return answer
            elif provider == "openrouter":
                answer = self._call_openrouter_free_router(system_prompt, user_query)
                if answer:
                    return answer
            elif provider == "mistral" and not self.mistral_disabled:
                answer = self._call_mistral(system_prompt, user_query)
                if answer:
                    return answer

        return (
            "⚠️ **All LLM API Providers Failed or Rate-Limited.**\n\n"
            "- **Groq**: Rate-limited or busy.\n"
            "- **OpenRouter Free Tier**: Upstream free models are currently at capacity.\n"
            "- **Mistral AI**: Invalid or rate-limited `MISTRAL_API_KEY`."
        )

    def stream_query(self, system_prompt: str, user_query: str, chunk_callback=None) -> str:
        """
        Streams response chunks in real-time following priority cascade:
        1. Groq Streaming (Default)
        2. OpenRouter Streaming (Secondary)
        3. Mistral / Non-Streaming Cascade (Tertiary)

        Emits each token chunk via chunk_callback(chunk_str).
        Filters out <think> tags in real-time so thinking scratchpads are never shown.
        Returns the complete final response string.
        """
        # 1. Attempt Groq streaming (Primary / Default)
        if not self.groq_disabled and self.groq_key and self.groq_key != "your-groq-api-key":
            try:
                print(f"[LLMClient] (Primary) Streaming from Groq...")
                client = Groq(api_key=self.groq_key)
                for m in self.GROQ_MODELS:
                    model_id = m["id"]
                    try:
                        stream = client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_query}
                            ],
                            model=model_id,
                            max_tokens=2500,
                            temperature=0.2,
                            stream=True,
                            timeout=15.0
                        )
                        full_text = []
                        inside_think = False
                        stream_count = 0
                        for chunk in stream:
                            token = chunk.choices[0].delta.content if chunk.choices else None
                            if not token:
                                continue
                            if "<think>" in token:
                                inside_think = True
                                token = token.split("<think>")[0]
                            if "</think>" in token:
                                inside_think = False
                                token = token.split("</think>")[-1]
                            if inside_think or not token:
                                continue
                            full_text.append(token)
                            if chunk_callback:
                                chunk_callback(token)
                            stream_count += 1

                        joined = "".join(full_text)
                        cleaned = self._clean_response(joined)
                        if cleaned and len(cleaned) > 20:
                            engine_note = f"\n\n<span style='color:#7d8590; font-size:11px;'>Engine: Groq ({model_id})</span>"
                            if chunk_callback:
                                chunk_callback(engine_note)
                            return f"{cleaned}{engine_note}"
                    except Exception as ge:
                        print(f"[LLMClient] Groq {model_id} streaming error: {ge}")
                        if "organization_restricted" in str(ge).lower():
                            self.groq_disabled = True
                            break
                        continue
            except Exception as ge:
                print(f"[LLMClient] Groq client stream error: {ge}")

        # 2. Attempt OpenRouter streaming (Secondary)
        if self._openrouter_client:
            try:
                print(f"[LLMClient] (Secondary) Streaming from OpenRouter ({self.openrouter_free_model})...")
                stream = self._openrouter_client.chat.completions.create(
                    model=self.openrouter_free_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    max_tokens=2500,
                    temperature=0.2,
                    stream=True,
                    timeout=20.0
                )

                full_text = []
                inside_think = False
                stream_count = 0

                for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if not delta:
                        continue
                    token = getattr(delta, "content", None)
                    if not token:
                        continue

                    # Filter <think> blocks in real-time
                    if "<think>" in token:
                        inside_think = True
                        token = token.split("<think>")[0]
                    if "</think>" in token:
                        inside_think = False
                        token = token.split("</think>")[-1]

                    if inside_think or not token:
                        continue

                    full_text.append(token)
                    if chunk_callback:
                        chunk_callback(token)
                    stream_count += 1

                joined = "".join(full_text)
                cleaned = self._clean_response(joined)
                if cleaned and len(cleaned) > 20:
                    engine_note = f"\n\n<span style='color:#7d8590; font-size:11px;'>Engine: OpenRouter ({self.openrouter_free_model})</span>"
                    if chunk_callback:
                        chunk_callback(engine_note)
                    return f"{cleaned}{engine_note}"
            except Exception as e:
                print(f"[LLMClient] OpenRouter streaming error: {e}")

        # 3. Fallback to resilient non-streaming cascade (Tertiary Mistral / Cascade)
        print("[LLMClient] (Tertiary) Falling back to resilient cascade...")
        raw_res = self.query(system_prompt, user_query)
        clean_res = self._clean_response(raw_res) or raw_res

        if chunk_callback and clean_res:
            import time
            words = clean_res.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                chunk_callback(chunk)
                time.sleep(0.015)

        return clean_res

    def answer_verified_specialized_query(
        self,
        user_query: str,
        domain_title: str,
        chroma_context: str,
        tavily_context: str,
        chunk_callback = None
    ) -> str:
        """
        Synthesizes pre-digested ChromaDB telemetry and live Tavily 5-result verification feed
        into an authoritative, verified Markdown intelligence report.
        """
        bounded_chroma = chroma_context[:6000] if len(chroma_context) > 6000 else chroma_context
        bounded_tavily = tavily_context[:6000] if len(tavily_context) > 6000 else tavily_context

        system_prompt = (
            "You are Pikachu AI, a specialized real-time intelligence assistant dedicated strictly to:\n"
            "1. Locality News (Civic, municipal & regional updates)\n"
            "2. Trading Summary of the Week (Markets, indices, commodities & crypto)\n"
            "3. Weather Updates (Meteorological conditions, telemetry, forecasts)\n\n"
            f"Active Domain: {domain_title}\n\n"
            "You have access to two sources of intelligence:\n"
            "Source A: PRE-DIGESTED CHROMADB INTELLIGENCE (Stored beforehand in vector memory on background thread):\n"
            f"{bounded_chroma}\n\n"
            "Source B: LIVE TAVILY VERIFICATION FEED (Top 5 verified results, 250-character summary each):\n"
            f"{bounded_tavily}\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- Cross-verify the ChromaDB baseline against the live Tavily 5-result verification findings.\n"
            "- If there are any recent updates or changes, incorporate the verified Tavily facts.\n"
            "- Format your response professionally in Markdown using clear headings, metric highlights, and bullet points.\n"
            "- Reference verified sources [1], [2], [3] when citing specific figures, events, or telemetry.\n"
            "- Output ONLY the final response in Markdown directly to the user.\n"
            "- Do NOT output any internal thoughts, reasoning steps, or 'Thinking Process:' scratchpads."
        )
        return self.stream_query(system_prompt, user_query, chunk_callback=chunk_callback)

    def answer_doc_query(self, user_query: str, context: str, chunk_callback = None) -> str:
        bounded_context = context[:8000] if len(context) > 8000 else context
        system_prompt = (
            "You are Pikachu AI, an intelligent agentic assistant reviewing the active web document.\n"
            "Provide a comprehensive, accurate, and structured answer to the user's request using the provided context as primary reference.\n"
            "Format your answer cleanly with Markdown headings, bullet points, and code examples where applicable.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- Output ONLY the final response in Markdown directly to the user.\n"
            "- Do NOT output any internal thoughts, reasoning steps, or 'Thinking Process:' scratchpads.\n\n"
            f"Context Excerpts:\n{bounded_context}"
        )
        return self.stream_query(system_prompt, user_query, chunk_callback=chunk_callback)

    def answer_searxng_query(self, user_query: str, web_context: str, search_provider: str = "SearXNG", chunk_callback = None) -> str:
        bounded_web = web_context[:8000] if len(web_context) > 8000 else web_context
        system_prompt = (
            "You are Pikachu AI, an agentic deep web research assistant.\n"
            f"The user query was researched using live multi-engine web search via {search_provider}.\n"
            "Summarize and answer the user's query comprehensively using the web search excerpts provided below.\n"
            "Cite web sources with numbers [1], [2] referencing URLs in the excerpts, and format cleanly in Markdown.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- Output ONLY the final response in Markdown directly to the user.\n"
            "- Do NOT output any internal thoughts, reasoning steps, or 'Thinking Process:' scratchpads.\n\n"
            f"Web Search Results:\n{bounded_web}"
        )
        return self.stream_query(system_prompt, user_query, chunk_callback=chunk_callback)

    def answer_general_query(self, user_query: str, chunk_callback = None) -> str:
        system_prompt = (
            "You are Pikachu AI, a helpful agentic web assistant.\n"
            "Answer the user's prompt helpfully, comprehensively, and accurately using rich Markdown formatting.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- Output ONLY the final response in Markdown directly to the user.\n"
            "- Do NOT output any internal thoughts, reasoning steps, or 'Thinking Process:' scratchpads."
        )
        return self.stream_query(system_prompt, user_query, chunk_callback=chunk_callback)

LLMClient = ResilientLLMClient

