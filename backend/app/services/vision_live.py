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
    # Identity (face recognition)
    identity: str = ""  # Name of recognized person
    identity_role: str = "unknown"  # "owner", "friend", "family", "unknown"
    identity_confidence: float = 0.0
    is_owner: bool = False
    
    def to_context(self) -> str:
        """Convert to natural language for system prompt"""
        if not self.present:
            return "User is not visible (webcam off or no face detected)"
        
        parts = []
        
        # Identity - most important!
        if self.identity and self.is_owner:
            parts.append(f"This is {self.identity} (the owner)")
        elif self.identity:
            parts.append(f"This is {self.identity} (a {self.identity_role})")
        elif self.identity_role == "unknown":
            parts.append("Unknown person - NOT the owner")
        
        # Emotion
        if self.emotion and self.emotion != "unknown":
            conf = "clearly" if self.emotion_confidence > 0.7 else "appears"
            parts.append(f"{conf} {self.emotion}")
        
        # Attention
        if self.attentive:
            parts.append("looking at the screen")
        else:
            parts.append("looking away")
        
        # Multiple faces
        if self.face_count > 1:
            parts.append(f"{self.face_count} people visible")
        
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
            present=data.get("face_detected", data.get("present", False)),
            emotion=data.get("emotion", "unknown"),
            emotion_confidence=data.get("emotion_scores", {}).get(data.get("emotion", ""), 0.0) / 100 if data.get("emotion_scores") else 0.0,
            age=data.get("age", 0),
            gender=data.get("gender", "unknown"),
            gender_confidence=data.get("gender_confidence", 0.0),
            attentive=data.get("attention", data.get("attentive", False)),
            face_count=data.get("face_count", 1 if data.get("face_detected") else 0),
            timestamp=data.get("timestamp", ""),
            # Identity fields
            identity=data.get("identity", ""),
            identity_role=data.get("identity_role", "unknown"),
            identity_confidence=data.get("identity_confidence", 0.0),
            is_owner=data.get("is_owner", False),
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
    
    # ============== Face Recognition Methods ==============
    
    async def enroll_face(self, name: str, role: str = "friend", image_base64: Optional[str] = None) -> dict:
        """
        Enroll a face for recognition
        
        Args:
            name: Name of the person
            role: "owner", "friend", or "family"
            image_base64: Optional base64 image, or None to capture from webcam
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {"name": name, "role": role}
                if image_base64:
                    payload["image"] = image_base64
                
                response = await client.post(f"{self.base_url}/faces/enroll", json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Face enrollment failed: {e}")
            return {"success": False, "message": str(e)}
    
    async def list_faces(self) -> dict:
        """List all enrolled faces"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/faces")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"List faces failed: {e}")
            return {"faces": [], "owner_enrolled": False, "error": str(e)}
    
    async def delete_face(self, face_id: str) -> dict:
        """Delete an enrolled face"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.delete(f"{self.base_url}/faces/{face_id}")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Delete face failed: {e}")
            return {"success": False, "message": str(e)}
    
    async def capture_frame(self) -> dict:
        """Capture a frame from webcam for enrollment preview"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{self.base_url}/faces/capture")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Capture frame failed: {e}")
            return {"error": str(e)}
    
    async def has_owner(self) -> bool:
        """Check if owner is enrolled"""
        faces = await self.list_faces()
        return faces.get("owner_enrolled", False)
    
    async def get_owner_name(self) -> Optional[str]:
        """Get owner's name if enrolled"""
        faces = await self.list_faces()
        return faces.get("owner_name")
    
    # ============== Access Control ==============
    
    def is_owner_present(self) -> bool:
        """Check if the current person is the owner"""
        if not self._current_result:
            return False
        return self._current_result.is_owner
    
    def is_known_person(self) -> bool:
        """Check if the current person is known (owner or friend)"""
        if not self._current_result:
            return False
        return bool(self._current_result.identity)
    
    def get_current_identity(self) -> tuple[str, str]:
        """Get current person's identity (name, role)"""
        if not self._current_result or not self._current_result.identity:
            return ("", "unknown")
        return (self._current_result.identity, self._current_result.identity_role)


# Singleton instance
vision_live_service = VisionLiveService()

