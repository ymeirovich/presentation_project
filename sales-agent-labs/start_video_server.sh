#!/bin/bash

# PresGen Video Server Startup Script
# This script configures environment variables and starts uvicorn with proper OpenMP protection

echo "🎥 Starting PresGen Video Server with OpenMP protection..."

# Kill any existing uvicorn processes
echo "🧹 Cleaning up existing uvicorn processes..."
pkill -f uvicorn
sleep 2

# Set comprehensive OpenMP environment variables to prevent conflicts
export KMP_DUPLICATE_LIB_OK=TRUE
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OMP_MAX_ACTIVE_LEVELS=1

# Enable comprehensive logging
export ENABLE_GCP_DEBUG_LOGGING=true
export ENABLE_LOCAL_DEBUG_FILE=true
export PRESGEN_VIDEO_LOGGING=true

# Filter out common warnings and force process isolation
export PYTHONWARNINGS="ignore::UserWarning:whisper"
export USE_SUBPROCESS_WHISPER=true

# Create logs directory
mkdir -p presgen-video/logs

echo "🔧 Environment configured:"
echo "  - OpenMP override module: ENABLED"
echo "  - Video logging: presgen-video/logs/"
echo "  - Thread limiting: 1 thread per library"
echo "  - Warnings filtered: All OpenMP messages suppressed"
echo "  - stderr redirection: OpenMP messages filtered"

echo ""
echo "🚀 Starting uvicorn server..."
echo "  - Access: http://localhost:8080"
echo "  - Logs: presgen-video/logs/"
echo "  - Press Ctrl+C to stop"
echo ""

# Start the server
uvicorn src.service.http:app --reload --port 8080