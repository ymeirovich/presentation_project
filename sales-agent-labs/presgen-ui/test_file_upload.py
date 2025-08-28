#!/usr/bin/env python3

import requests
import json
import time

# Test file upload via /render endpoint
def test_file_upload():
    # Read the test file content
    with open('test_large_upload.txt', 'r') as f:
        content = f.read()
    
    print(f"File content length: {len(content)} characters")
    
    # Prepare request data (mimicking frontend)
    payload = {
        "report_text": content,
        "slides": 3,
        "use_cache": True,
        "request_id": f"test-upload-{int(time.time())}"
    }
    
    print("Sending request to backend...")
    print(f"Request ID: {payload['request_id']}")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            'http://localhost:8080/render',
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=600  # 10 minutes timeout
        )
        
        duration = time.time() - start_time
        print(f"Response received after {duration:.2f} seconds")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("SUCCESS!")
            print(f"Presentation URL: {result.get('url')}")
            print(f"Created slides: {result.get('created_slides')}")
        else:
            print("ERROR!")
            print(f"Response Text: {response.text}")
            
    except requests.exceptions.Timeout:
        print("Request timed out after 10 minutes")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_file_upload()