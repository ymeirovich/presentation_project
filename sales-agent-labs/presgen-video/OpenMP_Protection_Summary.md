# OpenMP Conflict Protection Summary

## Problem
Python crashes with OpenMP conflicts when loading Whisper for video transcription:
- `OMP: Error #15: Initializing libomp.dylib, but found libomp.dylib already initialized`  
- `OMP: Info #276: omp_set_nested routine deprecated, please use omp_set_max_active_levels instead`

## Final Solution: Aggressive OpenMP Override Module ✅

**Status:** All tests passed - server should start without OpenMP conflicts!

## Multi-Layer Protection Implemented

### 0. OpenMP Override Module (PRIMARY SOLUTION)
**File:** `openmp_override.py`

This module provides system-level OpenMP protection by:
- Setting all OpenMP environment variables before any imports
- Overriding stderr to suppress OpenMP messages
- Attempting direct library-level OpenMP configuration
- Comprehensive warning suppression

**Usage:** Imported first in all critical modules:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import openmp_override  # MUST BE FIRST
```

### 1. Environment Variable Protection
Set in multiple locations for comprehensive coverage:

**Variables Set:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE              # Allow duplicate OpenMP libraries
OMP_NUM_THREADS=1                      # Limit OpenMP threads  
OPENBLAS_NUM_THREADS=1                 # Limit BLAS threads
MKL_NUM_THREADS=1                      # Limit Intel MKL threads
VECLIB_MAXIMUM_THREADS=1               # Limit macOS Accelerate threads
NUMEXPR_NUM_THREADS=1                  # Limit NumExpr threads
OMP_MAX_ACTIVE_LEVELS=1                # Set max OpenMP nesting level
```

**Locations Applied:**
- ✅ `src/service/http.py` - Server startup protection
- ✅ `src/mcp/tools/video_transcription.py` - Before Whisper import
- ✅ `start_video_server.sh` - Shell environment
- ✅ `whisper_subprocess.py` - Subprocess isolation

### 2. Warning Suppression
```python
warnings.filterwarnings("ignore", category=UserWarning, module="whisper")
warnings.filterwarnings("ignore", message=".*FP16 is not supported on CPU.*")
warnings.filterwarnings("ignore", message=".*omp_set_nested.*")
```

### 3. Lazy Import Strategy
**File:** `src/mcp/tools/video_transcription.py`

```python
# Defer whisper import to avoid startup crashes
whisper = None
torch = None

def _lazy_import_whisper():
    """Lazy import whisper with full OpenMP protection"""
    global whisper, torch
    if whisper is None:
        # Additional protection right before import
        os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
        os.environ['OMP_MAX_ACTIVE_LEVELS'] = '1'
        
        import whisper as _whisper
        import torch as _torch
        
        _torch.set_num_threads(1)  # Force single-threaded
        
        whisper = _whisper
        torch = _torch
        
    return whisper, torch
```

### 4. Subprocess Isolation (Fallback)
**Files:** 
- `whisper_subprocess.py` - Standalone Whisper runner
- `src/mcp/tools/video_transcription_subprocess.py` - Subprocess-based agent

**Benefits:**
- Complete process isolation prevents OpenMP conflicts
- Robust error handling and timeout protection
- JSON communication between processes
- Fallback option if lazy loading fails

### 5. Thread Limiting
```python
torch.set_num_threads(1)  # Limit PyTorch threads
```

## Usage Instructions

### Option 1: Use Startup Script (Recommended)
```bash
./start_video_server.sh
```

This automatically:
- Kills existing uvicorn processes
- Sets all OpenMP protection variables
- Enables comprehensive logging
- Starts server with protection

### Option 2: Manual Server Start
```bash
# Set environment
export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OMP_MAX_ACTIVE_LEVELS=1
export PRESGEN_VIDEO_LOGGING=true
export ENABLE_GCP_DEBUG_LOGGING=true
export ENABLE_LOCAL_DEBUG_FILE=true

# Start server
uvicorn src.service.http:app --reload --port 8080
```

### Option 3: Test Whisper Separately
```bash
python debug_openmp.py
```

## Debugging Tools

### 1. OpenMP Diagnostic Script
**File:** `debug_openmp.py`
- Check environment variables
- Test Whisper import with protection
- System resource monitoring
- Process conflict detection

### 2. Subprocess Whisper Test
```bash
python whisper_subprocess.py /path/to/audio.wav tiny
```

### 3. Logging Analysis
**Location:** `presgen-video/logs/debug-gcp-YYYYMMDD-HHMMSS.log`

**Key Log Patterns:**
- `whisper_model_loading` - Model initialization start
- `whisper_model_loaded` - Successful model load
- `whisper_model_load_error` - Model loading failure
- `subprocess_whisper_start` - Subprocess transcription start

## Protection Strategy Hierarchy

1. **Primary**: Lazy import with comprehensive environment setup
2. **Backup**: Multiple environment variable locations
3. **Fallback**: Subprocess isolation for complete process separation
4. **Monitoring**: Comprehensive logging to diagnose any remaining issues

## Testing Status

After implementing all protections:
- ✅ Environment variables set at all import points
- ✅ Warning suppression for common OpenMP messages
- ✅ Lazy loading prevents startup crashes
- ✅ Subprocess isolation as ultimate fallback
- ✅ Comprehensive logging to `presgen-video/logs/`
- ✅ Diagnostic tools for troubleshooting

## Next Steps If Issues Persist

1. **Check Logs**: Review `presgen-video/logs/` for specific error patterns
2. **Run Diagnostics**: `python debug_openmp.py` to identify remaining conflicts
3. **Use Subprocess Mode**: Set `USE_SUBPROCESS_WHISPER=true` for complete isolation
4. **System Restart**: If conflicts persist, restart computer to clear all OpenMP states

The multi-layer approach ensures that even if one protection layer fails, others will catch and prevent the OpenMP conflicts that cause Python crashes during video processing.