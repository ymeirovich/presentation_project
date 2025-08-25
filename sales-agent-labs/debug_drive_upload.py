#!/usr/bin/env python3
"""
Debug Drive upload performance by testing chart upload directly.
Run this to isolate whether the bottleneck is Drive API or elsewhere.
"""
import os
import time
import pathlib
from src.agent.slides_google import upload_image_to_drive

def test_drive_upload():
    # Find a recent chart file to test
    chart_dirs = pathlib.Path("out/images/charts").glob("*")
    for chart_dir in chart_dirs:
        chart_files = list(chart_dir.glob("*.png"))
        if chart_files:
            test_file = chart_files[0]
            print(f"Testing Drive upload with: {test_file}")
            print(f"File size: {test_file.stat().st_size:,} bytes")
            
            start_time = time.time()
            try:
                file_id, public_url = upload_image_to_drive(test_file, make_public=True)
                duration = time.time() - start_time
                print(f"✅ SUCCESS: {duration:.1f}s")
                print(f"File ID: {file_id}")
                print(f"URL: {public_url}")
                return True
            except Exception as e:
                duration = time.time() - start_time  
                print(f"❌ FAILED after {duration:.1f}s: {e}")
                return False
    
    print("No chart files found to test")
    return False

if __name__ == "__main__":
    # Enable debug logging
    os.environ["ENABLE_GCP_DEBUG_LOGGING"] = "true"
    
    print("=== Drive Upload Performance Test ===")
    test_drive_upload()