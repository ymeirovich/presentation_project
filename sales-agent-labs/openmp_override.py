#!/usr/bin/env python3
"""
OpenMP Override Module
This module must be imported FIRST to override OpenMP behavior at the system level
"""

import os
import sys
import ctypes
import warnings
from ctypes import CDLL, c_int

def setup_aggressive_openmp_protection():
    """Set up the most aggressive OpenMP protection possible"""
    
    # Set all environment variables before any imports
    openmp_vars = {
        'KMP_DUPLICATE_LIB_OK': 'TRUE',
        'OMP_NUM_THREADS': '1',
        'OPENBLAS_NUM_THREADS': '1', 
        'MKL_NUM_THREADS': '1',
        'VECLIB_MAXIMUM_THREADS': '1',
        'NUMEXPR_NUM_THREADS': '1',
        'OMP_MAX_ACTIVE_LEVELS': '1',
        'KMP_WARNINGS': '0',
        'OMP_WARNINGS': '0',
        'OMP_DISPLAY_ENV': 'FALSE'
    }
    
    for key, value in openmp_vars.items():
        os.environ[key] = value
    
    # Suppress ALL OpenMP related warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", message=".*omp.*", category=UserWarning)
    warnings.filterwarnings("ignore", message=".*OMP.*", category=UserWarning)
    warnings.filterwarnings("ignore", message=".*OpenMP.*", category=UserWarning)
    warnings.filterwarnings("ignore", message=".*FP16.*", category=UserWarning)
    
    # Try to load OpenMP library and override functions if possible
    try:
        # On macOS, try to find and configure libomp
        if sys.platform == "darwin":
            # Common locations for libomp on macOS
            libomp_paths = [
                "/opt/homebrew/lib/libomp.dylib",
                "/usr/local/lib/libomp.dylib", 
                "/System/Library/Frameworks/Accelerate.framework/Versions/A/Frameworks/vecLib.framework/Versions/A/libBLAS.dylib"
            ]
            
            for path in libomp_paths:
                try:
                    if os.path.exists(path):
                        lib = CDLL(path)
                        # Try to set max active levels if the function exists
                        try:
                            if hasattr(lib, 'omp_set_max_active_levels'):
                                lib.omp_set_max_active_levels(1)
                            if hasattr(lib, 'omp_set_num_threads'):
                                lib.omp_set_num_threads(1)
                        except:
                            pass
                        break
                except:
                    continue
                    
    except Exception:
        # If direct library manipulation fails, that's ok
        pass
    
    # Redirect stderr temporarily to suppress OpenMP messages
    class OpenMPSuppressor:
        def __init__(self):
            self.original_stderr = sys.stderr
            self.suppressed_messages = []
            
        def write(self, message):
            # Filter out OpenMP messages
            if any(keyword in message.lower() for keyword in [
                'omp:', 'openmp', 'omp_set_nested', 'kmp_duplicate_lib_ok',
                'libomp.dylib', 'multiple copies', 'runtime have been linked'
            ]):
                self.suppressed_messages.append(message)
                return  # Don't write OpenMP messages
            else:
                self.original_stderr.write(message)
                
        def flush(self):
            self.original_stderr.flush()
    
    # Install the suppressor
    sys.stderr = OpenMPSuppressor()
    
    return True

# Apply protection immediately when this module is imported
if __name__ != "__main__":
    setup_aggressive_openmp_protection()

if __name__ == "__main__":
    print("OpenMP Override Module")
    print("Setting up aggressive OpenMP protection...")
    success = setup_aggressive_openmp_protection()
    
    if success:
        print("✅ OpenMP protection configured")
        print("Environment variables set:")
        for key in ['KMP_DUPLICATE_LIB_OK', 'OMP_NUM_THREADS', 'OMP_MAX_ACTIVE_LEVELS']:
            print(f"  {key}={os.environ.get(key, 'NOT SET')}")
    else:
        print("❌ Failed to configure OpenMP protection")
        
    # Test import of problematic libraries
    try:
        print("Testing numpy import...")
        import numpy as np
        print("✅ numpy imported successfully")
        
        print("Testing torch import...")
        import torch
        torch.set_num_threads(1)
        print("✅ torch imported successfully")
        
        print("Testing whisper import...")
        import whisper
        print("✅ whisper imported successfully")
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")