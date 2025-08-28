#!/usr/bin/env python3
"""
Minimal test to identify the bytes object source.
"""

import requests
import json
import time

def test_minimal_render():
    """Test with the absolute minimum request."""
    url = "http://localhost:8080/render"
    
    payload = {
        "report_text": "This is a minimal test. No images should be generated.",
        "slides": 1,
        "use_cache": False,
        "request_id": f"minimal-test-{int(time.time())}"
    }
    
    print("🧪 Testing minimal render (no images)...")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS! Minimal render works.")
            result = response.json()
            print(f"URL: {result.get('url')}")
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    success = test_minimal_render()
    print(f"Result: {'PASS' if success else 'FAIL'}")