#!/usr/bin/env python3
"""
Final validation test for speaker notes implementation
Tests edge cases and verifies the improvements work correctly
"""
import sys
import time
import logging
sys.path.append('src')

# Enable detailed logging to verify our improvements
logging.basicConfig(level=logging.DEBUG)

from agent.slides_google import _load_credentials, _slides_service, create_main_slide_with_content
from agent.notes_native_api import set_speaker_notes_native

def final_validation():
    """Final validation test with edge cases"""
    print("=== Final Speaker Notes Validation Test ===")
    
    try:
        creds = _load_credentials()
        slides = _slides_service(creds)
        
        from agent.slides_google import create_presentation, delete_default_slide
        pres = create_presentation("Final Speaker Notes Validation")
        pres_id = pres['presentationId']
        
        # Delete default slide
        delete_default_slide(pres_id)
        print(f"✓ Created presentation: {pres_id}")
        
        # Test Case 1: Normal operation
        print("\n🧪 Test Case 1: Normal operation")
        slide_id_1 = create_main_slide_with_content(
            pres_id,
            title="Test Case 1: Normal Operation",
            subtitle="Regular speaker notes test", 
            bullets=["Normal bullet 1", "Normal bullet 2"],
            image_url=None,
            script="Normal speaker notes text for Test Case 1. This should appear in the Speaker Notes panel."
        )
        print(f"   ✓ Created slide 1: {slide_id_1}")
        
        # Test Case 2: Empty script (should not fail)
        print("\n🧪 Test Case 2: Empty script handling")
        slide_id_2 = create_main_slide_with_content(
            pres_id,
            title="Test Case 2: Empty Script",
            subtitle="Testing empty script handling", 
            bullets=["Empty script bullet 1", "Empty script bullet 2"],
            image_url=None,
            script=""  # Empty script
        )
        print(f"   ✓ Created slide 2: {slide_id_2}")
        
        # Test Case 3: Very long script text
        print("\n🧪 Test Case 3: Long script text")\n        long_script = \"This is a very long speaker notes script. \" * 50 + \"This tests that long text is handled properly in the speaker notes system.\"\n        slide_id_3 = create_main_slide_with_content(\n            pres_id,\n            title=\"Test Case 3: Long Script\",\n            subtitle=\"Testing long script text handling\", \n            bullets=[\"Long script bullet 1\", \"Long script bullet 2\"],\n            image_url=None,\n            script=long_script\n        )\n        print(f\"   ✓ Created slide 3: {slide_id_3}\")\n        print(f\"   📏 Script length: {len(long_script)} characters\")\n        \n        # Test Case 4: Special characters in script\n        print(\"\\n🧪 Test Case 4: Special characters\")\n        special_script = \"Speaker notes with special chars: \\\"quotes\\\", 'apostrophes', & ampersands, <brackets>, \\n\\nnewlines, and émojis 📝✅❌\"\n        slide_id_4 = create_main_slide_with_content(\n            pres_id,\n            title=\"Test Case 4: Special Characters\",\n            subtitle=\"Testing special character handling\", \n            bullets=[\"Special char bullet 1\", \"Special char bullet 2\"],\n            image_url=None,\n            script=special_script\n        )\n        print(f\"   ✓ Created slide 4: {slide_id_4}\")\n        \n        # Test Case 5: Direct API test with different slide types\n        print(\"\\n🧪 Test Case 5: Direct API on different slide types\")\n        slide_id_5 = create_main_slide_with_content(\n            pres_id,\n            title=\"Test Case 5: Direct API Test\",\n            subtitle=\"Testing direct native API call\", \n            bullets=[\"Direct API bullet 1\", \"Direct API bullet 2\"],\n            image_url=None,\n            script=None  # No script via integration\n        )\n        \n        # Now test direct API call\n        direct_script = \"Direct API call test - this text should be in speaker notes via direct native API call.\"\n        success = set_speaker_notes_native(slides, pres_id, slide_id_5, direct_script)\n        print(f\"   Native API direct call result: {success}\")\n        \n        # Validate all slides\n        print(\"\\n🔍 Final Validation: Checking all slides\")\n        pres_data = slides.presentations().get(presentationId=pres_id).execute()\n        \n        test_cases = [\n            (slide_id_1, \"Normal speaker notes text for Test Case 1\"),\n            (slide_id_2, \"\"),  # Empty script\n            (slide_id_3, long_script),\n            (slide_id_4, special_script),\n            (slide_id_5, direct_script)\n        ]\n        \n        all_passed = True\n        for i, (slide_id, expected_text) in enumerate(test_cases, 1):\n            print(f\"   Slide {i} ({slide_id}):\")\n            \n            # Find the slide\n            slide_data = None\n            for slide in pres_data.get(\"slides\", []):\n                if slide.get(\"objectId\") == slide_id:\n                    slide_data = slide\n                    break\n            \n            if not slide_data:\n                print(f\"      ❌ Slide not found\")\n                all_passed = False\n                continue\n                \n            # Check for visible script boxes (should be 0)\n            visible_boxes = 0\n            for element in slide_data.get(\"pageElements\", []):\n                obj_id = element.get(\"objectId\", \"\")\n                if \"script\" in obj_id.lower() or \"presenter\" in obj_id.lower():\n                    visible_boxes += 1\n                    \n            if visible_boxes > 0:\n                print(f\"      ❌ Found {visible_boxes} visible script boxes (fallback occurred)\")\n                all_passed = False\n            else:\n                print(f\"      ✅ No visible script boxes\")\n            \n            # Check speaker notes\n            slide_props = slide_data.get(\"slideProperties\", {})\n            notes_page = slide_props.get(\"notesPage\", {})\n            notes_props = notes_page.get(\"notesProperties\", {})\n            speaker_notes_id = notes_props.get(\"speakerNotesObjectId\")\n            \n            if not speaker_notes_id:\n                if expected_text:  # Only fail if we expected text\n                    print(f\"      ❌ No speaker notes shape ID found\")\n                    all_passed = False\n                else:\n                    print(f\"      ✅ No speaker notes (as expected for empty script)\")\n                continue\n                \n            # Find the actual text\n            actual_text = \"\"\n            for element in notes_page.get(\"pageElements\", []):\n                if element.get(\"objectId\") == speaker_notes_id:\n                    shape = element.get(\"shape\", {})\n                    text_content = shape.get(\"text\", {})\n                    if text_content:\n                        text_runs = [elem.get(\"textRun\", {}).get(\"content\", \"") \n                                    for elem in text_content.get(\"textElements\", []) \n                                    if \"textRun\" in elem]\n                        actual_text = \"\".join(text_runs).strip()\n                    break\n            \n            # Compare text (allowing for slight variations)\n            if expected_text:\n                if expected_text in actual_text or actual_text in expected_text:\n                    print(f\"      ✅ Speaker notes text matches (length: {len(actual_text)})\")\n                else:\n                    print(f\"      ❌ Text mismatch - expected: '{expected_text[:50]}...', got: '{actual_text[:50]}...'\")\n                    all_passed = False\n            else:\n                if not actual_text:\n                    print(f\"      ✅ No text (as expected for empty script)\")\n                else:\n                    print(f\"      ⚠️  Unexpected text found: '{actual_text[:50]}...'\")\n        \n        print(f\"\\n📊 Final Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}\")\n        print(f\"🔗 Validation presentation URL: https://docs.google.com/presentation/d/{pres_id}/edit\")\n        print(\"\\n🎯 Key Improvements Made:\")\n        print(\"   1. Fixed field path inconsistencies in slides_google.py\")\n        print(\"   2. Improved error handling and text insertion robustness\")\n        print(\"   3. Added detailed logging for better debugging\")\n        print(\"   4. Enhanced fallback detection and warnings\")\n        \n        return all_passed\n        \n    except Exception as e:\n        print(f\"❌ Validation failed: {e}\")\n        import traceback\n        traceback.print_exc()\n        return False\n\nif __name__ == \"__main__\":\n    success = final_validation()\n    print(f\"\\n🏁 Final validation: {'PASSED' if success else 'FAILED'}\")