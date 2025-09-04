# PresGen Video Logging Setup

## Overview
This directory contains server-side logs for PresGen Video processing. The logging system has been configured to output detailed debug information to help diagnose OpenMP conflicts and video processing issues.

## Log Files
- `debug-gcp-YYYYMMDD-HHMMSS.log` - Comprehensive server logs including:
  - Video processing pipeline logs (Phase 1, 2, 3)
  - Whisper transcription logs
  - ffmpeg composition logs
  - HTTP API request/response logs
  - OpenMP conflict warnings
  - Error traces and debugging info

## Logging Configuration
Logging is controlled by these environment variables:
- `ENABLE_GCP_DEBUG_LOGGING=true` - Enable detailed GCP and library logging
- `ENABLE_LOCAL_DEBUG_FILE=true` - Enable file logging to this directory
- `PRESGEN_VIDEO_LOGGING=true` - Direct logs to presgen-video/logs/ instead of src/logs/

## Video-Specific Loggers
The following loggers output to these files:
- `video_transcription` - Whisper audio transcription
- `video_content` - Content generation and summarization  
- `video_slides` - Slide generation with Playwright
- `video_phase2` - Phase 2 orchestration (content pipeline)
- `video_phase3` - Phase 3 orchestration (final composition)
- `video_audio` - Audio extraction and processing
- `video_face` - Face detection and cropping
- `service` - FastAPI HTTP service logs
- `uvicorn` - Web server logs

## Starting the Server with Logging
Use the provided startup script that configures all necessary environment variables:

```bash
./start_video_server.sh
```

This script:
1. Kills existing uvicorn processes
2. Sets OpenMP protection variables
3. Enables comprehensive logging to this directory
4. Filters common warnings
5. Starts uvicorn with proper configuration

## Debugging OpenMP Issues
If you encounter Python crashes or OpenMP conflicts, run the diagnostic script:

```bash
python debug_openmp.py
```

This will:
- Check OpenMP environment variables
- Test Whisper import with protection
- Check system resources and processes
- Provide troubleshooting recommendations

## Common Log Patterns
- **OpenMP Warnings**: Look for `OMP: Error #15` or `KMP_DUPLICATE_LIB_OK` messages
- **Whisper Errors**: Search for `whisper_model_load_error` or `FP16 is not supported`
- **Video Processing**: Look for `phase1_processing_start`, `phase2_processing_start`, `phase3_composition_start`
- **HTTP Errors**: Search for HTTP status codes 500, 400, or exception traces

## Manual Server Startup
If you prefer to start uvicorn manually, use these environment variables:

```bash
export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export ENABLE_GCP_DEBUG_LOGGING=true
export ENABLE_LOCAL_DEBUG_FILE=true
export PRESGEN_VIDEO_LOGGING=true

uvicorn src.service.http:app --reload --port 8080
```

## Log Rotation
Logs are timestamped and will not overwrite each other. Periodically clean old log files to save disk space:

```bash
# Keep only logs from last 7 days
find presgen-video/logs -name "debug-gcp-*.log" -mtime +7 -delete
```