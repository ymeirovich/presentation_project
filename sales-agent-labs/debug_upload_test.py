#!/usr/bin/env python3
"""
Debug script to test file upload and presentation generation flow.
This will help isolate where the HTTP 500 error is occurring.
"""

import requests
import json
import time
import sys
from pathlib import Path


def test_upload_and_render(base_url="http://localhost:8080", test_file_path=None):
    """Test the complete upload -> render flow with detailed error reporting."""
    
    print(f"🔍 Testing upload and render flow against {base_url}")
    print("=" * 60)
    
    # Step 1: Test server health
    print("1. Testing server health...")
    try:
        response = requests.get(f"{base_url}/healthz", timeout=10)
        if response.status_code == 200:
            print("   ✅ Server is healthy")
        else:
            print(f"   ❌ Server unhealthy: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot reach server: {e}")
        return False
    
    # Step 2: Upload test file (if provided)
    dataset_id = None
    if test_file_path:
        print(f"2. Uploading test file: {test_file_path}")
        try:
            with open(test_file_path, 'rb') as f:
                files = {'file': (Path(test_file_path).name, f, 'application/octet-stream')}
                response = requests.post(f"{base_url}/data/upload", files=files, timeout=30)
                
            print(f"   Upload response status: {response.status_code}")
            print(f"   Upload response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                upload_result = response.json()
                dataset_id = upload_result.get('dataset_id')
                print(f"   ✅ Upload successful: {dataset_id}")
                print(f"   Sheets: {upload_result.get('sheets', [])}")
            else:
                print(f"   ❌ Upload failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Upload exception: {e}")
            return False
    else:
        print("2. Skipping file upload (no test file provided)")
    
    # Step 3: Test presentation generation
    print("3. Testing presentation generation...")
    
    # Test with simple text-based presentation
    render_request = {
        "report_text": "This is a test report for debugging purposes. It should generate a simple presentation to test the system.",
        "slides": 2,
        "use_cache": False,  # Force fresh generation
        "request_id": f"debug-test-{int(time.time())}"
    }
    
    print(f"   Request payload: {json.dumps(render_request, indent=2)}")
    
    try:
        response = requests.post(
            f"{base_url}/render", 
            json=render_request,
            timeout=180,  # 3 minute timeout
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Render response status: {response.status_code}")
        print(f"   Render response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Render successful!")
            print(f"   URL: {result.get('url')}")
            print(f"   Presentation ID: {result.get('presentation_id')}")
            print(f"   Created slides: {result.get('created_slides')}")
            return True
        else:
            print(f"   ❌ Render failed: {response.status_code}")
            print(f"   Error response: {response.text}")
            
            # Try to parse error details
            try:
                error_json = response.json()
                print(f"   Error details: {json.dumps(error_json, indent=2)}")
            except:
                pass
                
            return False
            
    except requests.exceptions.Timeout:
        print("   ❌ Request timed out after 3 minutes")
        return False
    except Exception as e:
        print(f"   ❌ Request exception: {e}")
        return False
    
    # Step 4: If we have a dataset, test data-based presentation
    if dataset_id:
        print("4. Testing data-based presentation...")
        data_ask_request = {
            "dataset_id": dataset_id,
            "questions": ["What are the key trends in this data?"],
            "report_text": "Data analysis results",
            "slides": 1,
            "use_cache": False
        }
        
        try:
            response = requests.post(
                f"{base_url}/data/ask",
                json=data_ask_request,
                timeout=180,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Data ask response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Data presentation successful!")
                print(f"   URL: {result.get('url')}")
            else:
                print(f"   ❌ Data presentation failed: {response.status_code}")
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Data ask exception: {e}")
    else:
        print("4. Skipping data-based presentation (no dataset)")


def main():
    """Main function to run the debug test."""
    if len(sys.argv) > 1:
        test_file_path = sys.argv[1]
        if not Path(test_file_path).exists():
            print(f"❌ Test file does not exist: {test_file_path}")
            sys.exit(1)
    else:
        test_file_path = None
        print("ℹ️  No test file provided, will only test basic presentation generation")
        print("   Usage: python debug_upload_test.py [test_file.xlsx]")
    
    # Run the test
    success = test_upload_and_render(test_file_path=test_file_path)
    
    print("=" * 60)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed - check the logs above for details")
        print("💡 Tips for debugging:")
        print("   1. Check server logs for detailed error information")
        print("   2. Ensure all required environment variables are set")
        print("   3. Verify Google Cloud authentication is working")
        print("   4. Check that the MCP server is starting correctly")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()