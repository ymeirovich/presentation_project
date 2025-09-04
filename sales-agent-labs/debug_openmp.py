#!/usr/bin/env python3
"""
OpenMP Debugging Script for PresGen Video
Use this to diagnose OpenMP conflicts before starting the server
"""

import os
import sys
import warnings

def check_openmp_environment():
    """Check current OpenMP environment setup"""
    print("🔍 OpenMP Environment Check")
    print("=" * 50)
    
    env_vars = [
        'KMP_DUPLICATE_LIB_OK',
        'OMP_NUM_THREADS',
        'OPENBLAS_NUM_THREADS',
        'MKL_NUM_THREADS'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'NOT SET')
        status = "✅" if value != 'NOT SET' else "❌"
        print(f"{status} {var}: {value}")
    
    print()

def test_whisper_import():
    """Test Whisper import with OpenMP protection"""
    print("🎤 Testing Whisper Import")
    print("=" * 50)
    
    # Set OpenMP protection
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    
    # Filter warnings
    warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")
    
    try:
        print("Importing whisper...")
        import whisper
        print("✅ Whisper imported successfully")
        
        print("Checking available models...")
        models = whisper.available_models()
        print(f"✅ Available models: {models}")
        
        print("Testing tiny model load...")
        model = whisper.load_model("tiny", device="cpu")
        print("✅ Tiny model loaded successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Whisper test failed: {e}")
        return False

def check_system_resources():
    """Check system resources and processes"""
    print("💻 System Resources Check")
    print("=" * 50)
    
    import psutil
    
    # Check memory
    memory = psutil.virtual_memory()
    print(f"Memory: {memory.percent}% used ({memory.available // 1024**2} MB available)")
    
    # Check for existing uvicorn processes
    uvicorn_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'uvicorn' in ' '.join(proc.info['cmdline'] or []):
                uvicorn_procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if uvicorn_procs:
        print(f"⚠️  Found {len(uvicorn_procs)} existing uvicorn processes:")
        for proc in uvicorn_procs:
            print(f"   PID {proc['pid']}: {' '.join(proc['cmdline'][:3])}...")
    else:
        print("✅ No existing uvicorn processes found")
    
    print()

if __name__ == "__main__":
    print("🎥 PresGen Video OpenMP Diagnostics")
    print("=" * 50)
    print()
    
    check_openmp_environment()
    check_system_resources()
    
    print("🧪 Running Whisper Test")
    print("=" * 50)
    whisper_ok = test_whisper_import()
    
    print()
    if whisper_ok:
        print("✅ All tests passed! Server should start without OpenMP conflicts.")
        print("💡 You can now start the server with: ./start_video_server.sh")
    else:
        print("❌ OpenMP conflicts detected. Try the following:")
        print("   1. Kill all Python processes: pkill -f python")
        print("   2. Restart your terminal")
        print("   3. Run this script again")
        print("   4. If issues persist, restart your computer")
    
    print("=" * 50)