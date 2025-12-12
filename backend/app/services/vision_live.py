"""Vision Live Service - Real-time face/emotion analysis via galatea-vision"""
import asyncio
import httpx
import json
from typing import Optional, Callable, Any
from dataclasses import dataclass
from ..config import settings

@dataclass
class VisionResult:
    """Result from vision analysis"""
    present: bool = False
    emotion: str = "unknown"
    emotion_confidence: float = 0.0
    age: int = 0
    gender: str = "unknown"
    gender_confidence: float = 0.0
    attentive: bool = False
    face_count: int = 0
    timestamp: str = ""
    
    def to_context(self) -> str:
        """Convert to natural language for system prompt"""
        if not self.present:
            return "User is not visible (webcam off or no face detected)"
        
        parts = []
        
        # Emotion
        if self.emotion and self.emotion != "unknown":
            conf = "clearly" if self.emotion_confidence > 0.7 else "appears"
            parts.append(f"User {conf} {self.emotion}")
        
        # Attention
        if self.attentive:
            parts.append("looking at the screen")
        else:
            parts.append("looking away")
        
        return "Visual context: " + ", ".join(parts) if parts else ""


class VisionLiveService:
    """Client for galatea-vision real-time analysis service"""
    
    def __init__(self):
        host = settings.vision_host
        port = settings.vision_port
        self.base_url = f"http://{host}:{port}"
        self._current_result: Optional[VisionResult] = None
        self._is_active = False
        self._ws_task: Optional[asyncio.Task] = None
        self._callbacks: list[Callable[[VisionResult], Any]] = []
    
    @property
    def is_active(self) -> bool:
        """Check if vision is currently active"""
        return self._is_active
    
    @property
    def current_result(self) -> Optional[VisionResult]:
        """Get the most recent vision result"""
        return self._current_result
    
    async def health_check(self) -> bool:
        """Check if vision service is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
    
    async def start(self) -> dict:
        """Start vision analysis (open Gala's eyes)"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{self.base_url}/start")
                response.raise_for_status()
                self._is_active = True
                return response.json()
        except Exception as e:
            print(f"❌ Vision start failed: {e}")
            raise
    
    async def stop(self) -> dict:
        """Stop vision analysis (close Gala's eyes)"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{self.base_url}/stop")
                response.raise_for_status()
                self._is_active = False
                self._current_result = None
                return response.json()
        except Exception as e:
            print(f"❌ Vision stop failed: {e}")
            raise
    
    async def get_status(self) -> dict:
        """Get current vision status"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/status")
                response.raise_for_status()
                data = response.json()
                
                # Update active state
                self._is_active = data.get("analyzing", False)
                
                # Parse latest result if available
                if data.get("latest_result"):
                    self._parse_result(data["latest_result"])
                
                return data
        except Exception as e:
            print(f"❌ Vision status failed: {e}")
            return {"analyzing": False, "error": str(e)}
    
    async def analyze_single(self, image_base64: str) -> VisionResult:
        """Analyze a single image"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/analyze",
                    json={"image": image_base64}
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_result(data)
        except Exception as e:
            print(f"❌ Vision analyze failed: {e}")
            raise
    
    def _parse_result(self, data: dict) -> VisionResult:
        """Parse API response into VisionResult"""
        result = VisionResult(
            present=data.get("present", False),
            emotion=data.get("emotion", "unknown"),
            emotion_confidence=data.get("emotion_confidence", 0.0),
            age=data.get("age", 0),
            gender=data.get("gender", "unknown"),
            gender_confidence=data.get("gender_confidence", 0.0),
            attentive=data.get("attentive", False),
            face_count=data.get("face_count", 0),
            timestamp=data.get("timestamp", ""),
        )
        self._current_result = result
        return result
    
    def register_callback(self, callback: Callable[[VisionResult], Any]):
        """Register a callback for vision updates"""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[VisionResult], Any]):
        """Unregister a callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def poll_updates(self, interval: float = 1.0):
        """Poll for vision updates (alternative to WebSocket)"""
        while self._is_active:
            try:
                await self.get_status()
                if self._current_result:
                    for callback in self._callbacks:
                        try:
                            await callback(self._current_result) if asyncio.iscoroutinefunction(callback) else callback(self._current_result)
                        except Exception as e:
                            print(f"Vision callback error: {e}")
            except Exception as e:
                print(f"Vision poll error: {e}")
            await asyncio.sleep(interval)
    
    def get_emotion_context(self) -> str:
        """Get emotion context for system prompt injection"""
        if not self._is_active or not self._current_result:
            return ""
        return self._current_result.to_context()


# Singleton instance
vision_live_service = VisionLiveService()

