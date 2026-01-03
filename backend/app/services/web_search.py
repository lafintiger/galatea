"""Web Search Service - SearXNG and Perplexica integration"""
import httpx
from typing import Optional, Literal
from ..config import settings


class SearchResult:
    """A single search result"""
    def __init__(self, title: str, url: str, snippet: str, source: str = ""):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source
        }


class WebSearchService:
    """Unified web search service supporting SearXNG and Perplexica"""
    
    def __init__(self):
        self.searxng_url = f"http://{settings.searxng_host}:{settings.searxng_port}"
        self.perplexica_url = f"http://{settings.perplexica_host}:{settings.perplexica_port}"
        # Perplexica needs longer timeout as it does AI-powered search
        self.client = httpx.AsyncClient(timeout=120.0)
        # Cache for Perplexica providers
        self._providers_cache: dict = {}
        self._ollama_provider_id: Optional[str] = None
    
    async def _get_perplexica_providers(self) -> dict:
        """Fetch available providers from Perplexica API"""
        try:
            response = await self.client.get(
                f"{self.perplexica_url}/api/providers",
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            self._providers_cache = data
            
            # Find Ollama provider
            for provider in data.get("providers", []):
                if provider.get("name", "").lower() == "ollama":
                    self._ollama_provider_id = provider.get("id")
                    print(f"[Search] Found Ollama provider: {self._ollama_provider_id}")
                    break
            
            return data
        except Exception as e:
            print(f"[Search] Failed to get Perplexica providers: {e}")
            return {}
    
    async def _get_ollama_provider_id(self) -> Optional[str]:
        """Get cached Ollama provider ID or fetch it"""
        if not self._ollama_provider_id:
            await self._get_perplexica_providers()
        return self._ollama_provider_id
    
    async def search_searxng(self, query: str, num_results: int = 5) -> list[SearchResult]:
        """Search using SearXNG meta-search engine
        
        SearXNG aggregates results from multiple search engines.
        Returns raw results - use Ollama to summarize if needed.
        """
        print(f"[Search] SearXNG: Searching '{query}' at {self.searxng_url}")
        try:
            response = await self.client.get(
                f"{self.searxng_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "engines": "google,bing,duckduckgo",
                    "language": "en",
                },
                timeout=15.0  # Explicit shorter timeout
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"[Search] SearXNG: Got {len(data.get('results', []))} results")
            
            results = []
            for item in data.get("results", [])[:num_results]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source=item.get("engine", "searxng")
                ))
            
            return results
        except Exception as e:
            print(f"[Search] SearXNG error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def search_perplexica(
        self, 
        query: str, 
        sources: list[str] = ["web"],
        optimization_mode: str = "speed"
    ) -> dict:
        """Search using Perplexica AI-powered search (new API format)
        
        Perplexica provides AI-generated summaries with sources.
        
        API Reference: https://github.com/ItzCrazyKns/Perplexica/blob/master/docs/API/SEARCH.md
        
        Args:
            query: The search query
            sources: List of sources to search ["web", "academic", "discussions"]
            optimization_mode: "speed", "balanced", or "quality"
            
        Returns:
            Dict with 'answer' (AI summary) and 'sources' (list of sources)
        """
        try:
            # Get Ollama provider ID
            provider_id = await self._get_ollama_provider_id()
            
            if not provider_id:
                print("[Search] No Ollama provider configured in Perplexica")
                return {"answer": "", "sources": []}
            
            # Use Transformers for embedding (built-in, fast)
            # Use Ollama for chat (user's local models)
            embedding_provider_id = None
            embedding_model_key = "Xenova/all-MiniLM-L6-v2"  # Fast default
            
            for provider in self._providers_cache.get("providers", []):
                if provider.get("name", "").lower() == "transformers":
                    if provider.get("embeddingModels"):
                        embedding_provider_id = provider.get("id")
                        embedding_model_key = provider["embeddingModels"][0]["key"]
                        break
            
            if not embedding_provider_id:
                print("[Search] No Transformers provider for embeddings")
                return {"answer": "", "sources": []}
            
            # Use a fast small model for search summarization
            # Try to find qwen3:4b or similar small model
            chat_model_key = "qwen3:4b"  # Fast model for search
            for provider in self._providers_cache.get("providers", []):
                if provider.get("name", "").lower() == "ollama":
                    models = [m["key"] for m in provider.get("chatModels", [])]
                    # Prefer small fast models for search
                    for preferred in ["qwen3:4b", "phi4-mini:latest", "ministral-3:latest"]:
                        if preferred in models:
                            chat_model_key = preferred
                            break
                    break
            
            # New API format per docs
            request_body = {
                "chatModel": {
                    "providerId": provider_id,
                    "key": chat_model_key,
                },
                "embeddingModel": {
                    "providerId": embedding_provider_id,
                    "key": embedding_model_key,
                },
                "optimizationMode": optimization_mode,
                "sources": sources,  # New API uses "sources" not "focusMode"
                "query": query,
                "history": []
            }
            
            print(f"[Search] Perplexica request: query='{query}', model={chat_model_key}")
            
            # Use shorter timeout - fall back to SearXNG if Perplexica is slow
            response = await self.client.post(
                f"{self.perplexica_url}/api/search",
                json=request_body,
                timeout=45.0  # Shorter timeout for faster fallback
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"[Search] Perplexica response keys: {data.keys()}")
            
            # Parse response - Perplexica returns 'message' and 'sources'
            sources_list = []
            for src in data.get("sources", []):
                metadata = src.get("metadata", {})
                sources_list.append(SearchResult(
                    title=metadata.get("title", src.get("title", "")),
                    url=metadata.get("url", src.get("url", "")),
                    snippet=src.get("pageContent", src.get("content", ""))[:300],
                    source="perplexica"
                ).to_dict())
            
            return {
                "answer": data.get("message", ""),
                "sources": sources_list
            }
        except httpx.HTTPStatusError as e:
            print(f"[Search] Perplexica HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            return {"answer": "", "sources": []}
        except Exception as e:
            print(f"[Search] Perplexica error: {e}")
            return {"answer": "", "sources": []}
    
    async def search(
        self, 
        query: str, 
        provider: Literal["searxng", "perplexica", "auto"] = "auto",
        num_results: int = 5
    ) -> dict:
        """Unified search interface
        
        Args:
            query: Search query
            provider: Which search provider to use ("auto" now prefers SearXNG for reliability)
            num_results: Number of results (for SearXNG)
            
        Returns:
            Dict with 'results' and optionally 'summary'
        """
        # Use SearXNG first - it's faster and more reliable
        # Perplexica's bundled SearXNG has CAPTCHA issues
        print(f"[Search] Starting search for: '{query}' (provider={provider})")
        if provider in ["searxng", "auto"]:
            try:
                print(f"[Search] Checking SearXNG availability at {self.searxng_url}")
                available = await self.is_searxng_available()
                print(f"[Search] SearXNG available: {available}")
                if available:
                    print(f"[Search] Calling search_searxng...")
                    results = await self.search_searxng(query, num_results)
                    print(f"[Search] search_searxng returned {len(results) if results else 0} results")
                    if results:
                        return {
                            "provider": "searxng",
                            "query": query,
                            "summary": "",  # LLM will summarize
                            "results": [r.to_dict() for r in results]
                        }
                    print("[Search] SearXNG returned no results")
                else:
                    print("[Search] SearXNG not available")
            except Exception as e:
                print(f"[Search] SearXNG error: {e}")
                import traceback
                traceback.print_exc()
        
        # Try Perplexica as fallback (if explicitly requested or SearXNG failed)
        if provider == "perplexica":
            try:
                if await self.is_perplexica_available():
                    print(f"[Search] Trying Perplexica for: {query}")
                    data = await self.search_perplexica(query)
                    if data.get("sources") or data.get("answer"):
                        print(f"[Search] Perplexica returned results")
                        return {
                            "provider": "perplexica",
                            "query": query,
                            "summary": data.get("answer", ""),
                            "results": data.get("sources", [])
                        }
                    print("[Search] Perplexica returned no results")
            except Exception as e:
                print(f"[Search] Perplexica error: {e}")
        
        # Both failed
        print("[Search] No search services returned results")
        return {
            "provider": "none",
            "query": query,
            "summary": "",
            "results": [],
            "error": "Search services failed to return results"
        }
    
    async def is_searxng_available(self) -> bool:
        """Check if SearXNG is reachable"""
        try:
            response = await self.client.get(f"{self.searxng_url}/", timeout=5.0)
            return response.status_code == 200
        except:
            return False
    
    async def is_perplexica_available(self) -> bool:
        """Check if Perplexica is reachable via new API"""
        try:
            response = await self.client.get(f"{self.perplexica_url}/api/providers", timeout=5.0)
            return response.status_code == 200
        except:
            return False
    
    async def check_status(self) -> dict:
        """Check availability of search services"""
        searxng = await self.is_searxng_available()
        perplexica = await self.is_perplexica_available()
        
        # Get provider info if Perplexica is available
        perplexica_providers = []
        if perplexica:
            providers_data = await self._get_perplexica_providers()
            perplexica_providers = [p.get("name") for p in providers_data.get("providers", [])]
        
        return {
            "searxng": {
                "available": searxng,
                "url": self.searxng_url
            },
            "perplexica": {
                "available": perplexica,
                "url": self.perplexica_url,
                "providers": perplexica_providers,
                "ollama_configured": self._ollama_provider_id is not None
            }
        }
    
    def format_results_for_llm(self, search_data: dict) -> str:
        """Format search results as context for the LLM"""
        if not search_data.get("results"):
            return f"No search results found for: {search_data.get('query', 'unknown query')}"
        
        lines = []
        
        # If Perplexica provided a summary, use it directly
        if search_data.get("summary"):
            lines.append("=== WEB SEARCH RESULTS ===")
            lines.append(f"Query: {search_data['query']}")
            lines.append("")
            lines.append("Summary from search:")
            lines.append(search_data["summary"])
            lines.append("")
            lines.append("Sources used:")
            for result in search_data["results"][:3]:
                lines.append(f"- {result['title']} ({result['url']})")
        else:
            # SearXNG results - need to be summarized by LLM
            lines.append("=== WEB SEARCH RESULTS ===")
            lines.append(f"Query: {search_data['query']}")
            lines.append("")
            lines.append("IMPORTANT: Extract specific facts and numbers from these results to answer the user's question accurately:")
            lines.append("")
            
            for i, result in enumerate(search_data["results"], 1):
                lines.append(f"SOURCE {i}: {result['title']}")
                if result.get("snippet"):
                    lines.append(f"Content: {result['snippet'][:300]}")
                lines.append(f"URL: {result['url']}")
                lines.append("")
            
            lines.append("=== END SEARCH RESULTS ===")
            lines.append("")
            lines.append("Based on the search results above, provide a helpful, accurate answer with specific details and numbers. Cite sources where appropriate.")
        
        return "\n".join(lines)


# Singleton instance
web_search = WebSearchService()
