# src/mcp/tools/video_phase2.py
"""
Phase2Orchestrator for sequential content processing pipeline
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from src.mcp.tools.video_transcription import TranscriptionAgent, TranscriptionResult
from src.mcp.tools.video_content import ContentAgent, ContentResult
from src.mcp.tools.video_slides import PlaywrightAgent, SlidesGenerationResult
from src.mcp.tools.video_audio import AudioSegment
from src.common.jsonlog import jlog

log = logging.getLogger("video_phase2")


@dataclass
class Phase2Result:
    """Complete Phase 2 processing result"""
    success: bool
    transcription: Optional[TranscriptionResult]
    content: Optional[ContentResult]
    slides: Optional[SlidesGenerationResult]
    processing_time: float
    phase_completed: str
    error: Optional[str] = None


class Phase2Orchestrator:
    """Sequential orchestrator for content processing pipeline"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.job_dir = Path(f"/tmp/jobs/{job_id}")
        
        # Initialize agents
        self.transcription_agent = TranscriptionAgent(job_id)
        self.content_agent = ContentAgent(job_id)
        self.playwright_agent = PlaywrightAgent(job_id)
    
    async def process_content_pipeline(self, audio_segments: List[AudioSegment] = None) -> Phase2Result:
        """
        Execute Phase 2: Transcription → Summarization → Slide Generation
        
        Args:
            audio_segments: Audio segments from Phase 1 (optional, will use main audio)
            
        Returns:
            Phase2Result with complete content processing results
        """
        start_time = time.time()
        
        jlog(log, logging.INFO,
             event="phase2_start",
             job_id=self.job_id,
             has_audio_segments=bool(audio_segments),
             target_time=60)
        
        transcription_result = None
        content_result = None
        slides_result = None
        
        try:
            # Step 1: Transcription (Whisper)
            jlog(log, logging.INFO,
                 event="phase2_step1_transcription_start",
                 job_id=self.job_id)
            
            if audio_segments:
                transcription_result = await self.transcription_agent.batch_transcribe_segments(audio_segments)
            else:
                # Use main audio file
                main_audio = str(self.job_dir / "extracted_audio.aac")
                transcription_result = await self.transcription_agent.transcribe_audio(main_audio)
            
            if not transcription_result.success:
                raise Exception(f"Transcription failed: {transcription_result.error}")
            
            jlog(log, logging.INFO,
                 event="phase2_step1_transcription_complete",
                 job_id=self.job_id,
                 segments_count=len(transcription_result.segments),
                 duration=round(transcription_result.processing_time, 2))
            
            # Step 2: Content Summarization (LLM)
            jlog(log, logging.INFO,
                 event="phase2_step2_content_start",
                 job_id=self.job_id)
            
            content_result = await self.content_agent.batch_summarize(
                transcription_result.segments, max_bullets=5
            )
            
            if not content_result.success:
                raise Exception(f"Content summarization failed: {content_result.error}")
            
            jlog(log, logging.INFO,
                 event="phase2_step2_content_complete",
                 job_id=self.job_id,
                 bullets_generated=len(content_result.summary.bullet_points),
                 duration=round(content_result.processing_time, 2))
            
            # Step 3: Slide Generation (Playwright)
            jlog(log, logging.INFO,
                 event="phase2_step3_slides_start",
                 job_id=self.job_id)
            
            slides_result = await self.playwright_agent.generate_slides(content_result.summary)
            
            if not slides_result.success:
                raise Exception(f"Slides generation failed: {slides_result.error}")
            
            jlog(log, logging.INFO,
                 event="phase2_step3_slides_complete",
                 job_id=self.job_id,
                 slides_generated=slides_result.slides_generated,
                 duration=round(slides_result.processing_time, 2))
            
            # Calculate total processing time
            processing_time = time.time() - start_time
            
            result = Phase2Result(
                success=True,
                transcription=transcription_result,
                content=content_result,
                slides=slides_result,
                processing_time=processing_time,
                phase_completed="phase2_complete"
            )
            
            jlog(log, logging.INFO,
                 event="phase2_success",
                 job_id=self.job_id,
                 total_processing_time=round(processing_time, 2),
                 target_met=processing_time < 60,
                 transcription_time=round(transcription_result.processing_time, 2),
                 content_time=round(content_result.processing_time, 2),
                 slides_time=round(slides_result.processing_time, 2),
                 final_slides=slides_result.slides_generated)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Phase 2 pipeline failed: {str(e)}"
            
            jlog(log, logging.ERROR,
                 event="phase2_exception",
                 job_id=self.job_id,
                 error=error_msg,
                 processing_time=round(processing_time, 2),
                 failed_at=self._determine_failure_point(transcription_result, content_result, slides_result))
            
            return Phase2Result(
                success=False,
                transcription=transcription_result,
                content=content_result,
                slides=slides_result,
                processing_time=processing_time,
                phase_completed="phase2_failed",
                error=error_msg
            )
    
    def _determine_failure_point(self, transcription: Optional[TranscriptionResult],
                               content: Optional[ContentResult],
                               slides: Optional[SlidesGenerationResult]) -> str:
        """Determine where the pipeline failed for better error reporting"""
        
        if transcription is None or not transcription.success:
            return "transcription"
        elif content is None or not content.success:
            return "content_summarization"
        elif slides is None or not slides.success:
            return "slide_generation"
        else:
            return "unknown"
    
    async def get_processing_status(self) -> Dict[str, Any]:
        """Get current processing status for monitoring"""
        
        # Check for intermediate files to determine progress
        audio_file = self.job_dir / "extracted_audio.aac"
        slides_dir = self.job_dir / "slides"
        
        status = {
            "job_id": self.job_id,
            "phase": "phase2",
            "audio_available": audio_file.exists(),
            "slides_directory": slides_dir.exists(),
        }
        
        if slides_dir.exists():
            slide_files = list(slides_dir.glob("*.png"))
            status["slides_generated"] = len(slide_files)
            status["slide_files"] = [f.name for f in slide_files]
        else:
            status["slides_generated"] = 0
            status["slide_files"] = []
        
        return status


if __name__ == "__main__":
    # Test Phase2Orchestrator
    async def test_phase2_orchestrator():
        print("Testing Phase2Orchestrator...")
        
        # Use existing job from Module 2 if available
        test_job_id = "ced12236-0fe7-4dc1-a260-7282f4ea52f9"
        test_job_dir = Path(f"/tmp/jobs/{test_job_id}")
        test_job_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if we have audio from previous tests
        audio_file = test_job_dir / "extracted_audio.aac"
        if not audio_file.exists():
            print(f"No audio file found at {audio_file}")
            print("Run Module 2 first to generate audio file")
            return
        
        orchestrator = Phase2Orchestrator(test_job_id)
        
        # Test status check first
        status = await orchestrator.get_processing_status()
        print(f"Initial status: {status}")
        
        # Run Phase 2 pipeline
        result = await orchestrator.process_content_pipeline()
        
        print(f"Phase 2 processing: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Total processing time: {result.processing_time:.2f} seconds")
        print(f"Target met (<60s): {result.processing_time < 60}")
        print(f"Phase completed: {result.phase_completed}")
        
        if result.transcription:
            print(f"\nTranscription: {'SUCCESS' if result.transcription.success else 'FAILED'}")
            print(f"  Segments: {len(result.transcription.segments)}")
            print(f"  Duration: {result.transcription.duration:.2f}s")
            print(f"  Language: {result.transcription.language}")
            print(f"  Processing time: {result.transcription.processing_time:.2f}s")
        
        if result.content:
            print(f"\nContent summarization: {'SUCCESS' if result.content.success else 'FAILED'}")
            if result.content.summary:
                print(f"  Bullets: {len(result.content.summary.bullet_points)}")
                print(f"  Themes: {result.content.summary.main_themes}")
                print(f"  Confidence: {result.content.summary.summary_confidence:.2f}")
            print(f"  Processing time: {result.content.processing_time:.2f}s")
        
        if result.slides:
            print(f"\nSlides generation: {'SUCCESS' if result.slides.success else 'FAILED'}")
            print(f"  Slides generated: {result.slides.slides_generated}")
            print(f"  Processing time: {result.slides.processing_time:.2f}s")
            
            if result.slides.slides:
                print("  Generated files:")
                for slide in result.slides.slides:
                    if slide.success:
                        print(f"    [{slide.timestamp}] {Path(slide.slide_path).name}")
        
        if result.error:
            print(f"Error: {result.error}")
        
        # Final status check
        final_status = await orchestrator.get_processing_status()
        print(f"\nFinal status: {final_status}")
    
    asyncio.run(test_phase2_orchestrator())