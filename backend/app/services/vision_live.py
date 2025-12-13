"""Vision Live Service - Real-time face/emotion analysis via galatea-vision"""
import asyncio
import httpx
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from ..config import settings

@dataclass
class StartupContext:
    """Rich context captured when Gala opens her eyes"""
    # Identity
    identity: str = ""
    identity_role: str = "unknown"
    is_owner: bool = False
    
    # Emotional state
    emotion: str = "neutral"
    emotion_confidence: float = 0.0
    
    # Demographics (from DeepFace)
    age: int = 0
    gender: str = ""
    
    # Scene analysis (from vision model)
    scene_description: str = ""
    environment: str = ""  # "home office", "living room", etc.
    
    # Time context
    time_of_day: str = ""  # "morning", "afternoon", "evening", "night"
    day_type: str = ""  # "weekday", "weekend"
    
    # Captured timestamp
    captured_at: datetime = field(default_factory=datetime.now)
    
    def to_greeting_context(self) -> str:
        """Build a rich context string for Gala's greeting"""
        parts = []
        
        # Who
        if self.identity and self.is_owner:
            parts.append(f"{self.identity} (the owner) just opened Gala")
        elif self.identity:
            parts.append(f"{self.identity} (a {self.identity_role}) is here")
        else:
            parts.append("An unknown person is here")
        
        # Emotional state
        if self.emotion and self.emotion != "neutral" and self.emotion != "unknown":
            emotion_desc = {
                "happy": "looking happy",
                "sad": "looking a bit down",
                "angry": "looking frustrated",
                "fear": "looking worried",
                "surprise": "looking surprised",
                "disgust": "looking bothered",
            }.get(self.emotion, f"appearing {self.emotion}")
            parts.append(emotion_desc)
        elif self.emotion == "neutral":
            parts.append("with a calm expression")
        
        # Environment
        if self.scene_description:
            parts.append(f"Scene: {self.scene_description}")
        elif self.environment:
            parts.append(f"in their {self.environment}")
        
        # Time context
        time_parts = []
        if self.time_of_day:
            time_parts.append(f"It's {self.time_of_day}")
        if self.day_type:
            time_parts.append(f"on a {self.day_type}")
        if time_parts:
            parts.append(". ".join(time_parts))
        
        return ". ".join(parts) + "."
    
    def to_dict(self) -> dict:
        return {
            "identity": self.identity,
            "identity_role": self.identity_role,
            "is_owner": self.is_owner,
            "emotion": self.emotion,
            "emotion_confidence": self.emotion_confidence,
            "age": self.age,
            "gender": self.gender,
            "scene_description": self.scene_description,
            "environment": self.environment,
            "time_of_day": self.time_of_day,
            "day_type": self.day_type,
            "captured_at": self.captured_at.isoformat(),
        }


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
            print(f"[Vision] Start failed: {e}")
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
            print(f"[Vision] Stop failed: {e}")
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
            print(f"[Vision] Status failed: {e}")
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
            print(f"[Vision] Analyze failed: {e}")
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
    
    # ============== Startup Awareness ==============
    
    _startup_context: Optional[StartupContext] = None
    
    async def capture_startup_context(self, scene_analyzer=None) -> StartupContext:
        """
        Capture comprehensive startup context when Gala opens her eyes.
        
        This includes:
        - Face recognition (who is this?)
        - Emotion detection (how are they feeling?)
        - Scene analysis (where are they?)
        - Time context (when is this?)
        
        Args:
            scene_analyzer: Optional async function to analyze scene from image
                           Should accept base64 image and return description string
        """
        from datetime import datetime
        
        context = StartupContext()
        context.captured_at = datetime.now()
        
        # Time context
        hour = context.captured_at.hour
        if 5 <= hour < 12:
            context.time_of_day = "morning"
        elif 12 <= hour < 17:
            context.time_of_day = "afternoon"
        elif 17 <= hour < 21:
            context.time_of_day = "evening"
        else:
            context.time_of_day = "night"
        
        weekday = context.captured_at.weekday()
        context.day_type = "weekend" if weekday >= 5 else "weekday"
        
        try:
            # Capture a frame for analysis
            frame_data = await self.capture_frame()
            
            if "error" in frame_data:
                print(f"Could not capture startup frame: {frame_data['error']}")
                self._startup_context = context
                return context
            
            image_base64 = frame_data.get("image", "")
            
            if not image_base64:
                self._startup_context = context
                return context
            
            # Run face/emotion analysis via vision service
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/analyze",
                        json={"image": image_base64}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extract identity
                        context.identity = data.get("identity", "")
                        context.identity_role = data.get("identity_role", "unknown")
                        context.is_owner = data.get("is_owner", False)
                        
                        # Extract emotion
                        context.emotion = data.get("emotion", "neutral")
                        emotion_scores = data.get("emotion_scores", {})
                        if context.emotion and emotion_scores:
                            context.emotion_confidence = emotion_scores.get(context.emotion, 0) / 100
                        
                        # Extract demographics
                        context.age = data.get("age", 0)
                        context.gender = data.get("gender", "")
                        
                        print(f"Startup analysis: {context.identity or 'Unknown'}, emotion={context.emotion}")
            except Exception as e:
                print(f"Face analysis failed during startup: {e}")
            
            # Run scene analysis if analyzer provided
            if scene_analyzer and image_base64:
                try:
                    scene_desc = await scene_analyzer(image_base64)
                    if scene_desc:
                        context.scene_description = scene_desc
                        
                        # Try to extract environment type
                        scene_lower = scene_desc.lower()
                        if "office" in scene_lower:
                            context.environment = "home office"
                        elif "bedroom" in scene_lower:
                            context.environment = "bedroom"
                        elif "living" in scene_lower:
                            context.environment = "living room"
                        elif "kitchen" in scene_lower:
                            context.environment = "kitchen"
                        elif "outdoor" in scene_lower or "outside" in scene_lower:
                            context.environment = "outdoors"
                        
                        print(f"Scene analysis: {context.environment or scene_desc[:50]}")
                except Exception as e:
                    print(f"Scene analysis failed during startup: {e}")
        
        except Exception as e:
            print(f"Startup context capture failed: {e}")
        
        self._startup_context = context
        return context
    
    def get_startup_context(self) -> Optional[StartupContext]:
        """Get the most recent startup context"""
        return self._startup_context
    
    def get_startup_greeting_context(self) -> str:
        """Get startup context formatted for greeting"""
        if not self._startup_context:
            return ""
        return self._startup_context.to_greeting_context()
    
    def clear_startup_context(self):
        """Clear startup context (e.g., when eyes close)"""
        self._startup_context = None


# Singleton instance
vision_live_service = VisionLiveService()

