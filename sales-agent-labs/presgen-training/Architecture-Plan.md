# PresGen-Training: Technical Architecture Plan

## System Overview

**PresGen-Training** extends the existing PresGen ecosystem with avatar video generation capabilities, creating a seamless pipeline from text scripts to professional presentation videos with AI-generated avatars and automatic content overlays.

## Architecture Principles

### 1. Local-First Processing
- **Zero Cloud Costs**: All processing on local MacBook hardware
- **Privacy Control**: No data leaves local environment
- **Speed Optimization**: Eliminate network latency and API limits
- **Resource Adaptive**: Gracefully scale quality based on hardware capabilities

### 2. Pipeline Integration
- **Seamless Handoff**: Avatar generation → PresGen-Video processing
- **Shared Infrastructure**: Leverage existing logging, error handling, job management
- **Consistent UX**: Similar interface patterns and status reporting
- **File System Integration**: Organized within existing `/tmp/jobs/` structure

### 3. Rapid Prototyping Focus
- **Speed over Perfection**: Demo-quality output optimized for VC presentation
- **Simple Setup**: Minimal dependencies and configuration
- **Robust Fallbacks**: Multiple quality levels and processing options
- **Quick Iteration**: Fast feedback loops for script testing and refinement

## System Architecture

### High-Level Data Flow
```
Text Script → TTS Audio → Avatar Video → PresGen-Video → Final Presentation
     ↓            ↓           ↓              ↓              ↓
   Parsing    Audio Gen   Face Synthesis  Content Analysis  Professional
   Validation  (gTTS)     (SadTalker)    Bullet Extraction    Output
```

### Component Architecture

#### 1. Input Processing Layer
```python
# Script Processing Pipeline
class ScriptProcessor:
    """Handles text script validation, optimization, and TTS generation"""
    
    def validate_script(self, script: str) -> ScriptValidation:
        # Word count, readability, timing estimation
    
    def optimize_for_speech(self, script: str) -> str:
        # Add natural pauses, pronunciation hints
        
    def generate_audio(self, script: str) -> AudioResult:
        # TTS generation with timing metadata
```

#### 2. Avatar Generation Layer
```python
# Avatar Video Generation
class AvatarGenerator:
    """Manages SadTalker/Wav2Lip processing with resource monitoring"""
    
    def __init__(self, hardware_profile: HardwareProfile):
        self.processor = self._select_processor(hardware_profile)
        self.monitor = ResourceMonitor()
    
    def generate_avatar_video(self, 
                            audio_path: str, 
                            source_image: str) -> AvatarResult:
        # Primary: SadTalker, Fallback: Wav2Lip
```

#### 3. Integration Layer
```python
# PresGen-Video Pipeline Integration
class TrainingVideoOrchestrator:
    """Orchestrates complete pipeline from script to final video"""
    
    def process_training_video(self, 
                              script: str, 
                              source_video: str) -> TrainingResult:
        
        # Phase 1: Avatar Generation (5-8 minutes)
        avatar_video = self.generate_avatar(script, source_video)
        
        # Phase 2: PresGen-Video Processing (2-3 minutes)
        final_video = self.apply_content_overlays(avatar_video, script)
        
        return TrainingResult(success=True, final_path=final_video)
```

### Resource Management Architecture

#### 1. Hardware Profiling System
```python
class HardwareProfiler:
    """Detects and profiles local hardware capabilities"""
    
    def detect_hardware(self) -> HardwareProfile:
        return HardwareProfile(
            cpu_type="apple_silicon",  # or "intel"
            ram_gb=16,
            gpu_available=True,
            recommended_quality="standard"
        )
    
    def recommend_settings(self, profile: HardwareProfile) -> ProcessingSettings:
        # Optimize quality vs. speed based on hardware
```

#### 2. Resource Monitoring System
```python
class ResourceMonitor:
    """Real-time monitoring and automatic quality adjustment"""
    
    def start_monitoring(self):
        # Track CPU, memory, temperature
        
    def check_resources(self) -> ResourceStatus:
        # Return current usage and recommendations
        
    def auto_adjust_quality(self, current_settings: ProcessingSettings):
        # Dynamically reduce quality if resources constrained
```

### File System Architecture

#### Directory Structure
```
presgen-training/
├── src/
│   ├── processors/
│   │   ├── script_processor.py      # Text validation and TTS
│   │   ├── avatar_generator.py      # SadTalker/Wav2Lip integration
│   │   ├── source_extractor.py     # Frame extraction from videos
│   │   └── integration_manager.py  # PresGen-Video handoff
│   ├── monitoring/
│   │   ├── hardware_profiler.py    # Hardware detection and profiling
│   │   ├── resource_monitor.py     # Real-time resource monitoring
│   │   └── quality_controller.py   # Automatic quality adjustment
│   ├── models/
│   │   ├── sadtalker/              # SadTalker model files
│   │   ├── wav2lip/                # Wav2Lip model files
│   │   └── enhancers/              # Optional quality enhancement models
│   └── api/
│       ├── training_api.py         # FastAPI endpoints
│       └── integration_api.py      # PresGen-Video integration
├── jobs/                           # Per-job processing directories
│   └── {job_id}/
│       ├── input/
│       │   ├── script.txt          # Original text script
│       │   └── source_frame.jpg    # Extracted user frame
│       ├── processing/
│       │   ├── audio.wav           # Generated TTS audio
│       │   ├── avatar_video.mp4    # Raw avatar video
│       │   └── processing.log      # Detailed processing logs
│       └── output/
│           └── final_video.mp4     # Complete presentation video
├── config/
│   ├── hardware_profiles.yaml     # Hardware-specific settings
│   ├── quality_presets.yaml       # Quality/speed trade-off presets
│   └── integration_config.yaml    # PresGen-Video integration settings
└── docs/
    ├── setup_guide.md             # Hardware setup and model installation
    ├── troubleshooting.md          # Common issues and solutions
    └── api_reference.md            # API documentation
```

## Implementation Architecture

### Phase 1: Foundation Setup (Day 1)

#### 1.1 Environment Setup
```bash
# Hardware Detection and Validation
python3 setup/detect_hardware.py
# Output: Hardware profile and recommended settings

# Model Installation
python3 setup/install_models.py --profile apple_silicon_16gb
# Downloads and configures SadTalker/Wav2Lip based on hardware

# Resource Monitoring Setup
python3 setup/configure_monitoring.py
# Configures resource thresholds and fallback triggers
```

#### 1.2 Core Components
```python
# Script to TTS Pipeline
class TTSGenerator:
    def __init__(self, voice_quality: str = "standard"):
        self.tts_engine = gTTS(lang='en', slow=False)
        
    def script_to_audio(self, script: str, output_path: str):
        # Process script with natural pauses
        processed_script = self._add_natural_pauses(script)
        self.tts_engine.text = processed_script
        self.tts_engine.save(output_path)
        
        # Convert to WAV for better compatibility
        self._convert_to_wav(output_path)

# Source Frame Extraction
class SourceExtractor:
    def extract_best_frames(self, video_path: str, count: int = 5):
        # Use face detection to find best frames
        # Select well-lit, front-facing, high-quality frames
        pass
```

### Phase 2: Avatar Generation (Day 1-2)

#### 2.1 SadTalker Integration
```python
class SadTalkerProcessor:
    def __init__(self, hardware_profile: HardwareProfile):
        self.config = self._load_optimized_config(hardware_profile)
        self.quality_level = hardware_profile.recommended_quality
        
    def generate_video(self, audio_path: str, source_image: str):
        """Generate avatar video using SadTalker"""
        
        cmd = [
            "python", "sadtalker/inference.py",
            "--driven_audio", audio_path,
            "--source_image", source_image,
            "--result_dir", self.output_dir,
            "--still" if self.quality_level == "fast" else "",
            "--enhancer", "gfpgan" if self.quality_level == "high" else "",
        ]
        
        # Run with resource monitoring
        with ResourceMonitor() as monitor:
            result = subprocess.run(cmd, ...)
            
        return result
```

#### 2.2 Fallback System
```python
class AvatarGeneratorOrchestrator:
    def __init__(self):
        self.primary = SadTalkerProcessor()
        self.fallback = Wav2LipProcessor()
        
    def generate_avatar(self, audio_path: str, source_image: str):
        """Generate avatar with automatic fallback"""
        
        try:
            # Try SadTalker first
            result = self.primary.generate_video(audio_path, source_image)
            if result.success:
                return result
        except Exception as e:
            log.warning(f"SadTalker failed: {e}")
            
        # Fallback to Wav2Lip
        try:
            result = self.fallback.generate_video(audio_path, source_image)
            return result
        except Exception as e:
            log.error(f"All avatar generators failed: {e}")
            raise AvatarGenerationError("Unable to generate avatar video")
```

### Phase 3: PresGen-Video Integration (Day 2)

#### 3.1 Pipeline Integration
```python
class TrainingVideoOrchestrator:
    def __init__(self):
        self.avatar_generator = AvatarGeneratorOrchestrator()
        self.presgen_video = Phase3Orchestrator  # Existing
        
    def process_training_video(self, job_id: str, script: str, source_video: str):
        """Complete pipeline orchestration"""
        
        job_dir = Path(f"presgen-training/jobs/{job_id}")
        
        try:
            # Step 1: Extract source frame
            source_frame = self._extract_source_frame(source_video)
            
            # Step 2: Generate TTS audio
            audio_path = self._generate_tts_audio(script)
            
            # Step 3: Create avatar video
            avatar_video = self.avatar_generator.generate_avatar(
                audio_path, source_frame
            )
            
            # Step 4: Hand off to PresGen-Video
            # Convert to PresGen-Video job format
            presgen_job_id = self._create_presgen_job(avatar_video, script)
            
            # Process through existing PresGen-Video pipeline
            final_result = self.presgen_video.compose_final_video(presgen_job_id)
            
            return TrainingResult(
                success=True,
                avatar_video_path=avatar_video,
                final_video_path=final_result["output_path"],
                processing_time=final_result["processing_time"]
            )
            
        except Exception as e:
            return TrainingResult(success=False, error=str(e))
```

#### 3.2 Job Management Integration
```python
# Extend existing video job management
def create_training_job(script: str, source_video: str) -> str:
    """Create new training job integrated with existing system"""
    
    job_id = str(uuid.uuid4())
    
    # Create job entry compatible with existing system
    training_jobs[job_id] = {
        "id": job_id,
        "type": "training",  # New job type
        "status": "avatar_processing",
        "created_at": time.time(),
        "script": script,
        "source_video": source_video,
        "phases": {}
    }
    
    return job_id

# New API endpoints extending existing FastAPI app
@app.post("/training/upload")
async def upload_training_script(script: str, source_video: UploadFile):
    """Upload script and source video for training video generation"""
    
@app.post("/training/generate/{job_id}")  
async def generate_training_video(job_id: str):
    """Start avatar video generation and PresGen-Video processing"""
    
@app.get("/training/status/{job_id}")
async def get_training_status(job_id: str):
    """Get current processing status with resource usage info"""
```

## Quality and Performance Architecture

### Quality Control System
```python
class QualityController:
    """Manages quality vs. performance trade-offs"""
    
    def __init__(self, hardware_profile: HardwareProfile):
        self.presets = self._load_quality_presets()
        self.current_preset = self._select_optimal_preset(hardware_profile)
        
    def get_processing_settings(self) -> ProcessingSettings:
        """Return current optimal settings"""
        return ProcessingSettings(
            avatar_quality="standard",     # fast | standard | high
            enhancement_enabled=False,     # GFPGAN face enhancement
            resolution="720p",             # 720p | 1080p
            audio_quality="standard",      # basic | standard | high
            processing_priority="speed"    # speed | quality | balanced
        )
    
    def auto_adjust_for_resources(self, resource_status: ResourceStatus):
        """Dynamically adjust quality based on resource usage"""
        if resource_status.memory_percent > 85:
            self.current_preset = "fast_low_memory"
        elif resource_status.cpu_percent > 90:
            self.current_preset = "cpu_optimized"
```

### Performance Monitoring
```python
class PerformanceTracker:
    """Track processing performance across pipeline stages"""
    
    def track_stage(self, stage: str, duration: float, resources: ResourceUsage):
        """Record performance metrics for pipeline optimization"""
        
        metrics = {
            "stage": stage,
            "duration_seconds": duration,
            "peak_cpu_percent": resources.peak_cpu,
            "peak_memory_percent": resources.peak_memory,
            "quality_setting": self.current_quality
        }
        
        # Store for optimization and troubleshooting
        self.performance_db.append(metrics)
    
    def get_optimization_recommendations(self) -> List[str]:
        """Analyze performance data and recommend optimizations"""
        # Return recommendations based on bottlenecks and patterns
```

## Error Handling and Fallback Architecture

### Graceful Degradation Strategy
```python
class FallbackOrchestrator:
    """Manages graceful degradation when processing fails"""
    
    def handle_avatar_generation_failure(self, job_id: str, error: Exception):
        """Fallback strategies when avatar generation fails"""
        
        fallback_strategies = [
            self._try_wav2lip_fallback,      # Switch to simpler generator
            self._try_lower_quality,         # Reduce quality requirements  
            self._try_static_image_video,    # Use static image with audio
            self._try_original_video_overlay # Use original video with overlays
        ]
        
        for strategy in fallback_strategies:
            try:
                result = strategy(job_id)
                if result.success:
                    return result
            except Exception as e:
                log.warning(f"Fallback strategy failed: {e}")
                
        # Final fallback: Return original video with text overlays
        return self._create_text_only_presentation(job_id)
```

### Resource Exhaustion Handling
```python
class ResourceGuard:
    """Protect system from resource exhaustion during processing"""
    
    def __init__(self, limits: ResourceLimits):
        self.cpu_limit = limits.max_cpu_percent      # Default: 85%
        self.memory_limit = limits.max_memory_percent # Default: 80%
        self.temp_limit = limits.max_temp_celsius     # Default: 85°C
        
    def check_safe_to_proceed(self) -> Tuple[bool, str]:
        """Check if system resources allow processing to continue"""
        
        current = self._get_current_usage()
        
        if current.cpu_percent > self.cpu_limit:
            return False, f"CPU usage too high: {current.cpu_percent}%"
            
        if current.memory_percent > self.memory_limit:
            return False, f"Memory usage too high: {current.memory_percent}%"
            
        if current.temperature > self.temp_limit:
            return False, f"System temperature too high: {current.temperature}°C"
            
        return True, "Resources available"
    
    def pause_for_cooldown(self, duration: int = 60):
        """Pause processing to allow system to cool down"""
        log.info(f"Pausing processing for {duration}s to allow system recovery")
        time.sleep(duration)
```

## Integration Testing Architecture

### End-to-End Testing Framework
```python
class TrainingPipelineTest:
    """Test complete training video pipeline"""
    
    def test_minimal_example(self):
        """Test with minimal 15-second script to validate setup"""
        
        test_script = "Hello, this is a test of our avatar generation system."
        test_source = "test_assets/sample_frame.jpg"
        
        result = self.orchestrator.process_training_video(
            script=test_script,
            source_video=test_source
        )
        
        assert result.success
        assert Path(result.final_video_path).exists()
        assert result.processing_time < 300  # 5 minutes max for test
    
    def test_resource_limits(self):
        """Test behavior under resource constraints"""
        
        # Simulate high resource usage
        with ResourceLimitSimulator(cpu_limit=95, memory_limit=90):
            result = self.orchestrator.process_training_video(
                script=self.long_test_script,
                source_video=self.test_source
            )
            
            # Should succeed with reduced quality
            assert result.success
            assert result.quality_level == "fast"
```

## Deployment Architecture

### Local Development Setup
```bash
# One-command setup script
./setup_training_env.sh

# What it does:
# 1. Detect hardware capabilities
# 2. Install appropriate model versions
# 3. Configure quality presets
# 4. Run validation tests  
# 5. Create sample job
```

### Production Deployment (Future)
```yaml
# Docker configuration for consistent deployment
services:
  presgen-training:
    image: presgen/training:latest
    volumes:
      - ./models:/app/models
      - ./jobs:/app/jobs
    environment:
      - HARDWARE_PROFILE=apple_silicon_16gb
      - QUALITY_PRESET=demo_optimized
      - RESOURCE_LIMITS_ENABLED=true
    ports:
      - "8081:8080"
```

---

## Summary

This architecture provides a **complete, production-ready system** for generating avatar-based training videos with automatic content analysis and overlay generation. The design prioritizes:

1. **Speed and Simplicity**: Optimized for rapid VC demo creation
2. **Cost Effectiveness**: 100% local processing, zero cloud costs
3. **Hardware Adaptability**: Scales quality based on available resources
4. **Robust Fallbacks**: Multiple quality levels and processing options
5. **Seamless Integration**: Leverages existing PresGen-Video infrastructure

**Expected Performance**: 
- **Avatar Generation**: 5-8 minutes for 90-second video
- **Content Processing**: 2-3 minutes (existing PresGen-Video pipeline)
- **Total**: 8-12 minutes for complete professional presentation video

**Status**: Ready for implementation with 3-day development timeline to VC-demo ready system.