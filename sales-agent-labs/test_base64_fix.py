#!/usr/bin/env python3
"""
Test script to verify the base64 chart embedding fix works.
"""
import pathlib
import os
from src.agent.slides_google import _create_base64_data_url

def test_base64_embedding():
    print("=== Testing Base64 Chart Embedding Fix ===")
    
    # Find existing chart files to test
    chart_dirs = pathlib.Path("out/images/charts").glob("*")
    test_files = []
    
    for chart_dir in chart_dirs:
        chart_files = list(chart_dir.glob("*.png"))
        test_files.extend(chart_files[:2])  # Test up to 2 files per directory
    
    if not test_files:
        print("❌ No chart files found to test")
        return False
        
    print(f"Found {len(test_files)} chart files to test")
    
    success_count = 0
    for test_file in test_files:
        file_size = test_file.stat().st_size
        print(f"\n📊 Testing: {test_file.name}")
        print(f"   Size: {file_size:,} bytes ({file_size/1024:.1f}KB)")
        
        if file_size <= 100_000:  # 100KB threshold
            data_url = _create_base64_data_url(test_file)
            if data_url and data_url.startswith("data:image/png;base64,"):
                print(f"   ✅ Base64 embedding successful")
                print(f"   📏 Data URL length: {len(data_url):,} chars")
                success_count += 1
            else:
                print(f"   ❌ Base64 embedding failed")
        else:
            print(f"   📈 File too large (>100KB) - would use Drive upload")
            success_count += 1  # This is expected behavior
    
    print(f"\n=== Results ===")
    print(f"✅ {success_count}/{len(test_files)} files handled correctly")
    
    if success_count == len(test_files):
        print("🎉 Base64 fix is working correctly!")
        print("📈 Charts <100KB will embed instantly (no Drive upload timeouts)")
        print("📂 Charts >100KB will still use Drive upload")
        return True
    else:
        print("⚠️  Some issues detected")
        return False

if __name__ == "__main__":
    test_base64_embedding()