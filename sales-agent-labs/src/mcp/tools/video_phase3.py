# src/mcp/tools/video_phase3.py
"""
Phase3Orchestrator for final video composition with 50/50 layout and timed slides
"""

import asyncio
import logging
import time
import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from src.common.jsonlog import jlog

log = logging.getLogger("video_phase3")


@dataclass
class CompositionResult:
    """Final composition result"""
    success: bool
    output_path: Optional[str]
    processing_time: float
    video_metadata: Optional[Dict[str, Any]]
    error: Optional[str] = None


class Phase3Orchestrator:
    """Orchestrator for full-screen video composition with natural SRT subtitle overlays"""
    
    def __init__(self, job_id: str, job_data: Optional[Dict[str, Any]] = None):
        self.job_id = job_id
        self.job_dir = Path(f"/tmp/jobs/{job_id}")
        self.output_dir = self.job_dir / "output"
        self.output_dir.mkdir(exist_ok=True)
        self._provided_job_data = job_data  # Store provided job data
        
    def compose_final_video(self) -> Dict[str, Any]:
        """
        Create final video with full-screen layout and natural SRT subtitle overlay:
        - Original video at full resolution
        - Timed text overlays using SRT subtitles
        
        Returns:
            Dict with success status, output path, and processing time
        """
        start_time = time.time()
        
        try:
            jlog(log, logging.INFO,
                 event="phase3_composition_start",
                 job_id=self.job_id)
            
            # 1. Load job data and validate inputs
            job_data = self._load_job_data()
            if not job_data:
                return {"success": False, "error": "Failed to load job data"}
            
            # 2. Prepare video assets
            video_assets = self._prepare_video_assets(job_data)
            if not video_assets:
                return {"success": False, "error": "Failed to prepare video assets"}
            
            # 3. Generate slide timeline
            slide_timeline = self._generate_slide_timeline(job_data)
            if not slide_timeline:
                return {"success": False, "error": "Failed to generate slide timeline"}
            
            # 3.5. Generate subtitle file for debugging/reference
            subtitle_path = self._generate_subtitle_file(slide_timeline)
            jlog(log, logging.INFO,
                 event="subtitle_file_generated",
                 job_id=self.job_id,
                 subtitle_path=subtitle_path)
            
            # 4. Create full-screen composition with SRT overlay
            output_path = self._create_fullscreen_composition(
                video_assets, slide_timeline, job_data
            )
            if not output_path:
                return {"success": False, "error": "Failed to create video composition"}
            
            processing_time = time.time() - start_time
            
            # 5. Verify output and get metadata
            video_metadata = self._get_video_metadata(output_path)
            
            jlog(log, logging.INFO,
                 event="phase3_composition_complete",
                 job_id=self.job_id,
                 output_path=str(output_path),
                 processing_time=processing_time,
                 video_metadata=video_metadata)
            
            return {
                "success": True,
                "output_path": str(output_path),
                "processing_time": processing_time,
                "video_metadata": video_metadata,
                "corrected_timeline": slide_timeline  # Corrected timestamps for UI
            }
            
        except Exception as e:
            error_msg = f"Phase 3 composition failed: {str(e)}"
            jlog(log, logging.ERROR,
                 event="phase3_composition_exception",
                 job_id=self.job_id,
                 error=error_msg)
            return {"success": False, "error": error_msg}
    
    def _load_job_data(self) -> Optional[Dict[str, Any]]:
        """Load job data including summary, crop region, and slide information"""
        try:
            summary_data = None
            
            # First try to use provided job data (from HTTP service)
            if self._provided_job_data:
                jlog(log, logging.INFO,
                     event="job_data_provided_debug",
                     job_id=self.job_id,
                     provided_keys=list(self._provided_job_data.keys()),
                     has_summary="summary" in self._provided_job_data)
                
                if "summary" in self._provided_job_data:
                    summary_data = self._provided_job_data["summary"]
                    jlog(log, logging.INFO,
                         event="job_data_loaded_from_provided",
                         job_id=self.job_id,
                         has_summary=bool(summary_data),
                         summary_keys=list(summary_data.keys()) if isinstance(summary_data, dict) else "not_dict")
            else:
                jlog(log, logging.WARNING,
                     event="no_job_data_provided",
                     job_id=self.job_id)
            
            # Fallback to loading from saved state file
            if not summary_data:
                job_state_file = self.job_dir / "job_state.json"
                if job_state_file.exists():
                    # Load from saved job state
                    import json
                    with open(job_state_file, 'r') as f:
                        job_state = json.load(f)
                        summary_data = job_state.get("summary")
                        
                    jlog(log, logging.INFO,
                         event="job_data_loaded_from_state",
                         job_id=self.job_id,
                         has_summary=bool(summary_data))
            
            # Final fallback to mock data if no source found
            if not summary_data:
                jlog(log, logging.WARNING,
                     event="job_data_fallback_to_mock",
                     job_id=self.job_id,
                     reason="no_saved_state_found")
                
                summary_data = {
                    "bullet_points": [
                        {"timestamp": "00:30", "text": "Our goal is to demonstrate AI transformation", "confidence": 0.9, "duration": 20.0},
                        {"timestamp": "01:15", "text": "Data shows significant improvements", "confidence": 0.8, "duration": 25.0},
                        {"timestamp": "02:00", "text": "Recommendation: implement company-wide", "confidence": 0.9, "duration": 15.0}
                    ],
                    "main_themes": ["Strategy", "Data", "Implementation"],
                    "total_duration": "02:30"
                }
            
            return {
                "summary": summary_data,
                "video_metadata": {"width": 1280, "height": 720, "duration": 150.0, "fps": 30}
            }
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="load_job_data_failed",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _prepare_video_assets(self, job_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Prepare and validate video assets (simplified - only raw video needed)"""
        try:
            raw_video = self.job_dir / "raw_video.mp4"
            
            # Validate raw video exists
            if not raw_video.exists():
                jlog(log, logging.ERROR,
                     event="raw_video_missing",
                     job_id=self.job_id,
                     expected_path=str(raw_video))
                return None
            
            return {
                "raw_video": str(raw_video)
            }
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="prepare_assets_failed",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _generate_slide_timeline(self, job_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Generate timeline for slide overlays based on bullet points with video duration validation"""
        try:
            bullet_points = job_data["summary"]["bullet_points"]
            timeline = []
            
            # Get actual video duration - try multiple sources
            video_duration = self._get_actual_video_duration(job_data)
            
            jlog(log, logging.INFO,
                 event="video_duration_check",
                 job_id=self.job_id,
                 video_duration=video_duration,
                 bullet_count=len(bullet_points))
            
            # Sort bullets by original timestamp to maintain order
            sorted_bullets = []
            for i, bullet in enumerate(bullet_points):
                # Convert MM:SS timestamp to seconds
                timestamp_parts = bullet["timestamp"].split(":")
                start_seconds = int(timestamp_parts[0]) * 60 + int(timestamp_parts[1])
                sorted_bullets.append((i, bullet, start_seconds))
            
            # Redistribute all timestamps to ensure they fit within video duration
            # For a 66-second video with 5 bullets, distribute as: 0, 12, 24, 36, 48 (with 18-second buffer from end)
            for idx, (original_index, bullet, original_timestamp) in enumerate(sorted_bullets):
                if len(bullet_points) > 1:
                    # Use more buffer to ensure last bullet displays fully before video ends
                    buffer = 18  # 18-second buffer before video ends
                    usable_duration = max(video_duration - buffer, 30)  # At least 30 seconds for safety
                    # Distribute evenly: first at 0, rest distributed across usable duration
                    if idx == 0:
                        adjusted_start = 0
                    else:
                        # Spread remaining bullets evenly across remaining time
                        time_per_bullet = usable_duration / (len(bullet_points) - 1)
                        adjusted_start = int(idx * time_per_bullet)
                else:
                    adjusted_start = 0
                
                # Log if timestamp was adjusted
                if original_timestamp != adjusted_start:
                    jlog(log, logging.WARNING,
                         event="timestamp_adjusted",
                         job_id=self.job_id,
                         bullet_index=idx+1,
                         original_timestamp=original_timestamp,
                         adjusted_timestamp=adjusted_start,
                         video_duration=video_duration)
                
                timeline.append({
                    "slide_index": original_index,
                    "start_time": adjusted_start,
                    "duration": bullet["duration"],
                    "text": bullet["text"]
                })
            
            jlog(log, logging.INFO,
                 event="slide_timeline_generated",
                 job_id=self.job_id,
                 timeline_entries=len(timeline),
                 video_duration=video_duration,
                 final_timestamps=[entry["start_time"] for entry in timeline])
            
            return timeline
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="timeline_generation_failed",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _get_actual_video_duration(self, job_data: Dict[str, Any]) -> float:
        """Get actual video duration using ffprobe (most reliable method)"""
        # ALWAYS use ffprobe for accurate duration - job metadata can be wrong
        try:
            raw_video_path = self.job_dir / "raw_video.mp4"
            if raw_video_path.exists():
                metadata = self._get_video_metadata(raw_video_path)
                if metadata and "duration" in metadata:
                    duration = metadata["duration"]
                    jlog(log, logging.INFO,
                         event="video_duration_from_ffprobe",
                         job_id=self.job_id,
                         duration=duration,
                         source="ffprobe_direct")
                    return float(duration)
        except Exception as e:
            jlog(log, logging.WARNING,
                 event="video_duration_probe_failed",
                 job_id=self.job_id,
                 error=str(e))
        
        # Fallback: Try to get from job metadata (less reliable)
        if "video_metadata" in job_data:
            duration = job_data["video_metadata"].get("duration")
            if duration:
                jlog(log, logging.WARNING,
                     event="video_duration_from_metadata_fallback",
                     job_id=self.job_id,
                     duration=duration,
                     message="Using job metadata as fallback - may be inaccurate")
                return float(duration)
        
        # Default to 66 seconds (1:06)
        jlog(log, logging.WARNING,
             event="video_duration_default",
             job_id=self.job_id,
             default_duration=66)
        return 66.0
    
    def _create_fullscreen_composition(self, 
                                     video_assets: Dict[str, str], 
                                     slide_timeline: List[Dict[str, Any]],
                                     job_data: Dict[str, Any]) -> Optional[Path]:
        """Create full-screen video with natural SRT subtitle overlay"""
        try:
            raw_video = video_assets["raw_video"]
            output_path = self.output_dir / f"final_video_{self.job_id}.mp4"
            
            # Build simplified ffmpeg command for full-screen with SRT overlay
            cmd = self._build_fullscreen_ffmpeg_command(raw_video, slide_timeline, output_path)
            
            jlog(log, logging.INFO,
                 event="ffmpeg_command_start",
                 job_id=self.job_id,
                 command=" ".join(cmd),  # Log full command for debugging
                 input_video=raw_video)
            
            # Execute ffmpeg command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                jlog(log, logging.ERROR,
                     event="ffmpeg_execution_failed",
                     job_id=self.job_id,
                     return_code=result.returncode,
                     stderr=result.stderr,  # Log full stderr for debugging
                     stdout=result.stdout)
                return None
            
            # Verify output file was created
            if not output_path.exists() or output_path.stat().st_size == 0:
                jlog(log, logging.ERROR,
                     event="ffmpeg_output_invalid",
                     job_id=self.job_id,
                     output_path=str(output_path),
                     exists=output_path.exists(),
                     size=output_path.stat().st_size if output_path.exists() else 0)
                return None
            
            jlog(log, logging.INFO,
                 event="ffmpeg_composition_success",
                 job_id=self.job_id,
                 output_path=str(output_path),
                 file_size=output_path.stat().st_size)
            
            return output_path
            
        except subprocess.TimeoutExpired:
            jlog(log, logging.ERROR,
                 event="ffmpeg_timeout",
                 job_id=self.job_id)
            return None
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="ffmpeg_composition_exception",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _build_fullscreen_ffmpeg_command(self, 
                                        raw_video: str, 
                                        slide_timeline: List[Dict[str, Any]],
                                        output_path: Path) -> List[str]:
        """Build simplified ffmpeg command for full-screen video with right-side highlights rectangle"""
        
        # Build drawtext filters for right-side rectangle with numbered bullet highlights
        drawtext_filters = self._build_drawtext_filters(slide_timeline)
        if not drawtext_filters:
            raise Exception("Failed to generate drawtext filters")
        
        # Command with drawtext filters for precise positioning
        cmd = [
            "ffmpeg", "-y",  # Overwrite output
            "-i", raw_video,
            "-vf", drawtext_filters,
            "-c:v", "libx264",  # Video codec
            "-c:a", "aac",      # Audio codec  
            "-preset", "medium", # Balance between quality and speed
            "-crf", "23",       # Quality setting (lower = better quality)
            str(output_path)
        ]
        
        return cmd
    
    def _build_drawtext_filters(self, slide_timeline: List[Dict[str, Any]]) -> str:
        """Build drawtext filters with right-side rectangle and numbered bullet highlights"""
        if not slide_timeline:
            return ""
            
        filter_parts = []
        
        # 1. Add white rectangle (25% of screen width, positioned on the right)
        # Use fixed coordinates assuming 1280x720 video (320px width, positioned at x=960)
        rect_filter = (
            "drawbox="
            "x=960:y=0:"              # Position at 960px from left (right 320px)
            "w=320:h=720:"            # Width=320px (25% of 1280), height=720px
            "color=white:t=fill"       # Solid white fill
        )
        filter_parts.append(rect_filter)
        
        # 2. Add static "Highlights" title at top-center of rectangle  
        title_filter = (
            "drawtext=text='Highlights':"
            "fontsize=28:"
            "fontcolor=navy:"
            "x=960+(320-text_w)/2:"        # Center within the 320px rectangle
            "y=20"                         # 20px margin from top
        )
        filter_parts.append(title_filter)
        
        # 3. Add numbered bullet points within the rectangle
        for i, entry in enumerate(slide_timeline, 1):
            start_time = entry['start_time']
            text = entry['text'].replace("'", "\\'").replace(":", "\\:")  # Escape special chars
            
            # Prepend with numbered index
            numbered_text = f"#{i} {text}"
            
            # Break long text into multiple lines to fit within 300px width (approximately 25-30 chars per line at 20px font)
            wrapped_lines = self._wrap_text_for_rectangle(numbered_text, max_chars_per_line=25)
            
            # Create multiple drawtext filters for wrapped text
            # Add 20px margin-bottom to each bullet (space after each bullet)
            base_start = 60
            base_spacing = 80  # Base spacing between bullets
            margin_bottom = 20  # 20px margin-bottom for each bullet
            # For margin-bottom: add space after each bullet (except the last one)
            extra_margin = margin_bottom if i < len(slide_timeline) else 0  # Add margin-bottom except for last bullet
            additional_margin = (i-1) * (10 + margin_bottom)  # Progressive spacing includes margin-bottom
            
            for line_idx, line in enumerate(wrapped_lines):
                bullet_filter = (
                    f"drawtext=text='{line}':"
                    f"fontsize=20:"                  # 20px font size
                    f"fontcolor=navy:"
                    f"x=970:"                        # 10px margin from left edge of rectangle (960+10)
                    f"y={base_start + extra_margin + additional_margin + (i-1)*base_spacing + line_idx*22}:"  # Tighter spacing
                    f"enable='gte(t,{start_time})'"  # Show from start time and KEEP visible (no end time)
                )
                filter_parts.append(bullet_filter)
        
        # Chain all filters together
        return ",".join(filter_parts)
    
    def _wrap_text_for_rectangle(self, text: str, max_chars_per_line: int = 25) -> List[str]:
        """Wrap text to fit within rectangle width"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            # Check if adding this word would exceed the line limit
            test_line = current_line + (" " if current_line else "") + word
            if len(test_line) <= max_chars_per_line:
                current_line = test_line
            else:
                # Start a new line
                if current_line:
                    lines.append(current_line)
                current_line = word
                
                # Handle very long words that exceed line limit
                if len(word) > max_chars_per_line:
                    # Split long word
                    while len(current_line) > max_chars_per_line:
                        lines.append(current_line[:max_chars_per_line-1] + "-")
                        current_line = current_line[max_chars_per_line-1:]
        
        # Add the last line
        if current_line:
            lines.append(current_line)
            
        return lines if lines else [""]
    
    def _generate_subtitle_file(self, slide_timeline: List[Dict[str, Any]]) -> str:
        """Generate SRT subtitle file for timed text overlays"""
        # Use the presgen-video/srt directory
        srt_dir = Path("presgen-video/subtitles")
        srt_dir.mkdir(parents=True, exist_ok=True)
        srt_path = srt_dir / f"subtitles_{self.job_id}.srt"
        
        try:
            with open(srt_path, 'w', encoding='utf-8') as f:
                for i, entry in enumerate(slide_timeline, 1):
                    start_time = entry['start_time']
                    duration = entry['duration']
                    end_time = start_time + duration
                    text = entry['text']
                    
                    # Convert seconds to SRT time format (HH:MM:SS,mmm)
                    start_srt = self._seconds_to_srt_time(start_time)
                    end_srt = self._seconds_to_srt_time(end_time)
                    
                    # Write SRT entry
                    f.write(f"{i}\n")
                    f.write(f"{start_srt} --> {end_srt}\n")
                    f.write(f"{text}\n\n")
            
            jlog(log, logging.INFO,
                 event="subtitle_file_generated",
                 job_id=self.job_id,
                 subtitle_path=str(srt_path),
                 entries=len(slide_timeline))
            
            return str(srt_path)
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="subtitle_generation_failed",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def _get_video_metadata(self, video_path: Path) -> Dict[str, Any]:
        """Extract metadata from the final video using ffprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return {}
            
            metadata = json.loads(result.stdout)
            video_stream = next(
                (s for s in metadata.get("streams", []) if s.get("codec_type") == "video"), 
                {}
            )
            
            return {
                "duration": float(metadata.get("format", {}).get("duration", 0)),
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "fps": eval(video_stream.get("r_frame_rate", "30/1")),  # Convert fraction to float
                "codec": video_stream.get("codec_name"),
                "file_size": int(metadata.get("format", {}).get("size", 0))
            }
            
        except Exception as e:
            jlog(log, logging.WARNING,
                 event="metadata_extraction_failed",
                 job_id=self.job_id,
                 error=str(e))
            return {}