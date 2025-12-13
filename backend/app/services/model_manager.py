"""
Model Manager - Load/unload Ollama models to manage VRAM
"""
import httpx
from typing import Optional, List
from ..config import settings


class ModelManager:
    """Manage Ollama model loading/unloading for VRAM optimization"""
    
    def __init__(self):
        self.ollama_url = settings.ollama_base_url
        self.chat_model: Optional[str] = None
        self.embedding_model = "nomic-embed-text-v2-moe"  # MoE embedding model (958MB, 768 dims, faster)
    
    async def get_loaded_models(self) -> List[dict]:
        """Get list of currently loaded models"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.ollama_url}/api/ps",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("models", [])
            except Exception as e:
                print(f"Error getting loaded models: {e}")
                return []
    
    async def is_model_loaded(self, model_name: str) -> bool:
        """Check if a specific model is loaded"""
        models = await self.get_loaded_models()
        return any(m.get("name", "").startswith(model_name) for m in models)
    
    async def unload_model(self, model_name: str) -> bool:
        """Unload a model from VRAM"""
        async with httpx.AsyncClient() as client:
            try:
                # Ollama unloads via generate with keep_alive=0
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model_name,
                        "keep_alive": 0
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                print(f"Unloaded model: {model_name}")
                return True
            except Exception as e:
                print(f"Error unloading model {model_name}: {e}")
                return False
    
    async def load_model(self, model_name: str) -> bool:
        """Pre-load a model into VRAM"""
        async with httpx.AsyncClient() as client:
            try:
                # Ollama loads via generate with empty prompt
                # stream: false for simpler handling
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": "hi",  # Minimal prompt to trigger load
                        "stream": False,
                        "keep_alive": "10m"  # Keep loaded for 10 minutes
                    },
                    timeout=180.0  # Loading can take time for large models
                )
                response.raise_for_status()
                print(f"Loaded model: {model_name}")
                return True
            except Exception as e:
                print(f"Error loading model {model_name}: {e}")
                return False
    
    async def prepare_for_embedding(self, chat_model: str) -> bool:
        """Prepare for embedding by unloading chat model"""
        self.chat_model = chat_model
        
        # Unload chat model
        if await self.is_model_loaded(chat_model):
            await self.unload_model(chat_model)
        
        # Load embedding model
        return await self.load_model(self.embedding_model)
    
    async def restore_chat_model(self) -> bool:
        """Restore chat model after embedding"""
        if not self.chat_model:
            return False
        
        # Unload embedding model
        if await self.is_model_loaded(self.embedding_model):
            await self.unload_model(self.embedding_model)
        
        # Reload chat model
        return await self.load_model(self.chat_model)
    
    async def get_vram_info(self) -> dict:
        """Get VRAM usage info (if available)"""
        models = await self.get_loaded_models()
        
        total_size = 0
        model_info = []
        
        for m in models:
            size_gb = m.get("size", 0) / (1024**3)
            total_size += size_gb
            model_info.append({
                "name": m.get("name", "unknown"),
                "size_gb": round(size_gb, 2),
            })
        
        return {
            "loaded_models": model_info,
            "total_vram_gb": round(total_size, 2),
        }


# Singleton instance
model_manager = ModelManager()

