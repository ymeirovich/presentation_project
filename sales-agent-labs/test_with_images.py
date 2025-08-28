#!/usr/bin/env python3
"""
Test script to check if image generation bytes error is fixed.
"""

import requests
import json
import time

def test_image_render():
    """Test with request that should generate images."""
    url = "http://localhost:8080/render"
    
    payload = {
        "report_text": """
        This is a test report about technology trends in 2024. 
        
        Key findings include:
        - AI adoption has accelerated across industries
        - Cloud computing continues to dominate infrastructure decisions
        - Cybersecurity remains a top priority for organizations
        
        The market shows strong growth in several areas, with particular emphasis on 
        automation and digital transformation initiatives.
        """,
        "slides": 2,
        "use_cache": False,  # Force fresh generation
        "request_id": f"image-test-{int(time.time())}"
    }
    
    print("🧪 Testing render with image generation...")
    
    try:
        response = requests.post(url, json=payload, timeout=180)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS! Image render works.")
            result = response.json()
            print(f"URL: {result.get('url')}")
            print(f"Created slides: {result.get('created_slides')}")
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    success = test_image_render()
    print(f"Result: {'PASS' if success else 'FAIL'}")
    
    if not success:
        print("\n💡 Check server logs for:")
        print("   - 'imagen_result_contains_bytes' events")  
        print("   - 'slide_params_contains_bytes' events")
        print("   - 'removed_bytes_from_slide_params' events")