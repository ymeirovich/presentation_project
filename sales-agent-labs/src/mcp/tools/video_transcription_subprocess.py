# src/mcp/tools/video_transcription_subprocess.py
"""
Subprocess-based TranscriptionAgent to avoid OpenMP conflicts
This is a fallback implementation that runs Whisper in a separate process
"""

import asyncio
import logging
import time
import json
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.mcp.tools.context7 import context7_client
from src.mcp.tools.video_audio import AudioSegment
from src.common.jsonlog import jlog

log = logging.getLogger("video_transcription_subprocess")


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
    """Complete transcription result from subprocess"""
    success: bool
    segments: List[TranscriptSegment]
    full_text: str
    language: str
    duration: float
    processing_time: float
    model_used: str
    error: Optional[str] = None


class SubprocessTranscriptionAgent:
    """Transcription agent using subprocess to avoid OpenMP conflicts"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.job_dir = Path(f"/tmp/jobs/{job_id}")
        self.model_name = "tiny"  # Default to fastest model
        
    async def transcribe_audio(self, audio_segments: List[AudioSegment] = None) -> TranscriptionResult:
        """
        Main transcription entry point using subprocess approach
        
        Args:
            audio_segments: Optional list of audio segments for targeted processing
            
        Returns:
            TranscriptionResult with segments, full text, and metadata
        """
        start_time = time.time()
        
        try:
            jlog(log, logging.INFO,
                 event="subprocess_transcription_start",
                 job_id=self.job_id,
                 model=self.model_name)
            
            # Get Context7 recommendations
            context = await self._get_transcription_context()
            
            # Update model based on context
            self._update_model_from_context(context)
            
            # Find audio file
            audio_file = self._find_audio_file()
            if not audio_file:
                raise FileNotFoundError("No audio file found for transcription")
            
            # Run transcription in subprocess
            result_data = await self._run_subprocess_transcription(audio_file)
            
            if not result_data['success']:
                raise Exception(result_data['error'])
            
            # Convert to our data structures
            segments = [
                TranscriptSegment(
                    start_time=seg['start_time'],
                    end_time=seg['end_time'],
                    text=seg['text'],
                    confidence=seg['confidence'],
                    words=seg.get('words', [])
                )
                for seg in result_data['segments']
            ]
            
            processing_time = time.time() - start_time
            
            transcription_result = TranscriptionResult(
                success=True,
                segments=segments,
                full_text=result_data['full_text'],
                language=result_data['language'],
                duration=result_data['duration'],
                processing_time=processing_time,
                model_used=result_data['model_used']
            )
            
            jlog(log, logging.INFO,
                 event="subprocess_transcription_complete",
                 job_id=self.job_id,
                 duration_secs=round(processing_time, 2),
                 segments_count=len(segments),
                 text_length=len(transcription_result.full_text),
                 language=transcription_result.language,
                 model=self.model_name)
            
            return transcription_result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Subprocess transcription failed: {str(e)}"
            
            jlog(log, logging.ERROR,
                 event="subprocess_transcription_exception",
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
    
    def _find_audio_file(self) -> Optional[Path]:
        """Find the audio file for transcription"""
        # Look for common audio file extensions
        for ext in ['.wav', '.mp3', '.m4a', '.aac']:
            audio_file = self.job_dir / f"audio{ext}"
            if audio_file.exists():
                return audio_file
        return None
    
    async def _get_transcription_context(self) -> Dict[str, Any]:
        """Get Context7 recommendations for transcription"""
        try:
            context_prompt = f"""
            Optimize Whisper transcription for this video processing job:
            - Job ID: {self.job_id}
            - Purpose: Extract bullet points for presentation slides
            - Priority: Accuracy over speed for content extraction
            - Language: Likely English business/technical content
            
            Recommend optimal model and parameters.
            """
            
            context = await context7_client.get_context(
                query=context_prompt,
                max_tokens=200
            )
            
            return context if context else {}
            
        except Exception as e:
            jlog(log, logging.WARNING,
                 event="context7_transcription_failed",
                 job_id=self.job_id,
                 error=str(e))
            return {}
    
    def _update_model_from_context(self, context: Dict[str, Any]):
        """Update model selection based on Context7 recommendations"""
        if "optimal_model" in context:
            recommended_model = context["optimal_model"]
            # Map to available Whisper models
            model_mapping = {
                "fastest": "tiny",
                "balanced": "base", 
                "accurate": "small",
                "premium": "medium"
            }
            self.model_name = model_mapping.get(recommended_model, "tiny")
        
        # Check performance settings
        performance_settings = context.get("performance_settings", {})
        if performance_settings.get("model"):
            self.model_name = performance_settings["model"]
    
    async def _run_subprocess_transcription(self, audio_file: Path) -> Dict[str, Any]:
        """Run transcription in subprocess to avoid OpenMP conflicts"""
        script_path = Path(__file__).parent.parent.parent / "whisper_subprocess.py"
        
        cmd = [
            "python",
            str(script_path),
            str(audio_file),
            self.model_name
        ]
        
        jlog(log, logging.INFO,
             event="subprocess_whisper_start",
             job_id=self.job_id,
             audio_file=str(audio_file),
             model=self.model_name)
        
        try:
            # Run subprocess with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300  # 5 minute timeout
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Subprocess failed"
                raise Exception(f"Subprocess failed with code {process.returncode}: {error_msg}")
            
            # Parse JSON result
            result_data = json.loads(stdout.decode('utf-8'))
            
            jlog(log, logging.INFO,
                 event="subprocess_whisper_complete",
                 job_id=self.job_id,
                 success=result_data['success'])
            
            return result_data
            
        except asyncio.TimeoutError:
            jlog(log, logging.ERROR,
                 event="subprocess_whisper_timeout",
                 job_id=self.job_id)
            raise Exception("Whisper subprocess timed out after 5 minutes")
        
        except json.JSONDecodeError as e:
            jlog(log, logging.ERROR,
                 event="subprocess_whisper_json_error",
                 job_id=self.job_id,
                 error=str(e))
            raise Exception(f"Failed to parse subprocess output: {e}")
        
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="subprocess_whisper_error",
                 job_id=self.job_id,
                 error=str(e))
            raise