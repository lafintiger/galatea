"""
Embedding Service - Uses Ollama embeddings API with LanceDB storage
"""
import httpx
import lancedb
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from ..config import settings


class EmbeddingChunk(BaseModel):
    """A chunk of text with its embedding"""
    id: str
    conversation_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    vector: Optional[List[float]] = None


class EmbeddingService:
    """Service for creating and storing embeddings using LanceDB"""
    
    def __init__(self):
        self.ollama_url = settings.ollama_base_url
        self.embedding_model = "nomic-embed-text-v2-moe"  # MoE embedding model (958MB, 768 dims, faster)
        self.db_path = settings.data_dir / "lancedb"
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.db = None
        self.table = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of LanceDB"""
        if not self._initialized:
            self.db = lancedb.connect(str(self.db_path))
            self._initialized = True
    
    def _get_or_create_table(self):
        """Get or create the embeddings table"""
        self._ensure_initialized()
        
        table_name = "conversation_embeddings"
        
        if table_name in self.db.table_names():
            self.table = self.db.open_table(table_name)
        else:
            # Create table with initial schema
            # nomic-embed-text-v2-moe produces 768-dim embeddings
            import pyarrow as pa
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("conversation_id", pa.string()),
                pa.field("role", pa.string()),
                pa.field("content", pa.string()),
                pa.field("timestamp", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), 768)),
            ])
            self.table = self.db.create_table(table_name, schema=schema)
        
        return self.table
    
    async def get_embedding(self, text: str, is_query: bool = False) -> List[float]:
        """Get embedding for a single text using Ollama
        
        Args:
            text: The text to embed
            is_query: If True, use query prefix; if False, use document prefix
                     (nomic-embed-text-v2-moe requires these prefixes for best results)
        """
        # Add appropriate prefix for nomic model
        prefix = "search_query: " if is_query else "search_document: "
        prefixed_text = prefix + text
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_url}/api/embed",
                json={
                    "model": self.embedding_model,
                    "input": prefixed_text
                },
                timeout=60.0  # Embeddings can take time
            )
            response.raise_for_status()
            data = response.json()
            
            # Ollama returns embeddings in data["embeddings"][0]
            return data["embeddings"][0]
    
    async def embed_and_store(self, chunks: List[EmbeddingChunk]) -> int:
        """Embed multiple chunks and store in LanceDB"""
        if not chunks:
            return 0
        
        table = self._get_or_create_table()
        
        # Get embeddings for all chunks
        embedded_data = []
        for chunk in chunks:
            try:
                vector = await self.get_embedding(chunk.content)
                embedded_data.append({
                    "id": chunk.id,
                    "conversation_id": chunk.conversation_id,
                    "role": chunk.role,
                    "content": chunk.content,
                    "timestamp": chunk.timestamp.isoformat(),
                    "vector": vector,
                })
            except Exception as e:
                print(f"Error embedding chunk {chunk.id}: {e}")
                continue
        
        if embedded_data:
            table.add(embedded_data)
        
        return len(embedded_data)
    
    async def search_similar(
        self, 
        query: str, 
        limit: int = 5,
        min_score: float = 0.5
    ) -> List[dict]:
        """Search for similar content in the knowledge base"""
        table = self._get_or_create_table()
        
        if table is None or len(table) == 0:
            return []
        
        # Get query embedding (use query prefix for better retrieval)
        query_vector = await self.get_embedding(query, is_query=True)
        
        # Search LanceDB
        results = (
            table
            .search(query_vector)
            .limit(limit)
            .to_list()
        )
        
        # Filter by score and format results
        filtered = []
        for r in results:
            # LanceDB returns _distance (lower is better for L2)
            # Convert to similarity score (higher is better)
            score = 1.0 / (1.0 + r.get("_distance", 1.0))
            if score >= min_score:
                filtered.append({
                    "id": r["id"],
                    "conversation_id": r["conversation_id"],
                    "role": r["role"],
                    "content": r["content"],
                    "timestamp": r["timestamp"],
                    "score": score,
                })
        
        return filtered
    
    async def delete_conversation_embeddings(self, conversation_id: str) -> int:
        """Delete all embeddings for a conversation"""
        table = self._get_or_create_table()
        
        if table is None:
            return 0
        
        # LanceDB delete syntax
        table.delete(f"conversation_id = '{conversation_id}'")
        return 1  # Can't easily get count of deleted rows
    
    def get_stats(self) -> dict:
        """Get stats about the embedding database"""
        table = self._get_or_create_table()
        
        return {
            "total_embeddings": len(table) if table else 0,
            "db_path": str(self.db_path),
            "embedding_model": self.embedding_model,
        }


# Singleton instance
embedding_service = EmbeddingService()

