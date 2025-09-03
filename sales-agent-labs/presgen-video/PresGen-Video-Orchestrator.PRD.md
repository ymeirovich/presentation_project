# PresGen-Video-Orchestrator.PRD.md

## Context & Purpose
Orchestrate parallel video processing agents for 1-3 minute videos with <2 minute total processing time, optimized for VC demos.

## Technical Specifications
- **Architecture**: FastAPI + asyncio + MCP tools + Context7
- **Dependencies**: Existing MCP infrastructure, Context7, Playwright MCP
- **Performance**: 3 parallel phases, max 2 minutes end-to-end
- **Error Recovery**: Circuit breaker pattern, graceful degradation
- **Cost Target**: $0 for local-only demo mode

## Core Requirements

### 1. Phase 1 Parallel Execution (0-30s)
```python
class ParallelVideoOrchestrator:
    async def phase1_parallel_processing(self, video_path: str):
        """Execute independent operations in parallel for maximum speed"""
        
        phase1_tasks = [
            self.audio_agent.extract_audio(video_path),
            self.video_agent.detect_face(video_path),
            self.video_agent.get_metadata(video_path)
        ]
        
        # True parallelism with error handling
        results = await asyncio.gather(*phase1_tasks, return_exceptions=True)
        
        # Process results and handle any failures
        audio_result, face_result, metadata = self.process_phase1_results(results)
        
        return {
            "audio": audio_result,
            "face": face_result, 
            "metadata": metadata,
            "phase1_duration": time.time() - self.start_time
        }
```

**Validation**: All Phase 1 operations complete within 30 seconds, with fallback handling.

### 2. Phase 2 Sequential Processing (30-90s)
```python
async def phase2_content_processing(self, phase1_results: Dict):
    """Process content sequentially with optimized batching"""
    
    # Transcription (depends on audio)
    transcript = await self.transcription_agent.transcribe(
        phase1_results["audio"], 
        model="whisper-base"  # Optimal speed/quality for demo
    )
    
    # Batch summarization (optimized for token efficiency)
    summary = await self.content_agent.batch_summarize(
        transcript.segments,
        max_bullets=5,  # Limit for demo speed
        structured_output=True
    )
    
    # Parallel slide generation with Playwright MCP
    slides = await self.playwright_agent.generate_slides_parallel(
        summary.bullet_points,
        template="professional_minimal"
    )
    
    return {
        "transcript": transcript,
        "summary": summary,
        "slides": slides,
        "phase2_duration": time.time() - self.phase1_end_time
    }
```

**Validation**: Content processing completes within 60 seconds, produces 3-5 professional slides.

### 3. Phase 3 Final Composition (90-120s)
```python
async def phase3_final_composition(self, phase1_results: Dict, phase2_results: Dict):
    """Compose final 50/50 video with timing synchronization"""
    
    composition_config = {
        "layout": "50_50_split",
        "left_panel": phase1_results["face"]["cropped_video"],
        "right_panel": phase2_results["slides"],
        "timing": phase2_results["transcript"]["timing"],
        "transitions": "fade_between_slides",
        "output_format": "mp4_h264_aac"
    }
    
    final_video = await self.composition_agent.render_video(composition_config)
    
    # Generate download link and schedule cleanup
    download_url = await self.create_download_link(final_video)
    await self.schedule_cleanup(self.job_id, ttl_hours=24)
    
    return {
        "download_url": download_url,
        "total_duration": time.time() - self.start_time,
        "success": True
    }
```

**Validation**: Final composition completes within 30 seconds, produces downloadable MP4.

## Performance Targets
- **Total Processing Time**: <2 minutes for 1-3 minute video
- **Memory Usage**: <2GB peak memory consumption
- **CPU Utilization**: Efficient parallel processing, <90% sustained
- **Success Rate**: 95% completion rate with error recovery
- **Cost**: $0 for local-only mode, <$0.05 if cloud fallback used

## Error Recovery Architecture
```python
class CircuitBreakerOrchestrator:
    def __init__(self):
        self.circuit_breakers = {
            "audio_extraction": CircuitBreaker(failure_threshold=3),
            "face_detection": CircuitBreaker(failure_threshold=3),
            "transcription": CircuitBreaker(failure_threshold=2),
            "slide_generation": CircuitBreaker(failure_threshold=2)
        }
        
    async def execute_with_fallback(self, operation_name: str, primary_func, fallback_func):
        """Execute operation with circuit breaker and fallback"""
        
        breaker = self.circuit_breakers[operation_name]
        
        if breaker.state == "OPEN":
            # Circuit open, use fallback immediately
            return await fallback_func()
            
        try:
            result = await primary_func()
            breaker.on_success()
            return result
            
        except Exception as e:
            breaker.on_failure()
            
            if breaker.state == "OPEN":
                # Circuit just opened, try fallback
                return await fallback_func()
            else:
                raise
```

## Monitoring & Observability
```python
class VideoProcessingMonitor:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.metrics = {
            "phase_timings": {},
            "resource_usage": {},
            "error_counts": {},
            "cache_hit_rates": {}
        }
        
    async def log_phase_completion(self, phase: str, duration: float, success: bool):
        """Track processing metrics for optimization"""
        
        jlog(log, logging.INFO,
             event="phase_completed",
             job_id=self.job_id,
             phase=phase,
             duration_seconds=duration,
             success=success,
             memory_usage_mb=self.get_memory_usage(),
             cpu_usage_percent=self.get_cpu_usage())
```

## Integration with Existing Architecture
- **MCP Tools**: Extends current `src/mcp/tools/` patterns
- **FastAPI Service**: Integrates with `src/service/http.py`
- **Job Management**: Uses existing idempotency and state management
- **Caching**: Leverages current cache infrastructure
- **Logging**: Compatible with structured JSON logging

## Validation Criteria
- **Functional**: Upload → edit → download works end-to-end
- **Performance**: 95% of videos process within 2-minute target
- **Quality**: 50/50 layout accurate, slide transitions synchronized within ±0.5s
- **Reliability**: <5% failure rate during demo scenarios
- **Cost**: Zero cost for local-only demo mode

## Demo Readiness Checklist
```python
async def verify_demo_readiness(self) -> bool:
    """Pre-demo system verification"""
    
    checks = [
        await self.verify_whisper_model_loaded(),
        await self.verify_face_detection_ready(),
        await self.verify_playwright_available(),
        await self.verify_context7_responsive(),
        await self.verify_temp_storage_clean(),
        await self.verify_ffmpeg_functional()
    ]
    
    return all(checks)
```

## Success Metrics
- **Speed**: <2 minutes end-to-end processing
- **Quality**: Professional output suitable for business use
- **Reliability**: Handles common failure scenarios gracefully
- **Cost**: $0 operational cost for local demo
- **Scalability**: Architecture supports cloud scaling when needed