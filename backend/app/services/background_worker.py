"""
Background Worker - Processes embeddings when user is idle
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4
from ..config import settings
from .embedding import embedding_service, EmbeddingChunk
from .model_manager import model_manager


class BackgroundWorker:
    """Background worker for embedding conversations when idle"""
    
    def __init__(self):
        self.idle_timeout = 300  # 5 minutes in seconds
        self.last_activity: datetime = datetime.now()
        self.is_processing = False
        self.pending_queue_file = settings.data_dir / "pending_embeddings.json"
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    def _load_pending_queue(self) -> list:
        """Load pending embedding queue from disk"""
        if self.pending_queue_file.exists():
            try:
                with open(self.pending_queue_file, "r") as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_pending_queue(self, queue: list):
        """Save pending queue to disk"""
        self.pending_queue_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pending_queue_file, "w") as f:
            json.dump(queue, f, indent=2)
    
    def add_to_queue(self, conversation_id: str):
        """Add a conversation to the pending embedding queue"""
        queue = self._load_pending_queue()
        
        # Avoid duplicates
        if conversation_id not in queue:
            queue.append(conversation_id)
            self._save_pending_queue(queue)
            print(f"Added conversation {conversation_id} to embedding queue")
    
    def remove_from_queue(self, conversation_id: str):
        """Remove a conversation from the queue"""
        queue = self._load_pending_queue()
        if conversation_id in queue:
            queue.remove(conversation_id)
            self._save_pending_queue(queue)
    
    def record_activity(self):
        """Record user activity to reset idle timer"""
        self.last_activity = datetime.now()
    
    def is_idle(self) -> bool:
        """Check if user has been idle for the timeout period"""
        return datetime.now() - self.last_activity > timedelta(seconds=self.idle_timeout)
    
    async def process_pending_embeddings(self, chat_model: str) -> int:
        """Process all pending embeddings"""
        queue = self._load_pending_queue()
        
        if not queue:
            print("No pending embeddings to process")
            return 0
        
        print(f"Processing {len(queue)} pending conversations...")
        self.is_processing = True
        
        try:
            # Prepare models (unload chat, load embedding)
            await model_manager.prepare_for_embedding(chat_model)
            
            total_embedded = 0
            conversations_dir = settings.data_dir / "conversations"
            
            for conv_id in queue[:]:  # Copy to iterate safely
                conv_file = conversations_dir / f"{conv_id}.json"
                
                if not conv_file.exists():
                    print(f"Conversation file not found: {conv_id}")
                    self.remove_from_queue(conv_id)
                    continue
                
                try:
                    with open(conv_file, "r", encoding="utf-8") as f:
                        conv_data = json.load(f)
                    
                    # Create embedding chunks for each message
                    chunks = []
                    for msg in conv_data.get("messages", []):
                        # Skip system messages
                        if msg.get("role") == "system":
                            continue
                        
                        chunk = EmbeddingChunk(
                            id=msg.get("id", str(uuid4())),
                            conversation_id=conv_id,
                            role=msg.get("role", "user"),
                            content=msg.get("content", ""),
                            timestamp=datetime.fromisoformat(msg.get("timestamp", datetime.now().isoformat())),
                        )
                        chunks.append(chunk)
                    
                    # Embed and store
                    if chunks:
                        count = await embedding_service.embed_and_store(chunks)
                        total_embedded += count
                        print(f"Embedded {count} messages from conversation {conv_id}")
                    
                    # Remove from queue after successful processing
                    self.remove_from_queue(conv_id)
                    
                except Exception as e:
                    print(f"Error processing conversation {conv_id}: {e}")
            
            # Restore chat model
            await model_manager.restore_chat_model()
            
            return total_embedded
            
        finally:
            self.is_processing = False
    
    async def _worker_loop(self, chat_model: str):
        """Background worker loop"""
        while self._running:
            try:
                # Check every 30 seconds
                await asyncio.sleep(30)
                
                # Skip if already processing or not idle
                if self.is_processing:
                    continue
                
                if not self.is_idle():
                    continue
                
                # Check if there's work to do
                queue = self._load_pending_queue()
                if not queue:
                    continue
                
                print(f"User idle for {self.idle_timeout}s, processing {len(queue)} pending embeddings...")
                await self.process_pending_embeddings(chat_model)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Background worker error: {e}")
    
    def start(self, chat_model: str):
        """Start the background worker"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._worker_loop(chat_model))
        print(f"Background embedding worker started (idle timeout: {self.idle_timeout}s)")
    
    def stop(self):
        """Stop the background worker"""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        print("Background embedding worker stopped")
    
    def get_status(self) -> dict:
        """Get worker status"""
        queue = self._load_pending_queue()
        return {
            "running": self._running,
            "is_processing": self.is_processing,
            "pending_count": len(queue),
            "pending_conversations": queue,
            "idle_timeout_seconds": self.idle_timeout,
            "seconds_since_activity": (datetime.now() - self.last_activity).total_seconds(),
            "is_idle": self.is_idle(),
        }


# Singleton instance
background_worker = BackgroundWorker()

