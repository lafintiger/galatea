"""Search handler - Web search via SearXNG/Perplexica.

This handler processes web search requests and returns results.
"""
import base64

from .base import BaseHandler, HandlerContext
from ..core import (
    get_logger,
    clean_for_speech,
    synthesize_tts,
    ResponseType,
    Status,
)
from ..services.web_search import web_search
from ..services.ollama import ollama_service

logger = get_logger(__name__)


class SearchHandler(BaseHandler):
    """Handles web search requests."""
    
    async def handle(self, ctx: HandlerContext) -> None:
        """Handle web search message from frontend."""
        query = ctx.data.get("query", "")
        if query:
            await self.handle_search(ctx, query, query)
    
    async def handle_search(
        self,
        ctx: HandlerContext,
        query: str,
        original_request: str
    ) -> None:
        """Perform web search and summarize results."""
        try:
            await ctx.send_status(Status.SEARCHING)
            
            # Notify frontend search is starting
            await ctx.send_response(ResponseType.SEARCH_START, query=query)
            
            # Add location context for local queries
            user_location = getattr(ctx.settings, 'user_location', '')
            search_query = query
            
            if user_location:
                location_keywords = ['weather', 'restaurant', 'near', 'local', 'nearby', 'closest']
                query_lower = query.lower()
                if any(kw in query_lower for kw in location_keywords):
                    if user_location.lower() not in query_lower:
                        search_query = f"{query} in {user_location}"
            
            # Perform search
            results = await web_search.search(search_query)
            
            # Send results to frontend
            await ctx.send_response(ResponseType.SEARCH_RESULTS, data=results)
            
            if results.get("success"):
                # Prepare context for LLM
                search_context = self._format_search_context(results)
                
                # Build prompt for summarization
                summary_prompt = f"""Based on the following search results for "{query}", provide a helpful summary.

{search_context}

Provide a concise, helpful response based on these search results. If the results contain specific facts, numbers, or dates, include them."""
                
                # Generate summary
                await ctx.send_status(Status.THINKING)
                
                ctx.state.messages.append({"role": "user", "content": original_request})
                ctx.state.messages.append({
                    "role": "system",
                    "content": f"[Search results for: {query}]\n{search_context}"
                })
                
                # Stream response
                full_response = ""
                first_audio_sent = False
                sentence_buffer = ""
                
                async for chunk in ollama_service.chat_stream(
                    messages=ctx.state.messages,
                    model=ctx.settings.selected_model,
                    system_prompt="You are a helpful assistant summarizing search results. Be concise and factual."
                ):
                    if ctx.state.should_interrupt:
                        break
                    
                    full_response += chunk
                    await ctx.send_response(ResponseType.LLM_CHUNK, text=chunk)
                    
                    # Sentence-level TTS
                    sentence_buffer += chunk
                    for end in ['.', '!', '?']:
                        if end in sentence_buffer:
                            parts = sentence_buffer.split(end)
                            for part in parts[:-1]:
                                sentence = part.strip() + end
                                if sentence and len(sentence) > 2:
                                    if not first_audio_sent:
                                        await ctx.send_status(Status.SPEAKING)
                                        first_audio_sent = True
                                    
                                    clean_sentence = clean_for_speech(sentence)
                                    if clean_sentence:
                                        await self._speak(ctx, clean_sentence)
                            
                            sentence_buffer = parts[-1]
                            break
                
                # Handle remainder
                if sentence_buffer.strip() and not ctx.state.should_interrupt:
                    clean_remainder = clean_for_speech(sentence_buffer.strip())
                    if clean_remainder:
                        if not first_audio_sent:
                            await ctx.send_status(Status.SPEAKING)
                        await self._speak(ctx, clean_remainder)
                
                # Clean and send complete
                cleaned_response = clean_for_speech(full_response)
                await ctx.send_response(ResponseType.LLM_COMPLETE, text=cleaned_response)
                ctx.state.messages.append({"role": "assistant", "content": cleaned_response})
                
            else:
                error_msg = f"I couldn't find results for that search: {results.get('error', 'unknown error')}"
                await ctx.send_response(ResponseType.LLM_COMPLETE, text=error_msg)
                ctx.state.messages.append({"role": "assistant", "content": error_msg})
                await ctx.send_status(Status.SPEAKING)
                await self._speak(ctx, error_msg)
            
            await ctx.send_status(Status.IDLE)
            
        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            error_msg = f"Search failed: {str(e)}"
            await ctx.send_error(error_msg)
            await ctx.send_status(Status.IDLE)
    
    def _format_search_context(self, results: dict) -> str:
        """Format search results for LLM context."""
        parts = []
        
        # AI summary if available (from Perplexica)
        if results.get("summary"):
            parts.append(f"AI Summary: {results['summary']}")
        
        # Individual results
        items = results.get("results", [])
        if items:
            parts.append("\nSources:")
            for i, item in enumerate(items[:5], 1):
                title = item.get("title", "")
                snippet = item.get("snippet", item.get("content", ""))[:200]
                parts.append(f"{i}. {title}: {snippet}")
        
        return "\n".join(parts)
    
    async def _speak(self, ctx: HandlerContext, text: str) -> None:
        """Synthesize and send TTS audio."""
        try:
            audio_data = await synthesize_tts(
                text=text,
                voice=ctx.settings.selected_voice,
                provider=getattr(ctx.settings, 'tts_provider', 'piper'),
                speed=getattr(ctx.settings, 'voice_speed', 1.0)
            )
            if audio_data and not ctx.state.should_interrupt:
                await ctx.send_response(
                    ResponseType.AUDIO_CHUNK,
                    audio=base64.b64encode(audio_data).decode('utf-8'),
                    format="wav",
                    sentence=text
                )
        except Exception as e:
            logger.error(f"Search TTS error: {e}")
