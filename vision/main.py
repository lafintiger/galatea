"""
Galatea Vision Service
FastAPI server providing face/emotion analysis via DeepFace

Endpoints:
- POST /analyze - Analyze a single image (base64)
- POST /start - Start continuous webcam analysis
- POST /stop - Stop continuous analysis  
- GET /status - Get current analysis status and latest result
- GET /health - Health check
- WebSocket /ws - Real-time emotion updates
"""

import asyncio
import base64
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, List

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyzer import VisionAnalyzer, VisionResult, EnrolledFace, get_emotion_description

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
DETECTOR_BACKEND = os.getenv("DETECTOR_BACKEND", "opencv")
ANALYZE_INTERVAL = float(os.getenv("ANALYZE_INTERVAL", "2.0"))
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

# Global analyzer instance
analyzer: Optional[VisionAnalyzer] = None

# WebSocket connections for real-time updates
websocket_connections: List[WebSocket] = []


async def broadcast_result(result: VisionResult):
    """Broadcast analysis result to all connected WebSocket clients"""
    if not websocket_connections:
        return
    
    data = result.to_dict()
    data["description"] = get_emotion_description(result.emotion) if result.emotion else None
    
    disconnected = []
    for ws in websocket_connections:
        try:
            await ws.send_json(data)
        except Exception:
            disconnected.append(ws)
    
    # Remove disconnected clients
    for ws in disconnected:
        websocket_connections.remove(ws)


def on_analysis_result(result: VisionResult):
    """Callback for continuous analysis results"""
    # Schedule broadcast on event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(broadcast_result(result))
    except RuntimeError:
        pass  # No event loop in thread


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global analyzer
    
    logger.info("🔧 Initializing Galatea Vision Service...")
    logger.info(f"   Detector: {DETECTOR_BACKEND}")
    logger.info(f"   Interval: {ANALYZE_INTERVAL}s")
    
    # Initialize analyzer (loads models)
    analyzer = VisionAnalyzer(
        detector_backend=DETECTOR_BACKEND,
        analyze_interval=ANALYZE_INTERVAL,
        callback=on_analysis_result
    )
    
    logger.info("👁️ Galatea Vision Service ready!")
    
    yield
    
    # Cleanup
    if analyzer and analyzer.is_running:
        analyzer.stop_continuous()
    logger.info("👁️ Galatea Vision Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Galatea Vision",
    description="Face and emotion analysis service for Galatea AI companion",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class AnalyzeRequest(BaseModel):
    """Request to analyze a single image"""
    image: str  # Base64 encoded image
    

class AnalyzeResponse(BaseModel):
    """Response from image analysis"""
    face_detected: bool
    emotion: Optional[str] = None
    emotion_scores: Optional[dict] = None
    emotion_description: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    attention: bool = False
    timestamp: str


class StatusResponse(BaseModel):
    """Current status of the vision service"""
    eyes_open: bool  # Is continuous analysis running?
    detector: str
    interval: float
    latest_result: Optional[dict] = None
    owner_enrolled: bool = False
    owner_name: Optional[str] = None


class EnrollFaceRequest(BaseModel):
    """Request to enroll a face"""
    name: str
    role: str = "friend"  # "owner", "friend", "family"
    image: Optional[str] = None  # Base64 image, or None to capture from webcam


class EnrollFaceResponse(BaseModel):
    """Response from face enrollment"""
    success: bool
    face_id: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    message: str


class FaceListResponse(BaseModel):
    """List of enrolled faces"""
    faces: List[dict]
    owner_enrolled: bool
    owner_name: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    eyes_open: bool


# Endpoints

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="galatea-vision",
        eyes_open=analyzer.is_running if analyzer else False
    )


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current status and latest analysis result"""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    latest = analyzer.get_latest_result()
    
    return StatusResponse(
        eyes_open=analyzer.is_running,
        detector=DETECTOR_BACKEND,
        interval=ANALYZE_INTERVAL,
        latest_result=latest.to_dict() if latest else None,
        owner_enrolled=analyzer.has_owner(),
        owner_name=analyzer.get_owner_name(),
    )


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_image(request: AnalyzeRequest):
    """
    Analyze a single base64-encoded image
    
    Use this for one-off analysis (e.g., when user sends a photo)
    """
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    result = analyzer.analyze_base64(request.image)
    
    return AnalyzeResponse(
        face_detected=result.face_detected,
        emotion=result.emotion,
        emotion_scores=result.emotion_scores,
        emotion_description=get_emotion_description(result.emotion) if result.emotion else None,
        age=result.age,
        gender=result.gender,
        attention=result.attention,
        timestamp=result.timestamp.isoformat()
    )


@app.post("/start")
async def start_continuous(camera: int = CAMERA_INDEX):
    """
    Start continuous webcam analysis ("Open eyes")
    
    Args:
        camera: Camera index (default 0)
    """
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    if analyzer.is_running:
        return {"message": "Already running", "eyes_open": True}
    
    analyzer.start_continuous(camera_index=camera)
    
    logger.info("👁️ Eyes opened - continuous analysis started")
    return {"message": "Continuous analysis started", "eyes_open": True}


@app.post("/stop")
async def stop_continuous():
    """Stop continuous webcam analysis ("Close eyes")"""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    if not analyzer.is_running:
        return {"message": "Already stopped", "eyes_open": False}
    
    analyzer.stop_continuous()
    
    logger.info("Eyes closed - continuous analysis stopped")
    return {"message": "Continuous analysis stopped", "eyes_open": False}


# ============== Face Recognition Endpoints ==============

@app.post("/faces/enroll", response_model=EnrollFaceResponse)
async def enroll_face(request: EnrollFaceRequest):
    """
    Enroll a face for recognition
    
    - If image is provided (base64), use that
    - If no image, capture from webcam
    - role can be: "owner", "friend", "family"
    """
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    try:
        if request.image:
            # Enroll from provided image
            face = analyzer.enroll_face_base64(request.image, request.name, request.role)
        else:
            # Capture from webcam
            face = analyzer.enroll_from_webcam(request.name, request.role, CAMERA_INDEX)
        
        if face:
            role_msg = "Owner" if request.role == "owner" else request.role.capitalize()
            logger.info(f"Enrolled {role_msg}: {request.name}")
            return EnrollFaceResponse(
                success=True,
                face_id=face.id,
                name=face.name,
                role=face.role,
                message=f"Successfully enrolled {request.name} as {role_msg}"
            )
        else:
            return EnrollFaceResponse(
                success=False,
                message="Could not detect a face in the image. Please try again with a clear face photo."
            )
    except Exception as e:
        logger.error(f"Enrollment error: {e}")
        return EnrollFaceResponse(
            success=False,
            message=f"Enrollment failed: {str(e)}"
        )


@app.get("/faces", response_model=FaceListResponse)
async def list_faces():
    """List all enrolled faces"""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    return FaceListResponse(
        faces=analyzer.get_enrolled_faces(),
        owner_enrolled=analyzer.has_owner(),
        owner_name=analyzer.get_owner_name(),
    )


@app.delete("/faces/{face_id}")
async def delete_face(face_id: str):
    """Remove an enrolled face"""
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    if analyzer.remove_face(face_id):
        return {"success": True, "message": f"Face {face_id} removed"}
    else:
        raise HTTPException(status_code=404, detail=f"Face {face_id} not found")


@app.post("/faces/capture")
async def capture_for_enrollment(camera: int = CAMERA_INDEX):
    """
    Capture a frame from webcam and return as base64
    Use this to preview before enrolling
    """
    if not analyzer:
        raise HTTPException(status_code=503, detail="Analyzer not initialized")
    
    frame = analyzer.capture_frame_for_enrollment(camera)
    if frame is None:
        raise HTTPException(status_code=500, detail="Could not capture frame from webcam")
    
    # Encode as JPEG
    _, buffer = cv2.imencode('.jpg', frame)
    image_b64 = base64.b64encode(buffer).decode('utf-8')
    
    return {
        "image": image_b64,
        "message": "Frame captured. Use this image to enroll a face."
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time emotion updates
    
    Clients connecting here will receive analysis results in real-time
    when continuous analysis is running.
    """
    await websocket.accept()
    websocket_connections.append(websocket)
    logger.info(f"WebSocket client connected ({len(websocket_connections)} total)")
    
    try:
        # Send current status
        await websocket.send_json({
            "type": "connected",
            "eyes_open": analyzer.is_running if analyzer else False
        })
        
        # Keep connection alive
        while True:
            try:
                # Wait for client messages (ping/pong or commands)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Handle commands
                if data == "status":
                    latest = analyzer.get_latest_result() if analyzer else None
                    await websocket.send_json({
                        "type": "status",
                        "eyes_open": analyzer.is_running if analyzer else False,
                        "latest": latest.to_dict() if latest else None
                    })
                elif data == "ping":
                    await websocket.send_text("pong")
                    
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_text("ping")
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected ({len(websocket_connections)} remaining)")


# Additional utility endpoints

@app.get("/emotions")
async def list_emotions():
    """List all detectable emotions with descriptions"""
    from analyzer import EMOTION_DESCRIPTIONS
    return {
        "emotions": list(EMOTION_DESCRIPTIONS.keys()),
        "descriptions": EMOTION_DESCRIPTIONS
    }


@app.get("/detectors")
async def list_detectors():
    """List available face detector backends"""
    return {
        "available": [
            "opencv",      # Fast, CPU-friendly
            "ssd",         # Good balance
            "mtcnn",       # Accurate
            "retinaface",  # Most accurate, slower
            "mediapipe",   # Good for real-time
            "yolov8n",     # Fast YOLO
        ],
        "current": DETECTOR_BACKEND,
        "recommendations": {
            "fast": "opencv",
            "balanced": "ssd",
            "accurate": "retinaface"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)

