# src/mcp/tools/video_face.py
"""
VideoAgent for parallel face detection and video metadata with Context7 integration
"""

import asyncio
import logging
import time
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from src.mcp.tools.context7 import context7_client
from src.common.jsonlog import jlog

log = logging.getLogger("video_face")


@dataclass
class FaceDetection:
    """Face detection result for a single frame"""
    frame_number: int
    timestamp: float
    faces: List[Tuple[int, int, int, int]]  # (x, y, w, h) rectangles
    confidence: float
    best_face: Optional[Tuple[int, int, int, int]] = None


@dataclass
class VideoMetadata:
    """Video file metadata"""
    duration: float
    fps: float
    width: int
    height: int
    total_frames: int
    format: str
    codec: str


@dataclass
class FaceDetectionResult:
    """Result of face detection process"""
    success: bool
    video_metadata: VideoMetadata
    face_detections: List[FaceDetection]
    stable_crop_region: Optional[Tuple[int, int, int, int]]  # (x, y, w, h)
    detection_time: float
    confidence_score: float
    error: Optional[str] = None


class VideoAgent:
    """Agent for face detection and video metadata using Context7-optimized patterns"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.job_dir = Path(f"/tmp/jobs/{job_id}")
        self.job_dir.mkdir(parents=True, exist_ok=True)
        self.face_cascade = None
    
    async def detect_and_process_video(self, video_path: str) -> FaceDetectionResult:
        """
        Main entry point for video processing
        Combines metadata extraction and face detection
        """
        start_time = time.time()
        
        jlog(log, logging.INFO,
             event="video_processing_start",
             job_id=self.job_id,
             video_path=video_path)
        
        try:
            # Get Context7 patterns for face detection
            context = await context7_client.get_docs("opencv-python", "face_detection")
            
            # Initialize face detection with Context7 settings
            await self._initialize_face_detection(context)
            
            # Extract video metadata
            metadata = await self._extract_video_metadata(video_path)
            if not metadata:
                raise Exception("Failed to extract video metadata")
            
            # Perform face detection
            detections = await self._detect_faces_in_video(video_path, metadata, context)
            
            # Calculate stable crop region
            stable_crop = self._calculate_stable_crop(detections, metadata)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(detections)
            
            detection_time = time.time() - start_time
            
            result = FaceDetectionResult(
                success=True,
                video_metadata=metadata,
                face_detections=detections,
                stable_crop_region=stable_crop,
                detection_time=detection_time,
                confidence_score=confidence
            )
            
            jlog(log, logging.INFO,
                 event="video_processing_success",
                 job_id=self.job_id,
                 duration_secs=round(detection_time, 2),
                 faces_detected=len([d for d in detections if d.faces]),
                 confidence_score=round(confidence, 2),
                 stable_crop=stable_crop is not None)
            
            return result
            
        except Exception as e:
            detection_time = time.time() - start_time
            error_msg = f"Video processing failed: {str(e)}"
            
            jlog(log, logging.ERROR,
                 event="video_processing_exception",
                 job_id=self.job_id,
                 error=error_msg,
                 duration_secs=round(detection_time, 2))
            
            return FaceDetectionResult(
                success=False,
                video_metadata=VideoMetadata(0, 0, 0, 0, 0, "", ""),
                face_detections=[],
                stable_crop_region=None,
                detection_time=detection_time,
                confidence_score=0.0,
                error=error_msg
            )
    
    async def _initialize_face_detection(self, context: Dict[str, Any]):
        """Initialize face detection with Context7-optimized settings"""
        
        try:
            # Use Context7 recommended method or fall back to Haar cascades
            if "current_api" in context:
                jlog(log, logging.INFO,
                     event="face_detection_context7_init",
                     job_id=self.job_id,
                     method=context.get("optimal_method", "unknown"))
            
            # Initialize OpenCV face cascade
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            
            if self.face_cascade.empty():
                raise Exception("Failed to load face detection cascade")
                
        except Exception as e:
            jlog(log, logging.WARNING,
                 event="face_detection_init_fallback",
                 job_id=self.job_id,
                 error=str(e))
            # Will use fallback detection methods
    
    async def _extract_video_metadata(self, video_path: str) -> Optional[VideoMetadata]:
        """Extract video metadata using OpenCV"""
        
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                jlog(log, logging.ERROR,
                     event="video_metadata_open_failed",
                     job_id=self.job_id,
                     video_path=video_path)
                return None
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            metadata = VideoMetadata(
                duration=duration,
                fps=fps,
                width=width,
                height=height,
                total_frames=frame_count,
                format="mp4",  # Assume MP4 for now
                codec="h264"   # Common default
            )
            
            jlog(log, logging.INFO,
                 event="video_metadata_extracted",
                 job_id=self.job_id,
                 duration=duration,
                 fps=fps,
                 resolution=f"{width}x{height}",
                 total_frames=frame_count)
            
            return metadata
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="video_metadata_failed",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    async def _detect_faces_in_video(self, video_path: str, metadata: VideoMetadata, 
                                   context: Dict[str, Any]) -> List[FaceDetection]:
        """Detect faces in video frames using Context7-optimized settings"""
        
        detections = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return detections
        
        try:
            # Get Context7 performance settings
            settings = context.get("performance_settings", {})
            scale_factor = settings.get("scaleFactor", 1.1)
            min_neighbors = settings.get("minNeighbors", 5)
            min_size = eval(settings.get("minSize", "(30, 30)"))
            
            # Sample frames for face detection (every 2 seconds for speed)
            sample_interval = max(1, int(metadata.fps * 2))  # Every 2 seconds
            frame_number = 0
            
            jlog(log, logging.INFO,
                 event="face_detection_start",
                 job_id=self.job_id,
                 scale_factor=scale_factor,
                 min_neighbors=min_neighbors,
                 sample_interval=sample_interval)
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Only process sampled frames
                if frame_number % sample_interval == 0:
                    timestamp = frame_number / metadata.fps
                    
                    # Convert to grayscale for face detection (Context7 best practice)
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    # Detect faces
                    faces = []
                    if self.face_cascade:
                        face_rects = self.face_cascade.detectMultiScale(
                            gray,
                            scaleFactor=scale_factor,
                            minNeighbors=min_neighbors,
                            minSize=min_size
                        )
                        faces = [(int(x), int(y), int(w), int(h)) for x, y, w, h in face_rects]
                    
                    # Calculate confidence based on face size and position
                    confidence = self._calculate_frame_confidence(faces, frame.shape)
                    
                    # Find best face (largest, most centered)
                    best_face = self._find_best_face(faces, frame.shape) if faces else None
                    
                    detection = FaceDetection(
                        frame_number=frame_number,
                        timestamp=timestamp,
                        faces=faces,
                        confidence=confidence,
                        best_face=best_face
                    )
                    
                    detections.append(detection)
                
                frame_number += 1
                
                # Yield control occasionally for async processing
                if frame_number % 100 == 0:
                    await asyncio.sleep(0.001)
            
            cap.release()
            
            jlog(log, logging.INFO,
                 event="face_detection_complete",
                 job_id=self.job_id,
                 total_detections=len(detections),
                 frames_with_faces=len([d for d in detections if d.faces]))
            
            return detections
            
        except Exception as e:
            cap.release()
            jlog(log, logging.ERROR,
                 event="face_detection_failed",
                 job_id=self.job_id,
                 error=str(e))
            return detections
    
    def _calculate_frame_confidence(self, faces: List[Tuple[int, int, int, int]], 
                                  frame_shape: Tuple[int, int, int]) -> float:
        """Calculate confidence score for face detection in a frame"""
        
        if not faces:
            return 0.0
        
        height, width = frame_shape[:2]
        
        # Score based on face size and position
        scores = []
        for x, y, w, h in faces:
            # Size score (larger faces = higher confidence)
            size_score = min(w * h / (width * height), 0.3)  # Max 30% of frame
            
            # Position score (centered faces = higher confidence)
            center_x, center_y = x + w//2, y + h//2
            frame_center_x, frame_center_y = width//2, height//2
            distance = ((center_x - frame_center_x)**2 + (center_y - frame_center_y)**2)**0.5
            max_distance = (width**2 + height**2)**0.5
            position_score = 1.0 - (distance / max_distance)
            
            scores.append(size_score + position_score * 0.5)
        
        return max(scores) if scores else 0.0
    
    def _find_best_face(self, faces: List[Tuple[int, int, int, int]], 
                       frame_shape: Tuple[int, int, int]) -> Optional[Tuple[int, int, int, int]]:
        """Find the best face (largest and most centered) in the frame"""
        
        if not faces:
            return None
        
        height, width = frame_shape[:2]
        best_face = None
        best_score = -1
        
        for face in faces:
            x, y, w, h = face
            
            # Combined size and position score
            size_score = w * h
            center_x, center_y = x + w//2, y + h//2
            distance_from_center = ((center_x - width//2)**2 + (center_y - height//2)**2)**0.5
            position_score = 1000 / (1 + distance_from_center)  # Inverse distance
            
            total_score = size_score + position_score
            
            if total_score > best_score:
                best_score = total_score
                best_face = face
        
        return best_face
    
    def _calculate_stable_crop(self, detections: List[FaceDetection], 
                             metadata: VideoMetadata) -> Optional[Tuple[int, int, int, int]]:
        """Calculate stable crop region based on face detections"""
        
        valid_faces = [d.best_face for d in detections if d.best_face]
        
        if not valid_faces:
            # No faces detected - return center crop
            crop_size = min(metadata.width, metadata.height) // 2
            x = (metadata.width - crop_size) // 2
            y = (metadata.height - crop_size) // 2
            return (x, y, crop_size, crop_size)
        
        # Calculate average face position and size
        avg_x = sum(x for x, y, w, h in valid_faces) / len(valid_faces)
        avg_y = sum(y for x, y, w, h in valid_faces) / len(valid_faces)
        avg_w = sum(w for x, y, w, h in valid_faces) / len(valid_faces)
        avg_h = sum(h for x, y, w, h in valid_faces) / len(valid_faces)
        
        # Create crop region with padding around average face position
        padding = max(avg_w, avg_h) * 1.5  # 50% padding
        crop_x = max(0, int(avg_x + avg_w//2 - padding//2))
        crop_y = max(0, int(avg_y + avg_h//2 - padding//2))
        crop_w = min(metadata.width - crop_x, int(padding))
        crop_h = min(metadata.height - crop_y, int(padding))
        
        # Ensure minimum size
        crop_size = min(crop_w, crop_h)
        if crop_size < 200:  # Minimum 200px
            crop_size = min(metadata.width, metadata.height) // 2
            crop_x = (metadata.width - crop_size) // 2
            crop_y = (metadata.height - crop_size) // 2
            crop_w = crop_h = crop_size
        
        return (crop_x, crop_y, crop_w, crop_h)
    
    def _calculate_confidence(self, detections: List[FaceDetection]) -> float:
        """Calculate overall confidence score for face detection"""
        
        if not detections:
            return 0.0
        
        # Percentage of frames with faces
        frames_with_faces = len([d for d in detections if d.faces])
        frame_percentage = frames_with_faces / len(detections)
        
        # Average confidence of detections with faces
        confident_detections = [d for d in detections if d.confidence > 0.3]
        avg_confidence = sum(d.confidence for d in confident_detections) / len(confident_detections) if confident_detections else 0
        
        # Combined score
        return (frame_percentage * 0.6 + avg_confidence * 0.4)


if __name__ == "__main__":
    # Test VideoAgent
    async def test_video_agent():
        print("Testing VideoAgent...")
        
        # Test with the uploaded video
        test_video = "/tmp/jobs/cd238746-7d7d-4041-8f3e-a5e512c9a406/raw_video.mp4"
        
        if not os.path.exists(test_video):
            print(f"Test video not found: {test_video}")
            return
        
        agent = VideoAgent("test_video_job")
        result = await agent.detect_and_process_video(test_video)
        
        print(f"Video processing: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Duration: {result.video_metadata.duration:.2f} seconds")
        print(f"Resolution: {result.video_metadata.width}x{result.video_metadata.height}")
        print(f"Face detections: {len(result.face_detections)}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Processing time: {result.detection_time:.2f} seconds")
        print(f"Stable crop: {result.stable_crop_region}")
        
        if result.error:
            print(f"Error: {result.error}")
    
    import os
    asyncio.run(test_video_agent())