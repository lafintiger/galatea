"""
Galatea Vision Analyzer
DeepFace wrapper for emotion, age, gender, presence detection, and FACE RECOGNITION
"""

import asyncio
import base64
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List, Dict
import threading

import cv2
import numpy as np
from deepface import DeepFace

logger = logging.getLogger(__name__)

# Face database location
FACES_DIR = Path(os.getenv("FACES_DIR", "./data/faces"))
FACES_DB_FILE = FACES_DIR / "faces.json"


@dataclass
class EnrolledFace:
    """A stored face for recognition"""
    id: str
    name: str
    role: str  # "owner", "friend", "family"
    embedding: List[float] = field(default_factory=list)
    enrolled_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "enrolled_at": self.enrolled_at,
        }


@dataclass
class VisionResult:
    """Result of a single vision analysis"""
    timestamp: datetime = field(default_factory=datetime.now)
    face_detected: bool = False
    emotion: Optional[str] = None
    emotion_scores: dict = field(default_factory=dict)
    age: Optional[int] = None
    gender: Optional[str] = None
    gender_confidence: Optional[float] = None
    face_confidence: Optional[float] = None
    # Derived metrics
    attention: bool = False  # Face detected = user is present and looking
    # Identity (face recognition)
    identity: Optional[str] = None  # Name of recognized person
    identity_role: Optional[str] = None  # "owner", "friend", "unknown"
    identity_confidence: Optional[float] = None
    is_owner: bool = False  # Quick check: is this the owner?
    face_count: int = 0  # Number of faces detected
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "face_detected": self.face_detected,
            "emotion": self.emotion,
            "emotion_scores": self.emotion_scores,
            "age": self.age,
            "gender": self.gender,
            "gender_confidence": self.gender_confidence,
            "face_confidence": self.face_confidence,
            "attention": self.attention,
            "identity": self.identity,
            "identity_role": self.identity_role,
            "identity_confidence": self.identity_confidence,
            "is_owner": self.is_owner,
            "face_count": self.face_count,
        }


class FaceDatabase:
    """Manages enrolled faces for recognition"""
    
    def __init__(self, db_path: Path = FACES_DB_FILE):
        self.db_path = db_path
        self.faces: Dict[str, EnrolledFace] = {}
        self._load()
    
    def _load(self):
        """Load faces from disk"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    for face_data in data.get("faces", []):
                        face = EnrolledFace(
                            id=face_data["id"],
                            name=face_data["name"],
                            role=face_data["role"],
                            embedding=face_data.get("embedding", []),
                            enrolled_at=face_data.get("enrolled_at", ""),
                        )
                        self.faces[face.id] = face
                logger.info(f"Loaded {len(self.faces)} enrolled faces")
            except Exception as e:
                logger.error(f"Failed to load face database: {e}")
    
    def _save(self):
        """Save faces to disk"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "faces": [
                {
                    "id": f.id,
                    "name": f.name,
                    "role": f.role,
                    "embedding": f.embedding,
                    "enrolled_at": f.enrolled_at,
                }
                for f in self.faces.values()
            ]
        }
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def enroll(self, face_id: str, name: str, role: str, embedding: List[float]) -> EnrolledFace:
        """Enroll a new face"""
        face = EnrolledFace(
            id=face_id,
            name=name,
            role=role,
            embedding=embedding,
            enrolled_at=datetime.now().isoformat(),
        )
        self.faces[face_id] = face
        self._save()
        logger.info(f"Enrolled face: {name} ({role})")
        return face
    
    def remove(self, face_id: str) -> bool:
        """Remove an enrolled face"""
        if face_id in self.faces:
            name = self.faces[face_id].name
            del self.faces[face_id]
            self._save()
            logger.info(f"Removed face: {name}")
            return True
        return False
    
    def get_owner(self) -> Optional[EnrolledFace]:
        """Get the owner face if enrolled"""
        for face in self.faces.values():
            if face.role == "owner":
                return face
        return None
    
    def list_faces(self) -> List[EnrolledFace]:
        """List all enrolled faces"""
        return list(self.faces.values())
    
    def has_owner(self) -> bool:
        """Check if owner is enrolled"""
        return self.get_owner() is not None


class VisionAnalyzer:
    """
    Continuous vision analyzer using DeepFace
    
    Features:
    - Emotion detection (7 emotions)
    - Age estimation
    - Gender detection
    - Presence/attention detection
    - FACE RECOGNITION (identify owner vs strangers)
    """
    
    def __init__(
        self,
        detector_backend: str = "opencv",  # Fast default, can use retinaface for accuracy
        analyze_interval: float = 2.0,  # Seconds between analyses
        callback: Optional[Callable[[VisionResult], None]] = None,
        recognition_threshold: float = 0.6,  # Lower = stricter matching
    ):
        self.detector_backend = detector_backend
        self.analyze_interval = analyze_interval
        self.callback = callback
        self.recognition_threshold = recognition_threshold
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_result: Optional[VisionResult] = None
        self._camera: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        
        # Face recognition database
        self.face_db = FaceDatabase()
        
        # Pre-load models on init (takes a few seconds)
        logger.info("Pre-loading DeepFace models...")
        self._preload_models()
        logger.info("Models loaded successfully")
    
    def _preload_models(self):
        """Pre-load DeepFace models to avoid cold start"""
        try:
            # Create a dummy image to trigger model loading
            dummy = np.zeros((224, 224, 3), dtype=np.uint8)
            dummy[100:124, 100:124] = 255  # Small white square
            
            # This will fail (no face) but loads the models
            try:
                DeepFace.analyze(
                    dummy,
                    actions=['emotion', 'age', 'gender'],
                    detector_backend=self.detector_backend,
                    enforce_detection=False,
                    silent=True
                )
            except:
                pass  # Expected - no face in dummy image
                
        except Exception as e:
            logger.warning(f"Model preload warning: {e}")
    
    def get_face_embedding(self, image: np.ndarray) -> Optional[List[float]]:
        """Extract face embedding from image for recognition"""
        try:
            embeddings = DeepFace.represent(
                image,
                model_name="Facenet512",  # Good balance of speed and accuracy
                detector_backend=self.detector_backend,
                enforce_detection=True,
            )
            if embeddings and len(embeddings) > 0:
                return embeddings[0]["embedding"]
        except Exception as e:
            logger.debug(f"Could not extract embedding: {e}")
        return None
    
    def enroll_face(self, image: np.ndarray, name: str, role: str = "friend") -> Optional[EnrolledFace]:
        """
        Enroll a face for recognition
        
        Args:
            image: BGR image containing the face
            name: Name of the person
            role: "owner", "friend", or "family"
            
        Returns:
            EnrolledFace if successful, None if failed
        """
        embedding = self.get_face_embedding(image)
        if embedding is None:
            logger.error("Could not extract face embedding for enrollment")
            return None
        
        # Generate unique ID
        import uuid
        face_id = str(uuid.uuid4())[:8]
        
        # If enrolling owner, remove any existing owner
        if role == "owner":
            existing_owner = self.face_db.get_owner()
            if existing_owner:
                self.face_db.remove(existing_owner.id)
        
        return self.face_db.enroll(face_id, name, role, embedding)
    
    def enroll_face_base64(self, image_b64: str, name: str, role: str = "friend") -> Optional[EnrolledFace]:
        """Enroll a face from base64-encoded image"""
        try:
            image_data = base64.b64decode(image_b64)
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Failed to decode image")
            return self.enroll_face(image, name, role)
        except Exception as e:
            logger.error(f"Failed to enroll face from base64: {e}")
            return None
    
    def identify_face(self, embedding: List[float]) -> tuple[Optional[str], Optional[str], float]:
        """
        Identify a face by comparing embedding to enrolled faces
        
        Returns:
            (name, role, confidence) or (None, None, 0) if not recognized
        """
        if not embedding or not self.face_db.faces:
            return None, None, 0.0
        
        best_match = None
        best_distance = float('inf')
        
        for face in self.face_db.faces.values():
            if not face.embedding:
                continue
            
            # Calculate cosine distance
            try:
                from scipy.spatial.distance import cosine
                distance = cosine(embedding, face.embedding)
            except ImportError:
                # Fallback to numpy if scipy not available
                a = np.array(embedding)
                b = np.array(face.embedding)
                distance = 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
            
            if distance < best_distance:
                best_distance = distance
                best_match = face
        
        # Convert distance to confidence (lower distance = higher confidence)
        confidence = max(0, 1 - best_distance)
        
        if best_match and best_distance < self.recognition_threshold:
            return best_match.name, best_match.role, confidence
        
        return None, None, confidence
    
    def analyze_image(self, image: np.ndarray, do_recognition: bool = True) -> VisionResult:
        """
        Analyze a single image for face, emotion, age, gender, and IDENTITY
        
        Args:
            image: BGR image from OpenCV
            do_recognition: Whether to attempt face recognition
            
        Returns:
            VisionResult with analysis data including identity
        """
        result = VisionResult()
        
        try:
            # Run DeepFace analysis
            analyses = DeepFace.analyze(
                image,
                actions=['emotion', 'age', 'gender'],
                detector_backend=self.detector_backend,
                enforce_detection=False,  # Don't throw if no face
                silent=True
            )
            
            # DeepFace returns a list (one per face found)
            if analyses and len(analyses) > 0:
                result.face_count = len(analyses)
                analysis = analyses[0]  # Take first/primary face
                
                result.face_detected = True
                result.attention = True
                
                # Emotion
                if 'emotion' in analysis:
                    emotions = analysis['emotion']
                    # Convert numpy floats to Python floats for JSON serialization
                    result.emotion_scores = {k: float(v) for k, v in emotions.items()}
                    result.emotion = max(emotions, key=emotions.get)
                
                # Age
                if 'age' in analysis:
                    result.age = int(analysis['age'])
                
                # Gender
                if 'gender' in analysis:
                    gender_data = analysis['gender']
                    if isinstance(gender_data, dict):
                        result.gender = max(gender_data, key=gender_data.get)
                        result.gender_confidence = float(gender_data.get(result.gender, 0)) / 100
                    else:
                        result.gender = str(gender_data)
                
                # Face confidence (from region if available)
                if 'face_confidence' in analysis:
                    result.face_confidence = float(analysis['face_confidence']) if analysis['face_confidence'] is not None else None
                elif 'region' in analysis:
                    conf = analysis['region'].get('confidence', None)
                    result.face_confidence = float(conf) if conf is not None else None
                
                # Face Recognition - identify who this is
                if do_recognition and self.face_db.has_owner():
                    try:
                        embedding = self.get_face_embedding(image)
                        if embedding:
                            name, role, confidence = self.identify_face(embedding)
                            result.identity = name
                            result.identity_role = role if role else "unknown"
                            result.identity_confidence = float(confidence) if confidence is not None else None
                            result.is_owner = (role == "owner")
                            
                            if name:
                                logger.debug(f"Recognized: {name} ({role}) confidence={confidence:.2f}")
                            else:
                                logger.debug(f"Unknown person (confidence={confidence:.2f})")
                    except Exception as e:
                        logger.debug(f"Recognition failed: {e}")
                        result.identity_role = "unknown"
                    
        except ValueError as e:
            # No face detected
            logger.debug(f"No face detected: {e}")
            result.face_detected = False
            result.attention = False
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            result.face_detected = False
            result.attention = False
        
        return result
    
    def analyze_base64(self, image_b64: str) -> VisionResult:
        """Analyze a base64-encoded image"""
        try:
            # Decode base64 to image
            image_data = base64.b64decode(image_b64)
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Failed to decode image")
            
            return self.analyze_image(image)
            
        except Exception as e:
            logger.error(f"Base64 decode error: {e}")
            return VisionResult()
    
    def start_continuous(self, camera_index: int = 0):
        """Start continuous analysis from webcam"""
        if self._running:
            logger.warning("Analyzer already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._analysis_loop, args=(camera_index,))
        self._thread.daemon = True
        self._thread.start()
        logger.info(f"Started continuous analysis from camera {camera_index}")
    
    def stop_continuous(self):
        """Stop continuous analysis"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self._camera:
            self._camera.release()
            self._camera = None
        logger.info("Stopped continuous analysis")
    
    def _analysis_loop(self, camera_index: int):
        """Main analysis loop (runs in thread)"""
        try:
            self._camera = cv2.VideoCapture(camera_index)
            if not self._camera.isOpened():
                logger.error(f"Failed to open camera {camera_index}")
                self._running = False
                return
            
            # Set camera properties for performance
            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._camera.set(cv2.CAP_PROP_FPS, 15)
            
            last_analysis = 0
            
            while self._running:
                ret, frame = self._camera.read()
                if not ret:
                    logger.warning("Failed to read frame")
                    time.sleep(0.1)
                    continue
                
                current_time = time.time()
                if current_time - last_analysis >= self.analyze_interval:
                    # Run analysis
                    result = self.analyze_image(frame)
                    
                    with self._lock:
                        self._latest_result = result
                    
                    # Call callback if set
                    if self.callback:
                        try:
                            self.callback(result)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                    
                    last_analysis = current_time
                    
                    logger.debug(
                        f"Analysis: face={result.face_detected}, "
                        f"emotion={result.emotion}, age={result.age}"
                    )
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.05)
                
        except Exception as e:
            logger.error(f"Analysis loop error: {e}")
        finally:
            if self._camera:
                self._camera.release()
                self._camera = None
            self._running = False
    
    def get_latest_result(self) -> Optional[VisionResult]:
        """Get the most recent analysis result"""
        with self._lock:
            return self._latest_result
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def capture_frame_for_enrollment(self, camera_index: int = 0) -> Optional[np.ndarray]:
        """Capture a single frame from webcam for face enrollment"""
        try:
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                logger.error(f"Could not open camera {camera_index}")
                return None
            
            # Warm up camera
            for _ in range(5):
                cap.read()
            
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                return frame
            return None
        except Exception as e:
            logger.error(f"Failed to capture frame: {e}")
            return None
    
    def enroll_from_webcam(self, name: str, role: str = "friend", camera_index: int = 0) -> Optional[EnrolledFace]:
        """Capture from webcam and enroll the face"""
        frame = self.capture_frame_for_enrollment(camera_index)
        if frame is None:
            return None
        return self.enroll_face(frame, name, role)
    
    def get_enrolled_faces(self) -> List[dict]:
        """Get list of enrolled faces (without embeddings)"""
        return [f.to_dict() for f in self.face_db.list_faces()]
    
    def remove_face(self, face_id: str) -> bool:
        """Remove an enrolled face"""
        return self.face_db.remove(face_id)
    
    def has_owner(self) -> bool:
        """Check if owner is enrolled"""
        return self.face_db.has_owner()
    
    def get_owner_name(self) -> Optional[str]:
        """Get owner's name if enrolled"""
        owner = self.face_db.get_owner()
        return owner.name if owner else None


# Emotion to description mapping for Galatea
EMOTION_DESCRIPTIONS = {
    "happy": "You look happy!",
    "sad": "You seem a bit down.",
    "angry": "You look frustrated.",
    "fear": "You seem worried.",
    "surprise": "You look surprised!",
    "disgust": "Something bothering you?",
    "neutral": "You seem calm.",
}

def get_emotion_description(emotion: str) -> str:
    """Get a natural description for an emotion"""
    return EMOTION_DESCRIPTIONS.get(emotion.lower(), f"You seem {emotion}.")

