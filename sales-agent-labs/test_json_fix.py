#!/usr/bin/env python3
"""
Test script to verify the JSON serialization fix.
"""

import requests
import json
import time

def test_simple_render():
    """Test a simple render request to see if the JSON serialization error is fixed."""
    url = "http://localhost:8080/render"
    
    payload = {
        "report_text": "This is a simple test report to verify the JSON serialization fix.",
        "slides": 1,
        "use_cache": False,  # Force fresh generation
        "request_id": f"json-fix-test-{int(time.time())}"
    }
    
    print("🧪 Testing JSON serialization fix...")
    print(f"Request: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! JSON serialization is working")
            print(f"Presentation URL: {result.get('url')}")
            print(f"Created slides: {result.get('created_slides')}")
            return True
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Error response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON response: {e}")
        print(f"Raw response: {response.text}")
        return False

if __name__ == "__main__":
    success = test_simple_render()
    
    if success:
        print("\n🎉 The JSON serialization fix appears to be working!")
    else:
        print("\n💡 If you're still seeing errors, check the server logs for:")
        print("   - 'Tool returned bytes object at path: ...' messages")
        print("   - 'Response contains bytes at: ...' messages")
        print("   - Any remaining TypeError: Object of type bytes is not JSON serializable")
        
    exit(0 if success else 1)