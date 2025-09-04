#!/usr/bin/env python3
"""
Comprehensive OpenMP Protection Test
Test all critical imports and operations to ensure no conflicts
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute()))
import openmp_override

print("🧪 Comprehensive OpenMP Protection Test")
print("=" * 50)

def test_basic_imports():
    """Test basic scientific computing imports"""
    print("1. Testing basic scientific imports...")
    
    try:
        import numpy as np
        print("✅ numpy imported")
        
        import torch
        torch.set_num_threads(1)
        print("✅ torch imported and configured")
        
        # Test basic operations
        x = np.array([1, 2, 3])
        y = torch.tensor([4, 5, 6])
        print(f"✅ Basic operations work: numpy sum={x.sum()}, torch sum={y.sum().item()}")
        
        return True
    except Exception as e:
        print(f"❌ Basic imports failed: {e}")
        return False

def test_whisper_import():
    """Test Whisper import with protection"""
    print("\n2. Testing Whisper import...")
    
    try:
        import whisper
        print("✅ Whisper imported successfully")
        
        # Test model availability
        models = whisper.available_models()
        print(f"✅ Available models: {models[:3]}...")  # Show first 3
        
        # Test tiny model loading
        model = whisper.load_model("tiny", device="cpu")
        print("✅ Tiny model loaded successfully")
        
        return True
    except Exception as e:
        print(f"❌ Whisper test failed: {e}")
        return False

def test_service_imports():
    """Test PresGen service imports"""
    print("\n3. Testing PresGen service imports...")
    
    try:
        from src.service import http
        print("✅ HTTP service imported")
        
        from src.mcp.tools import video_transcription
        print("✅ Video transcription module imported")
        
        from src.mcp.tools import video_phase2
        print("✅ Video phase2 module imported")
        
        from src.mcp.tools import video_phase3
        print("✅ Video phase3 module imported")
        
        return True
    except Exception as e:
        print(f"❌ Service imports failed: {e}")
        return False

def test_concurrent_operations():
    """Test concurrent operations that might trigger conflicts"""
    print("\n4. Testing concurrent operations...")
    
    try:
        import threading
        import time
        import numpy as np
        import torch
        
        results = []
        
        def worker(thread_id):
            # Simulate some ML operations
            for i in range(5):
                x = np.random.rand(100, 100)
                y = torch.rand(100, 100)
                result = np.sum(x) + torch.sum(y).item()
                time.sleep(0.1)
            results.append(f"Thread {thread_id} completed")
        
        # Start 3 worker threads
        threads = []
        for i in range(3):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        print(f"✅ Concurrent operations completed: {len(results)} threads finished")
        return True
        
    except Exception as e:
        print(f"❌ Concurrent operations failed: {e}")
        return False

def main():
    """Run all tests"""
    tests = [
        test_basic_imports,
        test_whisper_import,
        test_service_imports,
        test_concurrent_operations
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Server should start without OpenMP conflicts!")
        return True
    else:
        print("⚠️  Some tests failed - OpenMP conflicts may still occur")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)