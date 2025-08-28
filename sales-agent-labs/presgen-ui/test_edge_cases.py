#!/usr/bin/env python3
"""
Test edge cases and error handling for PresGen-Data API endpoints
"""

import requests
import json
import tempfile
import os

def test_upload_edge_cases():
    print("Testing upload edge cases...")
    
    # Test 1: No file provided
    print("\n1. Testing upload with no file...")
    response = requests.post('http://localhost:3002/api/presgen-data/upload-report')
    print(f"Status: {response.status_code} (expected: 400)")
    print(f"Response: {response.json()}")
    
    # Test 2: Empty file
    print("\n2. Testing upload with empty file...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("")  # Empty file
        empty_file = f.name
    
    try:
        with open(empty_file, 'rb') as f:
            files = {'report_file': ('empty.txt', f, 'text/plain')}
            response = requests.post('http://localhost:3002/api/presgen-data/upload-report', files=files)
        
        print(f"Status: {response.status_code} (expected: 400)")
        print(f"Response: {response.json()}")
    finally:
        os.unlink(empty_file)
    
    # Test 3: File too large (simulate)
    print("\n3. Testing upload with very small content (should work)...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Hi")  # Very small file
        small_file = f.name
    
    try:
        with open(small_file, 'rb') as f:
            files = {'report_file': ('tiny.txt', f, 'text/plain')}
            response = requests.post('http://localhost:3002/api/presgen-data/upload-report', files=files)
        
        print(f"Status: {response.status_code} (expected: 400 - too small)")
        print(f"Response: {response.json()}")
    finally:
        os.unlink(small_file)
    
    # Test 4: Wrong file type (PDF)
    print("\n4. Testing upload with PDF file...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
        f.write("This is not actually a PDF, just has .pdf extension")
        pdf_file = f.name
    
    try:
        with open(pdf_file, 'rb') as f:
            files = {'report_file': ('document.pdf', f, 'application/pdf')}
            response = requests.post('http://localhost:3002/api/presgen-data/upload-report', files=files)
        
        print(f"Status: {response.status_code} (expected: 400)")
        print(f"Response: {response.json()}")
    finally:
        os.unlink(pdf_file)

def test_generate_edge_cases():
    print("\n\nTesting generate endpoint edge cases...")
    
    # Test 1: Missing both report_text and report_id
    print("\n1. Testing with neither report_text nor report_id...")
    request_data = {
        "dataset_id": "test-123",
        "sheet_name": "Sheet1",
        "has_headers": True,
        "questions": ["What is the revenue?"],
        "presentation_title": "Test Presentation",
        "slide_count": 5,
        "chart_style": "modern",
        "include_images": True,
        "speaker_notes": True,
        "template_style": "corporate"
    }
    
    headers = {'Content-Type': 'application/json'}
    response = requests.post('http://localhost:3002/api/presgen-data/generate-mvp', 
                           json=request_data, headers=headers)
    
    print(f"Status: {response.status_code} (expected: 400)")
    print(f"Response: {response.json()}")
    
    # Test 2: Invalid slide_count
    print("\n2. Testing with invalid slide_count...")
    request_data = {
        "dataset_id": "test-123",
        "sheet_name": "Sheet1",
        "has_headers": True,
        "questions": ["What is the revenue?"],
        "report_text": "Some report text",
        "presentation_title": "Test Presentation",
        "slide_count": 25,  # Too high
        "chart_style": "modern",
        "include_images": True,
        "speaker_notes": True,
        "template_style": "corporate"
    }
    
    response = requests.post('http://localhost:3002/api/presgen-data/generate-mvp', 
                           json=request_data, headers=headers)
    
    print(f"Status: {response.status_code} (expected: 400)")
    print(f"Response: {response.json()}")
    
    # Test 3: Invalid chart_style
    print("\n3. Testing with invalid chart_style...")
    request_data = {
        "dataset_id": "test-123",
        "sheet_name": "Sheet1",
        "has_headers": True,
        "questions": ["What is the revenue?"],
        "report_text": "Some report text",
        "presentation_title": "Test Presentation",
        "slide_count": 5,
        "chart_style": "fancy",  # Invalid style
        "include_images": True,
        "speaker_notes": True,
        "template_style": "corporate"
    }
    
    response = requests.post('http://localhost:3002/api/presgen-data/generate-mvp', 
                           json=request_data, headers=headers)
    
    print(f"Status: {response.status_code} (expected: 400)")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    try:
        test_upload_edge_cases()
        test_generate_edge_cases()
        print("\n✅ All edge case tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")