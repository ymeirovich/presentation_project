# PresGen-Training: Avatar Video Generation PRD

## Product Overview

**PresGen-Training** is a local-first avatar video generation system that creates professional presentation videos from text scripts using AI-powered face synthesis, integrated with the existing PresGen-Video pipeline for automatic bullet point overlays.

### Mission Statement
Enable rapid creation of professional avatar-based training videos with automatic content summarization and overlay generation, optimized for VC demos and POCs with minimal cost and maximum speed.

## Business Context

### Target Use Case
- **Primary**: VC demo POC showing AI avatar + content summarization capabilities
- **Timeline**: Single demo video for immediate funding presentation
- **Quality Bar**: Demo-quality (not production) - speed and functionality over perfection
- **Budget**: $0 processing cost, local hardware only

### Success Metrics
- ✅ Generate 60-90 second avatar video from script in <10 minutes total processing
- ✅ Seamless integration with existing PresGen-Video bullet overlay system
- ✅ Professional enough quality for VC presentation
- ✅ Runs entirely on MacBook hardware (M1/M2 preferred)
- ✅ Zero cloud API costs

## Technical Requirements

### Core Functionality

#### 1. Avatar Video Generation
- **Input**: Text script (500-1000 words)
- **Output**: MP4 video of user avatar speaking the script
- **Duration Target**: 60-90 seconds final video
- **Quality**: Demo-appropriate (720p minimum)

#### 2. Script-to-Speech Pipeline
- **Text-to-Speech**: Local TTS generation (gTTS or similar)
- **Audio Format**: 16kHz WAV for compatibility
- **Speech Timing**: Natural pacing with proper pauses
- **Voice Quality**: Clear, professional presentation tone

#### 3. Face Synthesis Integration
- **Primary Option**: SadTalker (stable, well-documented)
- **Fallback Option**: Wav2Lip (simpler, faster)
- **Source Material**: Single high-quality frame from existing user video
- **Lip Sync Quality**: Believable for business presentation context

#### 4. PresGen-Video Integration
- **Seamless Handoff**: Generated avatar video → PresGen-Video pipeline
- **Automatic Processing**: Script content analysis for bullet point generation
- **Overlay Application**: Right-side bullet highlights on avatar video
- **Output Format**: Professional presentation video with avatar + content overlays

### Technical Architecture

#### Phase 1: Avatar Video Generation (Local)
```
Text Script → TTS Audio → SadTalker/Wav2Lip → Raw Avatar Video
```

#### Phase 2: Content Integration (Existing Pipeline)
```
Raw Avatar Video + Script → PresGen-Video → Professional Presentation
```

### Hardware Requirements

#### Minimum Specifications
- **MacBook M1/M2**: 8GB RAM, 50GB available storage
- **Intel MacBook Pro**: 16GB RAM, dedicated GPU preferred
- **Processing Time Budget**: 5-10 minutes avatar generation + 2-3 minutes PresGen-Video

#### Resource Monitoring
- Real-time CPU/memory monitoring during processing
- Automatic warnings at >85% resource usage
- Graceful fallback to lower quality if needed

## Feature Specifications

### 1. Script Input System
```yaml
Input Methods:
  - Text file upload (.txt)
  - Direct text input (web form)
  - Script validation and word count
  
Constraints:
  - Maximum 1000 words (to fit 90-second target)
  - Minimum 300 words (to generate meaningful content)
  - Automatic script optimization for speech
```

### 2. Avatar Generation Pipeline
```yaml
Source Material:
  - Single frame extraction from existing user video
  - Automatic best frame selection (well-lit, front-facing)
  - Image quality validation and enhancement
  
Processing Options:
  - Quality Level: Demo | Standard | High
  - Processing Speed: Fast (SadTalker --still) | Quality (full processing)
  - Enhancement: Optional GFPGAN face enhancement
```

### 3. Integration Architecture
```yaml
File Flow:
  presgen-training/
  ├── input/
  │   ├── scripts/           # Input text scripts
  │   └── source_images/     # Extracted user frames
  ├── output/
  │   ├── audio/            # Generated TTS files
  │   ├── avatar_videos/    # Raw avatar videos
  │   └── final/           # Final processed videos
  └── temp/                # Temporary processing files
```

### 4. Quality Controls
```yaml
Validation Checks:
  - Script readability and timing validation
  - Audio quality verification (volume, clarity)
  - Video sync quality assessment
  - Resource usage monitoring throughout
  
Fallback Strategies:
  - Reduce quality settings if resources insufficient
  - Switch to Wav2Lip if SadTalker fails
  - Use original video with overlays if avatar generation fails
```

## User Experience Flow

### 1. Setup Phase (One-time)
1. **Source Video Upload**: Upload existing video for frame extraction
2. **Avatar Calibration**: System extracts best frames for avatar generation
3. **Hardware Validation**: Test local resources with small sample
4. **Integration Test**: Verify PresGen-Video pipeline connectivity

### 2. Production Flow (Per Demo)
1. **Script Input**: Paste or upload presentation script
2. **Preview & Validate**: Review script timing and content analysis
3. **Avatar Generation**: Initiate local avatar video creation (5-8 minutes)
4. **PresGen-Video Integration**: Automatic handoff for bullet overlay processing (2-3 minutes)
5. **Final Output**: Download complete presentation video

### 3. Quality Assurance
1. **Preview Mode**: Quick low-quality preview for validation
2. **Resource Monitoring**: Real-time system performance feedback
3. **Quality Settings**: Adjustable based on hardware capabilities
4. **Fallback Options**: Automatic degradation if needed

## Technical Implementation Plan

### Phase 1: Foundation (Day 1 - 6 hours)
- Setup SadTalker and Wav2Lip environments
- Create resource monitoring system
- Build script-to-TTS pipeline
- Implement source frame extraction
- Basic avatar generation testing

### Phase 2: Integration (Day 2 - 6 hours)
- PresGen-Video pipeline integration
- File management and organization
- Quality validation systems
- Error handling and fallbacks
- End-to-end testing

### Phase 3: Polish (Day 3 - 4 hours)
- User interface for script input
- Resource optimization
- Performance tuning
- Demo preparation and testing
- Documentation and usage guides

## Risk Mitigation

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|---------|------------|
| MacBook insufficient resources | Medium | High | Resource monitoring + quality fallbacks |
| SadTalker setup complexity | Medium | Medium | Wav2Lip fallback + Docker option |
| Poor avatar quality | Low | Medium | Multiple source frames + enhancement |
| Integration failures | Low | High | Robust error handling + fallbacks |

### Timeline Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|---------|------------|
| Setup takes longer than expected | Medium | Medium | Start with Wav2Lip (simpler) |
| Quality iteration needed | High | Low | Accept demo-quality for POC |
| Hardware incompatibility | Low | High | Test early with minimal examples |

## Success Criteria

### MVP Requirements (Must Have)
- [x] Generate avatar video from text script locally
- [x] Integrate with PresGen-Video for bullet overlays  
- [x] Complete pipeline processing in <15 minutes total
- [x] Professional enough quality for VC demo
- [x] Zero cloud processing costs

### Demo Requirements (Should Have)
- [x] Resource monitoring and optimization
- [x] Quality settings based on hardware
- [x] Fallback options for robustness
- [x] Simple user interface for script input
- [x] Automated end-to-end processing

### Future Enhancements (Nice to Have)
- [ ] Multiple avatar personas/styles
- [ ] Advanced script optimization
- [ ] Batch processing capabilities
- [ ] Cloud deployment options
- [ ] Professional production quality

## Competitive Analysis

### Alternatives Considered
1. **Cloud-based solutions (Synthesia, D-ID)**: ❌ High cost, not local
2. **Murf + video editing**: ❌ Complex workflow, manual overlay work
3. **Live recording + editing**: ❌ Time-intensive, requires multiple takes
4. **SadTalker + PresGen-Video**: ✅ **Selected** - Local, cost-effective, integrated

### Key Differentiators
- **Local-first processing**: Zero ongoing costs, full control
- **Integrated content analysis**: Automatic bullet point generation from script
- **Speed optimized**: Demo-ready in minutes, not hours
- **Hardware adaptive**: Works within MacBook constraints

## Resource Requirements

### Development Resources
- **Time**: 3 days (16 hours) for MVP
- **Skills**: Python, FFmpeg, local AI model setup
- **Hardware**: MacBook M1/M2 with 16GB RAM preferred
- **Storage**: 10-20GB for models and temporary files

### Operational Resources
- **Per Video**: 5-10 minutes processing time
- **Storage**: 2-5GB temporary files per video
- **Memory**: 4-8GB peak usage during processing
- **Cost**: $0 ongoing (local processing only)

## Performance Targets

### Processing Time Targets
- **Avatar Generation**: 5-8 minutes for 90-second video
- **PresGen-Video Integration**: 2-3 minutes (existing pipeline)
- **Total Pipeline**: <15 minutes end-to-end
- **Setup Time**: <2 hours initial configuration

### Quality Targets
- **Video Resolution**: 720p minimum, 1080p preferred
- **Audio Quality**: Clear speech, proper lip sync
- **Content Accuracy**: Bullet points match script content
- **Professional Appearance**: Suitable for VC presentation

## Implementation Priority

### P0 (Critical - Must work for demo)
1. Basic avatar video generation from script
2. PresGen-Video integration and overlay processing
3. Resource monitoring and hardware validation
4. End-to-end automated pipeline

### P1 (Important - Improves demo quality)
1. Quality optimization and enhancement options
2. Fallback systems and error handling
3. Simple user interface for script input
4. Performance tuning and optimization

### P2 (Nice to have - Future improvements)
1. Advanced avatar customization
2. Batch processing capabilities
3. Cloud deployment preparation
4. Professional production quality features

---

## Appendix: Technical Specifications

### Supported Hardware
- **Recommended**: MacBook Pro M1/M2, 16GB RAM, 512GB SSD
- **Minimum**: MacBook Air M1, 8GB RAM, 256GB SSD
- **Fallback**: Intel MacBook Pro 2019+, 16GB RAM, discrete GPU

### Software Dependencies
```yaml
Core Dependencies:
  - Python 3.9+
  - PyTorch (Apple Silicon optimized)
  - FFmpeg with full codec support
  - SadTalker (primary) + Wav2Lip (fallback)
  - gTTS or similar TTS library
  
Integration Dependencies:
  - Existing PresGen-Video pipeline
  - FastAPI for web interface
  - File management utilities
```

### File Format Specifications
```yaml
Input Formats:
  - Scripts: .txt (UTF-8 encoded)
  - Source Video: .mp4 (H.264, 720p+)
  - Source Images: .jpg/.png (high resolution)

Output Formats:  
  - Avatar Video: .mp4 (H.264, 720p, AAC audio)
  - Final Video: .mp4 (H.264, 720p, with overlays)
  - Audio: .wav (16kHz mono) / .mp3 (for TTS)
```

**Status**: Ready for Implementation
**Owner**: Development Team  
**Timeline**: 3 days MVP → VC Demo Ready