# src/mcp/tools/video_orchestrator.py
"""
Parallel Video Processing Orchestrator with Context7 integration
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from src.mcp.tools.video_audio import AudioAgent, AudioExtractionResult
from src.mcp.tools.video_face import VideoAgent, FaceDetectionResult
from src.mcp.tools.context7 import context7_client
from src.common.jsonlog import jlog

log = logging.getLogger("video_orchestrator")


@dataclass
class Phase1Result:
    """Result of Phase 1 parallel processing"""
    success: bool
    audio_result: AudioExtractionResult
    video_result: FaceDetectionResult
    processing_time: float
    error: Optional[str] = None


class CircuitBreaker:
    """Circuit breaker for agent failure handling"""
    
    def __init__(self, failure_threshold: int = 3, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if circuit breaker allows execution"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def on_success(self):
        """Record successful execution"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def on_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class ParallelVideoOrchestrator:
    """
    Orchestrates parallel video processing agents for Phase 1 of PresGen-Video
    """
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.circuit_breakers = {
            "audio_agent": CircuitBreaker(),
            "video_agent": CircuitBreaker()
        }
    
    async def phase1_parallel_processing(self, video_path: str) -> Phase1Result:
        """
        Execute Phase 1 parallel processing (0-30s target)
        
        Runs AudioAgent and VideoAgent concurrently using asyncio.gather()
        for maximum speed optimization as per PRD requirements.
        
        Args:
            video_path: Path to the uploaded video file
            
        Returns:
            Phase1Result with both audio and video processing results
        """
        start_time = time.time()
        
        jlog(log, logging.INFO,
             event="phase1_parallel_start",
             job_id=self.job_id,
             video_path=video_path,
             target_time_secs=30)
        
        try:
            # Initialize agents
            audio_agent = AudioAgent(self.job_id)
            video_agent = VideoAgent(self.job_id)
            
            # Create parallel tasks with circuit breaker protection
            tasks = []
            
            # Audio processing task
            if self.circuit_breakers["audio_agent"].can_execute():
                tasks.append(self._execute_with_circuit_breaker(
                    "audio_agent",
                    audio_agent.extract_and_segment(video_path)
                ))
            else:
                tasks.append(self._create_circuit_breaker_fallback("audio"))
            
            # Video processing task  
            if self.circuit_breakers["video_agent"].can_execute():
                tasks.append(self._execute_with_circuit_breaker(
                    "video_agent", 
                    video_agent.detect_and_process_video(video_path)
                ))
            else:
                tasks.append(self._create_circuit_breaker_fallback("video"))
            
            jlog(log, logging.INFO,
                 event="phase1_agents_starting",
                 job_id=self.job_id,
                 audio_circuit_state=self.circuit_breakers["audio_agent"].state,
                 video_circuit_state=self.circuit_breakers["video_agent"].state)
            
            # Execute agents in parallel with timeout
            timeout_seconds = 35  # 5 seconds buffer over 30s target
            
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                jlog(log, logging.ERROR,
                     event="phase1_timeout",
                     job_id=self.job_id,
                     timeout_secs=timeout_seconds)
                
                return Phase1Result(
                    success=False,
                    audio_result=AudioExtractionResult(False, "", [], 0, 0, "", time.time() - start_time, "Phase 1 timeout"),
                    video_result=FaceDetectionResult(False, None, [], None, time.time() - start_time, 0.0, "Phase 1 timeout"),
                    processing_time=time.time() - start_time,
                    error="Phase 1 processing exceeded 35 second timeout"
                )
            
            # Process results
            audio_result, video_result = results
            
            # Handle individual agent failures
            if isinstance(audio_result, Exception):
                jlog(log, logging.ERROR,
                     event="audio_agent_exception",
                     job_id=self.job_id,
                     error=str(audio_result))
                audio_result = AudioExtractionResult(
                    False, "", [], 0, 0, "", time.time() - start_time, str(audio_result)
                )
            
            if isinstance(video_result, Exception):
                jlog(log, logging.ERROR,
                     event="video_agent_exception", 
                     job_id=self.job_id,
                     error=str(video_result))
                video_result = FaceDetectionResult(
                    False, None, [], None, time.time() - start_time, 0.0, str(video_result)
                )
            
            processing_time = time.time() - start_time
            overall_success = audio_result.success and video_result.success
            
            # Log completion
            jlog(log, logging.INFO,
                 event="phase1_parallel_complete",
                 job_id=self.job_id,
                 processing_time_secs=round(processing_time, 2),
                 audio_success=audio_result.success,
                 video_success=video_result.success,
                 overall_success=overall_success,
                 target_met=processing_time < 30)
            
            return Phase1Result(
                success=overall_success,
                audio_result=audio_result,
                video_result=video_result,
                processing_time=processing_time,
                error=None if overall_success else "One or more agents failed"
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Phase 1 orchestration failed: {str(e)}"
            
            jlog(log, logging.ERROR,
                 event="phase1_orchestration_exception",
                 job_id=self.job_id,
                 error=error_msg,
                 processing_time_secs=round(processing_time, 2))
            
            return Phase1Result(
                success=False,
                audio_result=AudioExtractionResult(False, "", [], 0, 0, "", processing_time, error_msg),
                video_result=FaceDetectionResult(False, None, [], None, processing_time, 0.0, error_msg),
                processing_time=processing_time,
                error=error_msg
            )
    
    async def _execute_with_circuit_breaker(self, agent_name: str, task) -> Any:
        """Execute agent task with circuit breaker protection"""
        
        try:
            result = await task
            
            # Record success
            if hasattr(result, 'success') and result.success:
                self.circuit_breakers[agent_name].on_success()
            else:
                self.circuit_breakers[agent_name].on_failure()
            
            return result
            
        except Exception as e:
            self.circuit_breakers[agent_name].on_failure()
            raise e
    
    async def _create_circuit_breaker_fallback(self, agent_type: str):
        """Create fallback result when circuit breaker is open"""
        
        jlog(log, logging.WARNING,
             event="circuit_breaker_fallback",
             job_id=self.job_id,
             agent_type=agent_type)
        
        if agent_type == "audio":
            return AudioExtractionResult(
                success=False,
                audio_path="",
                segments=[],
                duration=0,
                sample_rate=0,
                format="",
                extraction_time=0,
                error="Circuit breaker open - using fallback"
            )
        else:  # video
            return FaceDetectionResult(
                success=False,
                video_metadata=None,
                face_detections=[],
                stable_crop_region=None,
                detection_time=0,
                confidence_score=0.0,
                error="Circuit breaker open - using fallback"
            )
    
    async def get_processing_metadata(self) -> Dict[str, Any]:
        """Get additional metadata for the processing job"""
        
        try:
            # Get Context7 documentation status
            context_status = {}
            patterns = ["ffmpeg:audio_extraction", "opencv-python:face_detection"]
            
            for pattern in patterns:
                library, topic = pattern.split(":")
                try:
                    docs = await context7_client.get_docs(library, topic)
                    context_status[pattern] = "available"
                except:
                    context_status[pattern] = "unavailable"
            
            # Get circuit breaker states
            circuit_status = {
                name: breaker.state 
                for name, breaker in self.circuit_breakers.items()
            }
            
            return {
                "context7_status": context_status,
                "circuit_breakers": circuit_status,
                "job_dir": str(Path(f"/tmp/jobs/{self.job_id}")),
                "timestamp": time.time()
            }
            
        except Exception as e:
            jlog(log, logging.WARNING,
                 event="metadata_collection_failed",
                 job_id=self.job_id,
                 error=str(e))
            
            return {
                "error": str(e),
                "timestamp": time.time()
            }


if __name__ == "__main__":
    # Test parallel orchestrator
    async def test_parallel_orchestrator():
        print("Testing Parallel Video Orchestrator...")
        
        # Test with the uploaded video
        test_video = "/tmp/jobs/cd238746-7d7d-4041-8f3e-a5e512c9a406/raw_video.mp4"
        
        if not os.path.exists(test_video):
            print(f"Test video not found: {test_video}")
            return
        
        orchestrator = ParallelVideoOrchestrator("test_orchestrator_job")
        
        print("Starting Phase 1 parallel processing...")
        start_time = time.time()
        
        result = await orchestrator.phase1_parallel_processing(test_video)
        
        total_time = time.time() - start_time
        
        print(f"\n=== PHASE 1 RESULTS ===")
        print(f"Overall Success: {'YES' if result.success else 'NO'}")
        print(f"Processing Time: {result.processing_time:.2f} seconds")
        print(f"Target Met (<30s): {'YES' if result.processing_time < 30 else 'NO'}")
        
        print(f"\n--- Audio Results ---")
        print(f"Success: {'YES' if result.audio_result.success else 'NO'}")
        print(f"Duration: {result.audio_result.duration:.2f} seconds")
        print(f"Segments: {len(result.audio_result.segments)}")
        
        print(f"\n--- Video Results ---")
        print(f"Success: {'YES' if result.video_result.success else 'NO'}")
        if result.video_result.video_metadata:
            print(f"Resolution: {result.video_result.video_metadata.width}x{result.video_result.video_metadata.height}")
        print(f"Face Confidence: {result.video_result.confidence_score:.2f}")
        print(f"Stable Crop: {'YES' if result.video_result.stable_crop_region else 'NO'}")
        
        if result.error:
            print(f"\nError: {result.error}")
        
        # Test metadata collection
        metadata = await orchestrator.get_processing_metadata()
        print(f"\nContext7 Status: {metadata.get('context7_status', {})}")
    
    import os
    asyncio.run(test_parallel_orchestrator())