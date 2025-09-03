# Context7-VideoTools.PRD.md

## Context & Purpose  
Create video processing tools with real-time documentation context to eliminate outdated code patterns and ensure current API usage.

## Technical Specifications
- **Base**: Existing MCP tool architecture from presgen-core
- **Enhancement**: Context7 integration for latest API patterns
- **Libraries**: ffmpeg-python, opencv-python, whisper, mediapipe, playwright
- **Performance**: Context7 calls <200ms (cached after first request)

## Core Requirements

### 1. AudioTool with Context7
```python
async def extract_audio_optimized(self, video_path: str):
    # Get latest ffmpeg patterns from Context7
    context = await self.context7.get_docs("ffmpeg", "audio_extraction")
    
    # Generate optimized ffmpeg command using current best practices
    command = await self.generate_ffmpeg_command(context, video_path)
    return await self.execute_ffmpeg(command)
```

**Validation**: Audio extraction uses current ffmpeg flags and codecs, no deprecated options.

### 2. VideoTool with Context7
```python  
async def detect_face_current(self, video_path: str):
    # Get latest OpenCV/MediaPipe patterns
    context = await self.context7.get_docs("mediapipe", "face_detection")
    
    # Use current best practices for face detection
    detector = await self.create_face_detector(context)
    return await detector.process_video(video_path)
```

**Validation**: Face detection uses latest MediaPipe models and confidence thresholds.

### 3. TranscriptionTool with Context7
```python
async def transcribe_whisper_latest(self, audio_path: str):
    # Get latest Whisper API patterns and optimizations
    context = await self.context7.get_docs("whisper", "transcription")
    
    # Use most efficient current approach
    model = await self.load_whisper_model(context.recommended_model)
    return await model.transcribe(audio_path, **context.optimal_params)
```

**Validation**: Whisper transcription uses current model versions and optimal parameters.

### 4. PlaywrightTool with Context7
```python
async def generate_slides_optimized(self, bullet_points: List[BulletPoint]):
    # Get latest Playwright rendering patterns
    context = await self.context7.get_docs("playwright", "screenshot")
    
    # Use current best practices for HTML→PNG conversion
    browser_config = await self.create_browser_config(context)
    return await self.render_slides_parallel(bullet_points, browser_config)
```

**Validation**: Slide generation uses latest Playwright APIs and optimal rendering settings.

## Performance Targets
- **Context7 calls**: <200ms (cached after first request)
- **Tool execution**: Same speed as manual implementation
- **Code accuracy**: 99% (no outdated API usage)
- **Cache hit rate**: >80% for repeated Context7 queries

## Success Criteria
- All generated code uses current API versions (verified by Context7)
- No deprecated function calls in any video processing operations
- Optimal parameter usage for speed/accuracy balance
- Real-time access to latest documentation without manual updates

## Integration Points
- **MCP Architecture**: Extends existing MCP tool patterns
- **Caching System**: Leverages current cache infrastructure  
- **Error Handling**: Uses established retry and fallback patterns
- **Logging**: Integrates with existing structured logging

## Implementation Timeline
- **Day 1**: Context7 MCP server setup and basic integration
- **Day 2**: AudioTool and VideoTool with Context7 enhancement
- **Day 3**: TranscriptionTool and PlaywrightTool integration
- **Day 4**: Testing and optimization
- **Day 5**: Documentation and final validation

## Cost Optimization
- **Caching Strategy**: 24-hour TTL for Context7 responses
- **Batch Queries**: Group related documentation requests
- **Local Fallbacks**: Default to cached/local processing if Context7 unavailable
- **Selective Usage**: Only query Context7 for complex operations

## Quality Assurance
- **API Version Verification**: Automated checks for deprecated usage
- **Performance Benchmarks**: Compare Context7-enhanced vs manual implementations
- **Error Rate Monitoring**: Track Context7 integration reliability
- **Documentation Freshness**: Verify Context7 provides current information