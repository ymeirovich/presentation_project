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
    """Orchestrator for final 50/50 video composition with timed slide overlays"""
    
    def __init__(self, job_id: str, job_data: Optional[Dict[str, Any]] = None):
        self.job_id = job_id
        self.job_dir = Path(f"/tmp/jobs/{job_id}")
        self.output_dir = self.job_dir / "output"
        self.output_dir.mkdir(exist_ok=True)
        self._provided_job_data = job_data  # Store provided job data
        
    def compose_final_video(self) -> Dict[str, Any]:
        """
        Create final video with 50/50 layout:
        - Left side: Original cropped video
        - Right side: Timed slide overlays
        
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
            
            # 4. Create 50/50 composition using ffmpeg
            output_path = self._create_50_50_composition(
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
                "video_metadata": video_metadata
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
            
            # Load crop region from provided data or use defaults
            crop_region = {
                "x": 483,
                "y": 256, 
                "width": 379,
                "height": 379
            }
            
            # Use provided crop region if available
            if self._provided_job_data and "crop_region" in self._provided_job_data:
                crop_region = self._provided_job_data["crop_region"]
                jlog(log, logging.INFO,
                     event="crop_region_loaded_from_provided",
                     job_id=self.job_id,
                     crop_region=crop_region)
            
            return {
                "summary": summary_data,
                "crop_region": crop_region,
                "video_metadata": {"width": 1280, "height": 720, "duration": 150.0, "fps": 30}
            }
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="load_job_data_failed",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _prepare_video_assets(self, job_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Prepare and validate all required video assets"""
        try:
            raw_video = self.job_dir / "raw_video.mp4"
            slides_dir = self.job_dir / "slides"
            
            # Validate raw video exists
            if not raw_video.exists():
                jlog(log, logging.ERROR,
                     event="raw_video_missing",
                     job_id=self.job_id,
                     expected_path=str(raw_video))
                return None
            
            # Validate slides exist
            slide_files = list(slides_dir.glob("*.png")) if slides_dir.exists() else []
            if len(slide_files) < 3:
                jlog(log, logging.ERROR,
                     event="insufficient_slides",
                     job_id=self.job_id,
                     slide_count=len(slide_files),
                     slides_dir=str(slides_dir))
                return None
            
            return {
                "raw_video": str(raw_video),
                "slides_dir": str(slides_dir),
                "slide_files": [str(f) for f in sorted(slide_files)]
            }
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="prepare_assets_failed",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _generate_slide_timeline(self, job_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Generate timeline for slide overlays based on bullet points"""
        try:
            bullet_points = job_data["summary"]["bullet_points"]
            timeline = []
            
            for i, bullet in enumerate(bullet_points):
                # Convert MM:SS timestamp to seconds
                timestamp_parts = bullet["timestamp"].split(":")
                start_seconds = int(timestamp_parts[0]) * 60 + int(timestamp_parts[1])
                
                timeline.append({
                    "slide_index": i,
                    "start_time": start_seconds,
                    "duration": bullet["duration"],
                    "text": bullet["text"]
                })
            
            jlog(log, logging.INFO,
                 event="slide_timeline_generated",
                 job_id=self.job_id,
                 timeline_entries=len(timeline))
            
            return timeline
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="timeline_generation_failed",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _create_50_50_composition(self, 
                                video_assets: Dict[str, str], 
                                slide_timeline: List[Dict[str, Any]],
                                job_data: Dict[str, Any]) -> Optional[Path]:
        """Create 50/50 video composition using ffmpeg"""
        try:
            raw_video = video_assets["raw_video"]
            slide_files = video_assets["slide_files"]
            crop_region = job_data["crop_region"]
            output_path = self.output_dir / f"final_video_{self.job_id}.mp4"
            
            # Build ffmpeg command for 50/50 composition
            cmd = self._build_ffmpeg_command(raw_video, slide_files, slide_timeline, 
                                           crop_region, output_path)
            
            jlog(log, logging.INFO,
                 event="ffmpeg_command_start",
                 job_id=self.job_id,
                 command=" ".join(cmd),  # Log full command for debugging
                 input_video=raw_video,
                 slide_files=slide_files[:3],
                 crop_region=crop_region)
            
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
    
    def _build_ffmpeg_command(self, 
                            raw_video: str, 
                            slide_files: List[str],
                            slide_timeline: List[Dict[str, Any]],
                            crop_region: Dict[str, str],
                            output_path: Path) -> List[str]:
        """Build complex ffmpeg command for 50/50 composition with timed slide overlays"""
        
        # Base command with input video
        cmd = [
            "ffmpeg", "-y",  # Overwrite output
            "-i", raw_video
        ]
        
        # Add slide images as inputs
        for slide_file in slide_files:
            cmd.extend(["-i", slide_file])
        
        # Build complex filter for 50/50 layout with timed overlays
        filter_complex = self._build_filter_complex(slide_timeline, crop_region, len(slide_files))
        
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[v]",      # Map the filtered video output
            "-map", "0:a",      # Map the original audio
            "-c:v", "libx264",  # Video codec
            "-c:a", "aac",      # Audio codec
            "-preset", "medium", # Balance between quality and speed
            "-crf", "23",       # Quality setting (lower = better quality)
            "-r", "30",         # Frame rate
            str(output_path)
        ])
        
        return cmd
    
    def _build_filter_complex(self, 
                            slide_timeline: List[Dict[str, Any]], 
                            crop_region: Dict[str, str],
                            num_slides: int) -> str:
        """Build the complex filter for 50/50 video composition with timed slide transitions"""
        
        # Crop the original video to the face region
        x, y, w, h = crop_region["x"], crop_region["y"], crop_region["width"], crop_region["height"]
        
        # Create left side (cropped video)
        left_filter = f"[0:v]crop={w}:{h}:{x}:{y},scale=640:720[left]"
        
        # Create right side with timed slide transitions
        if num_slides <= 1:
            # Single slide case - simple implementation
            right_filter = f"[1:v]scale=640:720[right]"
        else:
            # Multiple slides with timing
            right_filter = self._build_slide_transitions(slide_timeline, num_slides)
        
        # Combine left and right
        filter_complex = f"{left_filter};{right_filter};[left][right]hstack=inputs=2[v]"
        
        return filter_complex
    
    def _build_slide_transitions(self, slide_timeline: List[Dict[str, Any]], num_slides: int) -> str:
        """Build slide transition filters with precise timing"""
        
        jlog(log, logging.WARNING,
             event="entering_build_slide_transitions",
             job_id=self.job_id,
             num_slides=num_slides)

        if num_slides <= 1:
            return f"[1:v]scale=640:720[right]" if num_slides == 1 else ""
        
        jlog(log, logging.INFO,
             event="slide_transition_debug",
             job_id=self.job_id,
             timeline_count=len(slide_timeline),
             num_slides=num_slides)
        
        filters = []
        for i in range(num_slides):
            filters.append(f"[{i+1}:v]scale=640:720[slide{i}]")
        
        last_stream = "slide0"
        for i in range(1, num_slides):
            start_time = slide_timeline[i]['start_time']
            output_name = 'right' if i == num_slides - 1 else f'temp{i}'
            
            jlog(log, logging.WARNING,
                 event="slide_transition_loop",
                 job_id=self.job_id,
                 iteration=i,
                 last_stream=last_stream,
                 output_name=output_name,
                 start_time=start_time)

            filters.append(f"[{last_stream}][slide{i}]overlay=0:0:enable='gte(t,{start_time})'[{output_name}]")
            last_stream = output_name

        filter_str = ";".join(filters)
        jlog(log, logging.WARNING,
             event="slide_transition_filter",
             job_id=self.job_id,
             filter_complex=filter_str)
        
        return filter_str
    
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