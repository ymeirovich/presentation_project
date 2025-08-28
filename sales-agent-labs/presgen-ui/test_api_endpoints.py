#!/usr/bin/env python3
"""
Test script for the enhanced PresGen-Data API endpoints
"""

import requests
import json

# Test the upload-report endpoint
def test_upload_report():
    print("Testing /api/presgen-data/upload-report endpoint...")
    
    # Test with a valid text file
    with open('test_report_context.txt', 'rb') as f:
        files = {'report_file': ('test_report.txt', f, 'text/plain')}
        response = requests.post('http://localhost:3002/api/presgen-data/upload-report', files=files)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        return response.json().get('report_id')
    return None

# Test the generate-mvp endpoint with text context
def test_generate_with_text():
    print("\nTesting /api/presgen-data/generate-mvp endpoint with text context...")
    
    request_data = {
        "dataset_id": "test-dataset-123",
        "sheet_name": "Sheet1", 
        "has_headers": True,
        "questions": [
            "What are the top performing products?",
            "How did revenue trend over time?"
        ],
        "report_text": "Q4 2024 Sales Report\n\nTotal revenue: $2.4M (up 24% from Q4 2023)\nSoftware Solutions led with $1.2M revenue.",
        "presentation_title": "Q4 2024 Sales Analysis",
        "slide_count": 5,
        "chart_style": "modern",
        "include_images": True,
        "speaker_notes": True,
        "template_style": "corporate"
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post('http://localhost:3002/api/presgen-data/generate-mvp', 
                           json=request_data, headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

# Test the generate-mvp endpoint with report ID
def test_generate_with_report_id(report_id):
    if not report_id:
        print("Skipping report ID test - no report ID available")
        return
        
    print(f"\nTesting /api/presgen-data/generate-mvp endpoint with report_id: {report_id}...")
    
    request_data = {
        "dataset_id": "test-dataset-123",
        "sheet_name": "Sheet1",
        "has_headers": True,
        "questions": [
            "What are the key performance metrics?",
            "What are the main challenges identified?"
        ],
        "report_id": report_id,
        "presentation_title": "Q4 2024 Performance Review",
        "slide_count": 7,
        "chart_style": "classic",
        "include_images": False,
        "speaker_notes": True,
        "template_style": "minimal"
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post('http://localhost:3002/api/presgen-data/generate-mvp', 
                           json=request_data, headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

# Test validation errors
def test_validation_errors():
    print("\nTesting validation errors...")
    
    # Test missing required fields
    request_data = {
        "dataset_id": "",  # Empty dataset_id
        "questions": [],   # Empty questions
        "presentation_title": "",  # Empty title
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post('http://localhost:3002/api/presgen-data/generate-mvp', 
                           json=request_data, headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    try:
        # Test file upload
        report_id = test_upload_report()
        
        # Test generation with text
        test_generate_with_text()
        
        # Test generation with report ID
        test_generate_with_report_id(report_id)
        
        # Test validation errors
        test_validation_errors()
        
    except Exception as e:
        print(f"Test failed with error: {e}")