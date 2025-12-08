"""
Vision Service - Image analysis using local vision models

Supports multiple vision models for different use cases:
- granite3.2-vision: Fast, general purpose (default)
- deepseek-ocr: Text extraction from images
- qwen3-vl-abliterated: Uncensored, for anything other models block
"""

import httpx
import base64
import re
from typing import Optional, Literal
from ..config import settings
from .model_manager import model_manager


class VisionService:
    def __init__(self):
        self.ollama_url = settings.ollama_base_url
        self.client = httpx.AsyncClient(base_url=self.ollama_url, timeout=120.0)
        
        # Available vision models (in order of preference)
        self.models = {
            "general": "granite3.2-vision:latest",      # Fast, general purpose
            "ocr": "deepseek-ocr:latest",               # Text extraction
            "uncensored": "huihui_ai/qwen3-vl-abliterated:2b",  # Uncensored
        }
        
        # Keywords that suggest OCR is needed
        self.ocr_keywords = [
            "read", "text", "words", "writing", "says", "written",
            "document", "receipt", "label", "sign", "menu", "letter"
        ]
    
    def detect_intent(self, prompt: str) -> Literal["general", "ocr", "uncensored"]:
        """Determine which vision model to use based on the prompt."""
        prompt_lower = prompt.lower()
        
        # Check for OCR keywords
        for keyword in self.ocr_keywords:
            if keyword in prompt_lower:
                return "ocr"
        
        # Default to general vision
        return "general"
    
    async def analyze_image(
        self, 
        image_base64: str, 
        prompt: str = "Describe this image in detail.",
        model_type: Optional[Literal["general", "ocr", "uncensored"]] = None
    ) -> dict:
        """
        Analyze an image using the appropriate vision model.
        
        Args:
            image_base64: Base64-encoded image data
            prompt: What to analyze/ask about the image
            model_type: Force a specific model type, or auto-detect from prompt
            
        Returns:
            dict with 'description', 'model_used', and 'success' fields
        """
        # Auto-detect model type if not specified
        if model_type is None:
            model_type = self.detect_intent(prompt)
        
        model_name = self.models[model_type]
        
        print(f"🖼️ Vision analysis requested")
        print(f"   Model type: {model_type}")
        print(f"   Model: {model_name}")
        print(f"   Prompt: {prompt[:50]}...")
        
        try:
            # Load the vision model (model_manager will handle VRAM)
            await model_manager.load_model(model_name)
            
            # Call Ollama's vision API
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500,  # Reasonable response length
                    }
                }
            )
            response.raise_for_status()
            
            result = response.json()
            description = result.get("response", "").strip()
            
            print(f"✅ Vision analysis complete ({len(description)} chars)")
            
            return {
                "success": True,
                "description": description,
                "model_used": model_name,
                "model_type": model_type
            }
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Vision model error: {e.response.status_code}"
            print(f"❌ {error_msg}")
            
            # Try fallback to uncensored model if general fails
            if model_type != "uncensored":
                print("🔄 Trying uncensored fallback...")
                return await self.analyze_image(image_base64, prompt, "uncensored")
            
            return {
                "success": False,
                "description": error_msg,
                "model_used": model_name,
                "model_type": model_type
            }
            
        except Exception as e:
            error_msg = f"Vision analysis failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "description": error_msg,
                "model_used": model_name,
                "model_type": model_type
            }
    
    async def analyze_screenshot(self, image_base64: str, prompt: str = None) -> dict:
        """Analyze a screenshot - optimized prompt for screen content."""
        if prompt is None:
            prompt = "Describe what you see on this screen. Include any text, UI elements, and what the user appears to be doing."
        return await self.analyze_image(image_base64, prompt, "general")
    
    async def extract_text(self, image_base64: str) -> dict:
        """Extract text from an image using OCR model."""
        prompt = "Read and transcribe all visible text in this image. Format it clearly."
        return await self.analyze_image(image_base64, prompt, "ocr")
    
    async def check_models_available(self) -> dict:
        """Check which vision models are available."""
        available = {}
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            installed_models = [m["name"] for m in response.json().get("models", [])]
            
            for model_type, model_name in self.models.items():
                # Check if model or a variant is installed
                base_name = model_name.split(":")[0]
                available[model_type] = any(
                    base_name in m for m in installed_models
                )
            
            return available
        except Exception as e:
            print(f"Error checking vision models: {e}")
            return {k: False for k in self.models.keys()}


# Singleton instance
vision_service = VisionService()

