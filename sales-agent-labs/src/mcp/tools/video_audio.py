# src/mcp/tools/video_audio.py
"""
AudioAgent for parallel video processing with Context7 integration
"""

import asyncio
import logging
import time
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.mcp.tools.context7 import context7_client
from src.common.jsonlog import jlog

log = logging.getLogger("video_audio")


@dataclass
class AudioSegment:
    """Audio segment with timing information"""
    start_time: float
    end_time: float
    duration: float
    file_path: str


@dataclass
class AudioExtractionResult:
    """Result of audio extraction process"""
    success: bool
    audio_path: str
    segments: List[AudioSegment]
    duration: float
    sample_rate: int
    format: str
    extraction_time: float
    error: Optional[str] = None


class AudioAgent:
    """Agent for audio extraction and segmentation using Context7-optimized patterns"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.job_dir = Path(f"/tmp/jobs/{job_id}")
        self.job_dir.mkdir(parents=True, exist_ok=True)
    
    async def extract_audio(self, video_path: str) -> AudioExtractionResult:
        """
        Extract audio from video using Context7-optimized ffmpeg patterns
        
        Args:
            video_path: Path to input video file
            
        Returns:
            AudioExtractionResult with extracted audio info
        """
        start_time = time.time()
        audio_path = str(self.job_dir / "extracted_audio.aac")
        
        jlog(log, logging.INFO,
             event="audio_extraction_start",
             job_id=self.job_id,
             video_path=video_path,
             audio_path=audio_path)
        
        try:
            # Get Context7-optimized ffmpeg patterns
            context = await context7_client.get_docs("ffmpeg", "audio_extraction")
            
            # Build ffmpeg command using Context7 patterns
            command = await self._build_ffmpeg_command(video_path, audio_path, context)
            
            jlog(log, logging.INFO,
                 event="audio_extraction_command",
                 job_id=self.job_id,
                 command=" ".join(command))
            
            # Execute ffmpeg extraction
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown ffmpeg error"
                jlog(log, logging.ERROR,
                     event="audio_extraction_failed",
                     job_id=self.job_id,
                     error=error_msg,
                     return_code=process.returncode)
                
                return AudioExtractionResult(
                    success=False,
                    audio_path="",
                    segments=[],
                    duration=0,
                    sample_rate=0,
                    format="",
                    extraction_time=time.time() - start_time,
                    error=error_msg
                )
            
            # Get audio metadata
            metadata = await self._get_audio_metadata(audio_path)
            
            # Create segments for processing (30-60s as per PRD)
            segments = await self._create_audio_segments(audio_path, metadata["duration"])
            
            extraction_time = time.time() - start_time
            
            result = AudioExtractionResult(
                success=True,
                audio_path=audio_path,
                segments=segments,
                duration=metadata["duration"],
                sample_rate=metadata["sample_rate"],
                format=metadata["format"],
                extraction_time=extraction_time
            )
            
            jlog(log, logging.INFO,
                 event="audio_extraction_success",
                 job_id=self.job_id,
                 duration_secs=round(extraction_time, 2),
                 audio_duration=metadata["duration"],
                 segments_count=len(segments),
                 sample_rate=metadata["sample_rate"])
            
            return result
            
        except Exception as e:
            extraction_time = time.time() - start_time
            error_msg = f"Audio extraction failed: {str(e)}"
            
            jlog(log, logging.ERROR,
                 event="audio_extraction_exception",
                 job_id=self.job_id,
                 error=error_msg,
                 duration_secs=round(extraction_time, 2))
            
            return AudioExtractionResult(
                success=False,
                audio_path="",
                segments=[],
                duration=0,
                sample_rate=0,
                format="",
                extraction_time=extraction_time,
                error=error_msg
            )
    
    async def _build_ffmpeg_command(self, video_path: str, audio_path: str, context: Dict[str, Any]) -> List[str]:
        """Build ffmpeg command using Context7 optimization patterns"""
        
        # Use Context7 optimal command if available
        if "optimal_command" in context:
            # Parse Context7 template
            template = context["optimal_command"]
            command_parts = template.replace("{input}", video_path).replace("{output}", audio_path).split()
        else:
            # Fallback command
            command_parts = [
                "ffmpeg", "-i", video_path,
                "-vn",  # No video
                "-acodec", "aac",
                "-ab", "192k",
                audio_path
            ]
        
        # Add overwrite flag
        if "-y" not in command_parts:
            command_parts.insert(1, "-y")
        
        # Add Context7 performance optimizations if available
        if "performance_tips" in context and "hwaccel" in context["performance_tips"]:
            # Insert hardware acceleration
            command_parts.insert(1, "-hwaccel")
            command_parts.insert(2, "auto")
        
        return command_parts
    
    async def _get_audio_metadata(self, audio_path: str) -> Dict[str, Any]:
        """Get audio file metadata using ffprobe"""
        
        try:
            command = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", audio_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                import json
                metadata = json.loads(stdout.decode())
                
                # Extract relevant info
                format_info = metadata.get("format", {})
                streams = metadata.get("streams", [])
                audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
                
                return {
                    "duration": float(format_info.get("duration", 0)),
                    "sample_rate": int(audio_stream.get("sample_rate", 44100)),
                    "format": format_info.get("format_name", "aac")
                }
            else:
                # Fallback metadata
                return {
                    "duration": 60.0,  # Default estimate
                    "sample_rate": 44100,
                    "format": "aac"
                }
                
        except Exception as e:
            jlog(log, logging.WARNING,
                 event="audio_metadata_failed",
                 job_id=self.job_id,
                 error=str(e))
            
            return {
                "duration": 60.0,
                "sample_rate": 44100, 
                "format": "aac"
            }
    
    async def _create_audio_segments(self, audio_path: str, duration: float, segment_length: float = 30.0) -> List[AudioSegment]:
        """Create audio segments for processing (30-60s as per PRD)"""
        
        segments = []
        current_time = 0.0
        
        while current_time < duration:
            end_time = min(current_time + segment_length, duration)
            
            # Create segment file path
            segment_filename = f"segment_{len(segments):03d}.aac"
            segment_path = str(self.job_dir / segment_filename)
            
            segments.append(AudioSegment(
                start_time=current_time,
                end_time=end_time,
                duration=end_time - current_time,
                file_path=segment_path
            ))
            
            current_time = end_time
        
        jlog(log, logging.INFO,
             event="audio_segments_created",
             job_id=self.job_id,
             total_duration=duration,
             segments_count=len(segments),
             segment_length=segment_length)
        
        return segments
    
    async def extract_and_segment(self, video_path: str) -> AudioExtractionResult:
        """
        Main entry point for audio processing
        Combines extraction and segmentation for parallel processing
        """
        
        jlog(log, logging.INFO,
             event="audio_processing_start",
             job_id=self.job_id,
             video_path=video_path)
        
        result = await self.extract_audio(video_path)
        
        if result.success:
            jlog(log, logging.INFO,
                 event="audio_processing_complete",
                 job_id=self.job_id,
                 total_time=result.extraction_time,
                 segments_count=len(result.segments))
        else:
            jlog(log, logging.ERROR,
                 event="audio_processing_failed", 
                 job_id=self.job_id,
                 error=result.error)
        
        return result


if __name__ == "__main__":
    # Test AudioAgent
    async def test_audio_agent():
        print("Testing AudioAgent...")
        
        # Test with the uploaded video
        test_video = "/tmp/jobs/cd238746-7d7d-4041-8f3e-a5e512c9a406/raw_video.mp4"
        
        if not os.path.exists(test_video):
            print(f"Test video not found: {test_video}")
            return
        
        agent = AudioAgent("test_audio_job")
        result = await agent.extract_and_segment(test_video)
        
        print(f"Audio extraction: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Duration: {result.duration:.2f} seconds")
        print(f"Segments: {len(result.segments)}")
        print(f"Processing time: {result.extraction_time:.2f} seconds")
        
        if result.error:
            print(f"Error: {result.error}")
    
    asyncio.run(test_audio_agent())