# src/mcp/tools/video_transcription.py
"""
TranscriptionAgent for video processing with Whisper and Context7 integration
"""

# CRITICAL: Import OpenMP override FIRST
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
import openmp_override  # This must be first

import asyncio
import logging
import time
import os

# Suppress OpenMP warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="whisper")
warnings.filterwarnings("ignore", message=".*FP16 is not supported on CPU.*")
warnings.filterwarnings("ignore", message=".*omp_set_nested.*")

# Defer whisper import to avoid startup crashes - import only when needed
whisper = None
torch = None

def _lazy_import_whisper():
    """Lazy import whisper with full OpenMP protection"""
    global whisper, torch
    if whisper is None:
        # Additional protection right before import
        import os
        os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
        os.environ['OMP_MAX_ACTIVE_LEVELS'] = '1'
        
        import whisper as _whisper
        import torch as _torch
        
        # Force single-threaded execution
        _torch.set_num_threads(1)
        
        whisper = _whisper
        torch = _torch
        
    return whisper, torch
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.mcp.tools.context7 import context7_client
from src.mcp.tools.video_audio import AudioSegment
from src.common.jsonlog import jlog

log = logging.getLogger("video_transcription")


@dataclass
class TranscriptSegment:
    """Individual transcript segment with timing"""
    start_time: float
    end_time: float
    text: str
    confidence: float
    words: Optional[List[Dict[str, Any]]] = None


@dataclass
class TranscriptionResult:
    """Complete transcription result"""
    success: bool
    segments: List[TranscriptSegment]
    full_text: str
    language: str
    duration: float
    processing_time: float
    model_used: str
    error: Optional[str] = None


class TranscriptionAgent:
    """Agent for audio transcription using Whisper with Context7 optimization"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.job_dir = Path(f"/tmp/jobs/{job_id}")
        self.whisper_model = None
        self.model_name = "base"  # Default model (best speed/quality for demo)
    
    async def transcribe_audio(self, audio_path: str) -> TranscriptionResult:
        """
        Transcribe audio using Whisper with Context7-optimized settings
        
        Args:
            audio_path: Path to extracted audio file
            
        Returns:
            TranscriptionResult with segments and timing
        """
        start_time = time.time()
        
        jlog(log, logging.INFO,
             event="transcription_start",
             job_id=self.job_id,
             audio_path=audio_path,
             model=self.model_name)
        
        try:
            # Get Context7 optimization patterns
            context = await context7_client.get_docs("whisper", "transcription")
            
            # Initialize Whisper model with Context7 settings
            await self._initialize_whisper_model(context)
            
            # Transcribe with optimized settings
            result = await self._transcribe_with_whisper(audio_path, context)
            
            # Process segments for video timing
            segments = self._process_transcript_segments(result)
            
            processing_time = time.time() - start_time
            
            transcription_result = TranscriptionResult(
                success=True,
                segments=segments,
                full_text=result.get("text", ""),
                language=result.get("language", "en"),
                duration=result.get("duration", 0),
                processing_time=processing_time,
                model_used=self.model_name
            )
            
            jlog(log, logging.INFO,
                 event="transcription_success",
                 job_id=self.job_id,
                 duration_secs=round(processing_time, 2),
                 segments_count=len(segments),
                 text_length=len(transcription_result.full_text),
                 language=transcription_result.language,
                 model=self.model_name)
            
            return transcription_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Transcription failed: {str(e)}"
            
            jlog(log, logging.ERROR,
                 event="transcription_exception",
                 job_id=self.job_id,
                 error=error_msg,
                 duration_secs=round(processing_time, 2))
            
            return TranscriptionResult(
                success=False,
                segments=[],
                full_text="",
                language="",
                duration=0,
                processing_time=processing_time,
                model_used=self.model_name,
                error=error_msg
            )
    
    async def _initialize_whisper_model(self, context: Dict[str, Any]):
        """Initialize Whisper model with Context7 optimization and lazy loading"""
        
        try:
            # Lazy import whisper with full protection
            whisper_lib, torch_lib = _lazy_import_whisper()
            
            # Use Context7 recommended model if available
            if "optimal_model" in context:
                recommended_model = context["optimal_model"]
                if recommended_model in whisper_lib.available_models():
                    self.model_name = recommended_model
                    
            # Check performance settings
            performance_settings = context.get("performance_settings", {})
            if performance_settings.get("model") in whisper_lib.available_models():
                self.model_name = performance_settings["model"]
            
            jlog(log, logging.INFO,
                 event="whisper_model_loading",
                 job_id=self.job_id,
                 model=self.model_name,
                 device="cpu",  # We verified CUDA is not available
                 context7_guided=bool("optimal_model" in context))
            
            # Load model (this will download if not cached) with OpenMP protection
            try:
                # Additional OpenMP protection before model loading
                os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
                import warnings
                warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")
                
                self.whisper_model = whisper_lib.load_model(self.model_name, device="cpu")
            except Exception as model_error:
                jlog(log, logging.ERROR,
                     event="whisper_model_load_error",
                     job_id=self.job_id,
                     model=self.model_name,
                     error=str(model_error))
                raise model_error
            
            jlog(log, logging.INFO,
                 event="whisper_model_loaded",
                 job_id=self.job_id,
                 model=self.model_name)
            
        except Exception as e:
            # Fallback to tiny model for demo reliability
            jlog(log, logging.WARNING,
                 event="whisper_model_fallback",
                 job_id=self.job_id,
                 error=str(e),
                 fallback_model="tiny")
            
            self.model_name = "tiny"
            # Fallback model loading with OpenMP protection  
            os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
            whisper_lib, _ = _lazy_import_whisper()
            self.whisper_model = whisper_lib.load_model("tiny", device="cpu")
    
    async def _transcribe_with_whisper(self, audio_path: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform transcription with Context7-optimized parameters"""
        
        # Get Context7 optimization settings
        settings = context.get("performance_settings", {})
        
        # Build transcription options
        transcribe_options = {
            "language": settings.get("language", "en"),  # Default to English
            "word_timestamps": settings.get("word_timestamps", True),  # For precise timing
            "fp16": settings.get("fp16", False),  # CPU doesn't support fp16
        }
        
        # Add temperature for consistency (demo mode)
        transcribe_options["temperature"] = 0.0  # Deterministic results
        
        jlog(log, logging.INFO,
             event="whisper_transcription_start",
             job_id=self.job_id,
             options=transcribe_options)
        
        # Transcribe (this is CPU-intensive but runs in current thread)
        # For production, consider running in thread pool
        result = self.whisper_model.transcribe(audio_path, **transcribe_options)
        
        return result
    
    def _process_transcript_segments(self, whisper_result: Dict[str, Any]) -> List[TranscriptSegment]:
        """Process Whisper segments into video-ready transcript segments"""
        
        segments = []
        whisper_segments = whisper_result.get("segments", [])
        
        for segment in whisper_segments:
            # Extract segment data
            start_time = segment.get("start", 0.0)
            end_time = segment.get("end", 0.0)
            text = segment.get("text", "").strip()
            
            # Calculate confidence (Whisper doesn't provide this directly)
            # Use a heuristic based on segment characteristics
            confidence = self._calculate_segment_confidence(segment, text)
            
            # Extract word-level timestamps if available
            words = segment.get("words", [])
            
            if text:  # Only include non-empty segments
                segments.append(TranscriptSegment(
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                    confidence=confidence,
                    words=words
                ))
        
        jlog(log, logging.INFO,
             event="transcript_segments_processed",
             job_id=self.job_id,
             segments_count=len(segments),
             total_duration=segments[-1].end_time if segments else 0)
        
        return segments
    
    def _calculate_segment_confidence(self, segment: Dict[str, Any], text: str) -> float:
        """Calculate confidence score for transcript segment"""
        
        # Basic heuristics for confidence (Whisper doesn't provide direct confidence)
        confidence = 0.8  # Base confidence
        
        # Adjust based on segment characteristics
        duration = segment.get("end", 0) - segment.get("start", 0)
        
        # Longer segments tend to be more reliable
        if duration > 5.0:
            confidence += 0.1
        elif duration < 1.0:
            confidence -= 0.1
            
        # Text characteristics
        word_count = len(text.split())
        if word_count >= 5:  # Reasonable length
            confidence += 0.05
        elif word_count <= 2:  # Very short might be unreliable
            confidence -= 0.1
            
        # Check for common transcription artifacts
        if any(artifact in text.lower() for artifact in ["[music]", "[inaudible]", "..."]):
            confidence -= 0.2
            
        return max(0.3, min(1.0, confidence))  # Clamp between 0.3 and 1.0
    
    async def batch_transcribe_segments(self, audio_segments: List[AudioSegment]) -> TranscriptionResult:
        """
        Transcribe multiple audio segments efficiently
        For now, transcribe the main audio file and segment the results
        """
        
        if not audio_segments:
            return TranscriptionResult(
                success=False,
                segments=[],
                full_text="",
                language="",
                duration=0,
                processing_time=0,
                model_used=self.model_name,
                error="No audio segments provided"
            )
        
        # For MVP, transcribe the main audio file
        # In production, might transcribe segments individually for better parallelization
        main_audio_path = str(self.job_dir / "extracted_audio.aac")
        
        jlog(log, logging.INFO,
             event="batch_transcription_start",
             job_id=self.job_id,
             segments_count=len(audio_segments),
             main_audio=main_audio_path)
        
        result = await self.transcribe_audio(main_audio_path)
        
        if result.success:
            # Map segments to original audio segments for better organization
            result = self._align_segments_with_audio(result, audio_segments)
        
        return result
    
    def _align_segments_with_audio(self, transcript_result: TranscriptionResult, 
                                  audio_segments: List[AudioSegment]) -> TranscriptionResult:
        """Align transcript segments with original audio segments"""
        
        # For MVP, return as-is
        # In production, could implement sophisticated alignment
        jlog(log, logging.INFO,
             event="segment_alignment_complete",
             job_id=self.job_id,
             transcript_segments=len(transcript_result.segments),
             audio_segments=len(audio_segments))
        
        return transcript_result


if __name__ == "__main__":
    # Test TranscriptionAgent
    async def test_transcription_agent():
        print("Testing TranscriptionAgent...")
        
        # Test with the extracted audio from Module 2
        test_audio = "/tmp/jobs/ced12236-0fe7-4dc1-a260-7282f4ea52f9/extracted_audio.aac"
        
        if not Path(test_audio).exists():
            print(f"Test audio not found: {test_audio}")
            return
        
        agent = TranscriptionAgent("test_transcription_job")
        result = await agent.transcribe_audio(test_audio)
        
        print(f"Transcription: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Model used: {result.model_used}")
        print(f"Language: {result.language}")
        print(f"Duration: {result.duration:.2f} seconds")
        print(f"Segments: {len(result.segments)}")
        print(f"Processing time: {result.processing_time:.2f} seconds")
        print(f"Text length: {len(result.full_text)} characters")
        
        if result.segments:
            print(f"\nFirst few segments:")
            for i, segment in enumerate(result.segments[:3]):
                print(f"  {segment.start_time:.1f}-{segment.end_time:.1f}s: {segment.text[:100]}...")
        
        if result.error:
            print(f"Error: {result.error}")
    
    import os
    asyncio.run(test_transcription_agent())