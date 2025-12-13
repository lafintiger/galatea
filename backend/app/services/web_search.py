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
    
    async def search_searxng(self, query: str, num_results: int = 5) -> list[SearchResult]:
        """Search using SearXNG meta-search engine
        
        SearXNG aggregates results from multiple search engines.
        Returns raw results - use Ollama to summarize if needed.
        """
        try:
            response = await self.client.get(
                f"{self.searxng_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "engines": "google,bing,duckduckgo",
                    "language": "en",
                }
            )
            response.raise_for_status()
            data = response.json()
            
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
            print(f"SearXNG search error: {e}")
            return []
    
    async def search_perplexica(
        self, 
        query: str, 
        focus_mode: str = "webSearch",
        optimization_mode: str = "speed"
    ) -> dict:
        """Search using Perplexica AI-powered search
        
        Perplexica provides AI-generated summaries with sources.
        
        Args:
            query: The search query
            focus_mode: One of "webSearch", "academicSearch", "writingAssistant", 
                       "wolframAlphaSearch", "youtubeSearch", "redditSearch"
            optimization_mode: "speed" or "balanced"
            
        Returns:
            Dict with 'answer' (AI summary) and 'sources' (list of sources)
        """
        try:
            # Perplexica API format per docs: https://github.com/ItzCrazyKns/Perplexica/blob/master/docs/API/SEARCH.md
            # Must use "providerId" and "key" (not "provider" and "model")
            provider_id = settings.perplexica_ollama_provider_id
            request_body = {
                "chatModel": {
                    "providerId": provider_id,
                    "key": settings.perplexica_chat_model,  # Fast non-thinking model for search
                },
                "embeddingModel": {
                    "providerId": provider_id,
                    "key": settings.perplexica_embedding_model,  # Embedding model for search
                },
                "optimizationMode": optimization_mode,
                "focusMode": focus_mode,
                "query": query,
                "history": []  # No conversation history for fresh searches
            }
            
            print(f"[Search] Perplexica request: {request_body}")
            
            response = await self.client.post(
                f"{self.perplexica_url}/api/search",
                json=request_body,
                timeout=120.0  # Perplexica needs time for AI search + Ollama
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"[Search] Perplexica response keys: {data.keys()}")
            
            # Parse response - Perplexica returns 'message' and 'sources'
            sources = []
            for src in data.get("sources", []):
                # Sources can have 'metadata' with title/url or direct fields
                metadata = src.get("metadata", {})
                sources.append(SearchResult(
                    title=metadata.get("title", src.get("title", "")),
                    url=metadata.get("url", src.get("url", "")),
                    snippet=src.get("pageContent", src.get("content", ""))[:300],
                    source="perplexica"
                ).to_dict())
            
            return {
                "answer": data.get("message", ""),
                "sources": sources
            }
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
            provider: Which search provider to use ("auto" prefers Perplexica for quality)
            num_results: Number of results (for SearXNG fallback)
            
        Returns:
            Dict with 'results' and optionally 'summary'
        """
        # Try Perplexica first if available (better AI summaries)
        if provider in ["perplexica", "auto"]:
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
                    print("[Search] Perplexica returned no results, trying SearXNG...")
            except Exception as e:
                print(f"[Search] Perplexica error: {e}, trying SearXNG...")
        
        # Use SearXNG (reliable fallback)
        try:
            if await self.is_searxng_available():
                print(f"[Search] Using SearXNG for: {query}")
                results = await self.search_searxng(query, num_results)
                if results:
                    print(f"[Search] SearXNG returned {len(results)} results")
                    return {
                        "provider": "searxng",
                        "query": query,
                        "summary": "",  # LLM will summarize
                        "results": [r.to_dict() for r in results]
                    }
                print("[Search] SearXNG returned no results")
        except Exception as e:
            print(f"[Search] SearXNG error: {e}")
        
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
        """Check if Perplexica is reachable"""
        try:
            response = await self.client.get(f"{self.perplexica_url}/api", timeout=5.0)
            return response.status_code in [200, 404]  # 404 means API exists but endpoint doesn't
        except:
            return False
    
    async def check_status(self) -> dict:
        """Check availability of search services"""
        searxng = await self.is_searxng_available()
        perplexica = await self.is_perplexica_available()
        
        return {
            "searxng": {
                "available": searxng,
                "url": self.searxng_url
            },
            "perplexica": {
                "available": perplexica,
                "url": self.perplexica_url
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
                    # Include more of the snippet for better context
                    lines.append(f"Content: {result['snippet'][:300]}")
                lines.append(f"URL: {result['url']}")
                lines.append("")
            
            lines.append("=== END SEARCH RESULTS ===")
            lines.append("")
            lines.append("Based on the search results above, provide a helpful, accurate answer with specific details and numbers. Cite sources where appropriate.")
        
        return "\n".join(lines)


# Singleton instance
web_search = WebSearchService()

