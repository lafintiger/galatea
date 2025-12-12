"""
Galatea Vision Analyzer
DeepFace wrapper for emotion, age, gender, and presence detection
"""

import asyncio
import base64
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, List
import threading

import cv2
import numpy as np
from deepface import DeepFace

logger = logging.getLogger(__name__)


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
        }


class VisionAnalyzer:
    """
    Continuous vision analyzer using DeepFace
    
    Features:
    - Emotion detection (7 emotions)
    - Age estimation
    - Gender detection
    - Presence/attention detection
    """
    
    def __init__(
        self,
        detector_backend: str = "opencv",  # Fast default, can use retinaface for accuracy
        analyze_interval: float = 2.0,  # Seconds between analyses
        callback: Optional[Callable[[VisionResult], None]] = None,
    ):
        self.detector_backend = detector_backend
        self.analyze_interval = analyze_interval
        self.callback = callback
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_result: Optional[VisionResult] = None
        self._camera: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        
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
    
    def analyze_image(self, image: np.ndarray) -> VisionResult:
        """
        Analyze a single image for face, emotion, age, gender
        
        Args:
            image: BGR image from OpenCV
            
        Returns:
            VisionResult with analysis data
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
                analysis = analyses[0]  # Take first/primary face
                
                result.face_detected = True
                result.attention = True
                
                # Emotion
                if 'emotion' in analysis:
                    emotions = analysis['emotion']
                    result.emotion_scores = emotions
                    result.emotion = max(emotions, key=emotions.get)
                
                # Age
                if 'age' in analysis:
                    result.age = int(analysis['age'])
                
                # Gender
                if 'gender' in analysis:
                    gender_data = analysis['gender']
                    if isinstance(gender_data, dict):
                        result.gender = max(gender_data, key=gender_data.get)
                        result.gender_confidence = gender_data.get(result.gender, 0) / 100
                    else:
                        result.gender = str(gender_data)
                
                # Face confidence (from region if available)
                if 'face_confidence' in analysis:
                    result.face_confidence = analysis['face_confidence']
                elif 'region' in analysis:
                    result.face_confidence = analysis['region'].get('confidence', None)
                    
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

