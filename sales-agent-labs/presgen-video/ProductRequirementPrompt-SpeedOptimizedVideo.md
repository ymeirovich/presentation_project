# Product Requirement Prompt: Speed-Optimized Video Processing

## Implementation Context
You are implementing a speed-critical video processing pipeline for VC demos. Every second counts for the demo success.

## Specific Requirements

### 1. Parallel Architecture Implementation
```python
class SpeedOptimizedVideoProcessor:
    def __init__(self):
        self.context7_client = Context7MCPClient()
        self.playwright_client = PlaywrightMCPClient()
        self.resource_pool = ResourcePool(cpu_workers=4, gpu_semaphore=1)
        self.demo_mode = True  # Optimized for speed over perfection
    
    async def process_video_fastest(self, video_path: str) -> ProcessingResult:
        """Process video with maximum speed optimization for VC demo"""
        
        # Phase 1: Maximum parallelism (target: 30 seconds)
        start_time = time.time()
        
        phase1_tasks = [
            self.audio_agent.extract_and_segment(video_path),
            self.video_agent.detect_and_crop_face(video_path),  
            self.metadata_agent.analyze(video_path)
        ]
        
        audio_result, face_result, metadata = await asyncio.gather(
            *phase1_tasks, return_exceptions=True
        )
        
        phase1_time = time.time() - start_time
        if phase1_time > 35:  # Alert if too slow for demo
            self.logger.warning(f"Phase 1 exceeded target: {phase1_time}s")
        
        # Phase 2: Optimized sequential processing (target: 60 seconds)
        phase2_start = time.time()
        
        # Use fastest Whisper model for demo
        transcript = await self.transcription_agent.transcribe_fast(
            audio_result, model="whisper-base"
        )
        
        # Batch process for token efficiency
        summary = await self.content_agent.batch_summarize(
            transcript.segments, max_bullets=5, demo_mode=True
        )
        
        # Parallel slide generation with Playwright
        slides = await self.playwright_agent.generate_slides_parallel(
            summary.bullets, template="demo_optimized"
        )
        
        phase2_time = time.time() - phase2_start
        
        # Phase 3: Final composition (target: 30 seconds)
        final_video = await self.composition_agent.render_50_50_fast(
            face_crop=face_result,
            slides=slides,
            timing=transcript.timing,
            quality="demo"  # Optimized for speed
        )
        
        total_time = time.time() - start_time
        
        return ProcessingResult(
            video_url=final_video.download_url,
            total_duration=total_time,
            phase_timings={
                "phase1": phase1_time,
                "phase2": phase2_time, 
                "phase3": time.time() - phase2_start - phase2_time
            },
            success=True
        )
```

### 2. Context7 Integration for Accuracy & Speed
```python
class Context7OptimizedAgent:
    def __init__(self):
        self.context7_cache = TTLCache(maxsize=1000, ttl=86400)  # 24-hour cache
        self.startup_preload = True
        
    async def startup_preload_patterns(self):
        """Pre-warm Context7 cache on system startup for demo speed"""
        
        preload_patterns = [
            ("ffmpeg", "audio_extraction"),
            ("ffmpeg", "video_composition"),
            ("whisper", "transcription_optimized"),
            ("opencv-python", "face_detection_fast"),
            ("playwright", "screenshot_optimization")
        ]
        
        # Preload all patterns in parallel
        tasks = [
            self.context7_client.get_docs(library, topic)
            for library, topic in preload_patterns
        ]
        
        preloaded = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Cache successful results
        for (library, topic), result in zip(preload_patterns, preloaded):
            if not isinstance(result, Exception):
                cache_key = f"{library}:{topic}"
                self.context7_cache[cache_key] = result
                
        return len([r for r in preloaded if not isinstance(r, Exception)])
    
    async def get_optimized_context(self, library: str, topic: str):
        """Get Context7 data with aggressive caching for demo performance"""
        
        cache_key = f"{library}:{topic}"
        
        # Check cache first (near-instant response)
        if cache_key in self.context7_cache:
            return self.context7_cache[cache_key]
            
        # Fallback to Context7 if not cached
        try:
            context = await asyncio.wait_for(
                self.context7_client.get_docs(library, topic),
                timeout=5.0  # Fast timeout for demo reliability
            )
            self.context7_cache[cache_key] = context
            return context
            
        except asyncio.TimeoutError:
            # Use fallback patterns for demo reliability
            return self.get_fallback_pattern(library, topic)
```

### 3. LLM Optimization Patterns for Demo Speed
```python
class DemoOptimizedLLM:
    def __init__(self):
        self.batch_size = 5  # Process multiple segments at once
        self.demo_limits = {
            "max_tokens": 300,  # Strict token limit for speed
            "max_bullets": 5,   # Limit bullet points for demo
            "response_timeout": 30  # Fast timeout
        }
        self.structured_output = True  # Use Pydantic for speed
        
    async def batch_summarize_demo(self, segments: List[TranscriptSegment]):
        """Optimize LLM calls for demo speed and cost"""
        
        # Create ultra-efficient prompt
        prompt = self.create_demo_prompt(segments)
        
        try:
            # Single LLM call for all segments
            response = await asyncio.wait_for(
                self.llm_client.generate_structured(
                    prompt=prompt,
                    response_model=DemoVideoSummary,  # Pydantic model
                    max_tokens=self.demo_limits["max_tokens"],
                    temperature=0.1  # Deterministic for caching
                ),
                timeout=self.demo_limits["response_timeout"]
            )
            
            return response
            
        except asyncio.TimeoutError:
            # Fast fallback for demo reliability
            return self.create_fallback_summary(segments)
    
    def create_demo_prompt(self, segments: List[TranscriptSegment]) -> str:
        """Ultra-compressed prompt optimized for demo speed"""
        
        # Compress segments to essential content only
        compressed_text = " ".join([
            s.text[:100] for s in segments  # Limit each segment
        ])[:1000]  # Hard limit total characters
        
        return f"""
        Extract {self.demo_limits["max_bullets"]} key points:
        
        Content: {compressed_text}
        
        Return JSON: {{"bullets": [
            {{"time": "MM:SS", "point": "concise bullet"}},
            ...
        ]}}
        
        Max 12 words per bullet. Focus on main insights only.
        """
```

### 4. Error Recovery for Demo Reliability
```python
class DemoReliabilityManager:
    def __init__(self):
        self.demo_mode = True
        self.acceptable_quality = 0.8  # Lower bar for demo speed
        self.fallback_chain = self.create_demo_fallback_chain()
        
    def create_demo_fallback_chain(self):
        """Cascading fallbacks optimized for demo success"""
        
        return {
            "transcription": [
                ("whisper_base_gpu", "fastest, good quality"),
                ("whisper_base_cpu", "fast, good quality"),
                ("whisper_tiny_cpu", "very fast, acceptable quality"),
                ("basic_speech_to_text", "fallback, basic quality")
            ],
            "face_detection": [
                ("mediapipe_fast", "fastest, good accuracy"),
                ("opencv_haar", "fast, acceptable accuracy"), 
                ("manual_crop_center", "instant, basic crop")
            ],
            "slide_generation": [
                ("playwright_optimized", "fast, professional"),
                ("playwright_basic", "fast, simple design"),
                ("text_only_slides", "instant, basic appearance")
            ]
        }
    
    async def execute_with_demo_fallbacks(self, operation: str, primary_args):
        """Execute with demo-optimized fallback chain"""
        
        fallback_methods = self.fallback_chain.get(operation, [])
        
        for method_name, description in fallback_methods:
            try:
                start_time = time.time()
                method = getattr(self, f"{operation}_{method_name}")
                result = await method(*primary_args)
                
                duration = time.time() - start_time
                
                # Log successful method for demo metrics
                self.log_demo_success(operation, method_name, duration)
                
                return result
                
            except Exception as e:
                # Continue to next fallback for demo reliability
                self.log_demo_fallback(operation, method_name, str(e))
                continue
                
        # If all methods fail, return minimal fallback for demo
        return await self.create_demo_emergency_fallback(operation, primary_args)
```

### 5. Pre-Demo System Verification
```python
class DemoReadinessChecker:
    def __init__(self):
        self.required_components = [
            "whisper_model", "face_detection", "playwright",
            "context7", "ffmpeg", "temp_storage"
        ]
        
    async def verify_demo_ready(self) -> DemoReadinessResult:
        """Comprehensive pre-demo system check"""
        
        checks = []
        
        # Parallel verification for speed
        verification_tasks = [
            self.check_whisper_loaded(),
            self.check_face_detection_ready(),
            self.check_playwright_functional(),
            self.check_context7_responsive(),
            self.check_ffmpeg_working(),
            self.check_storage_available(),
            self.check_resource_availability()
        ]
        
        results = await asyncio.gather(*verification_tasks, return_exceptions=True)
        
        # Process results
        all_ready = all(r is True for r in results if not isinstance(r, Exception))
        failed_checks = [
            self.required_components[i] 
            for i, r in enumerate(results) 
            if isinstance(r, Exception) or r is False
        ]
        
        return DemoReadinessResult(
            ready=all_ready,
            failed_components=failed_checks,
            recommendations=self.get_fix_recommendations(failed_checks),
            estimated_fix_time=self.estimate_fix_time(failed_checks)
        )
    
    async def auto_fix_demo_issues(self, failed_components: List[str]):
        """Attempt automatic fixes for common demo issues"""
        
        fix_tasks = []
        
        for component in failed_components:
            if component == "whisper_model":
                fix_tasks.append(self.download_whisper_base())
            elif component == "temp_storage":
                fix_tasks.append(self.cleanup_temp_storage())
            elif component == "context7":
                fix_tasks.append(self.restart_context7_connection())
                
        # Execute fixes in parallel
        if fix_tasks:
            await asyncio.gather(*fix_tasks, return_exceptions=True)
```

## Success Criteria for VC Demo
1. **Speed**: Complete video processing in <2 minutes consistently
2. **Reliability**: 98% success rate during demo conditions
3. **Quality**: Professional output suitable for business presentations
4. **Cost**: $0 operational cost using local processing
5. **Recovery**: Graceful fallbacks prevent demo failures

## Demo Flow Optimization
- **Pre-Demo**: Run readiness check and preload all systems
- **During Demo**: Monitor processing in real-time, show progress
- **Post-Demo**: Immediate cleanup and system reset for next demo

## Key Implementation Notes
- Prioritize speed over perfection for demo scenarios
- Use aggressive caching at every opportunity
- Implement multiple fallback paths for reliability
- Monitor performance metrics for continuous optimization
- Maintain professional output quality within speed constraints