#!/usr/bin/env python3
"""
Comprehensive speaker notes test to identify actual issues
"""
import sys
import time
sys.path.append('src')

from agent.slides_google import _load_credentials, _slides_service, create_main_slide_with_content
from agent.notes_native_api import set_speaker_notes_native

def comprehensive_test():
    """Run comprehensive test of speaker notes functionality"""
    print("=== Comprehensive Speaker Notes Test ===")
    
    try:
        creds = _load_credentials()
        slides = _slides_service(creds)
        
        # Test 1: Create slide using main function (this is what the user experiences)
        print("\n🧪 Test 1: Full integration test (create_main_slide_with_content)")
        
        from agent.slides_google import create_presentation, delete_default_slide
        pres = create_presentation("Comprehensive Speaker Notes Test")
        pres_id = pres['presentationId']
        
        # Delete default slide
        default_id = delete_default_slide(pres_id)
        print(f"✓ Deleted default slide: {default_id}")
        
        slide_id = create_main_slide_with_content(
            pres_id,
            title="Integration Test Slide",
            subtitle="Testing speaker notes integration", 
            bullets=["Point 1: First point", "Point 2: Second point", "Point 3: Third point"],
            image_url=None,
            script="This is the speaker notes text that should appear in the Speaker Notes section, NOT as visible text on the slide."
        )
        
        print(f"✓ Created slide via integration: {slide_id}")
        
        # Test 2: Verify the slide structure after creation
        print("\n🔍 Test 2: Verify slide structure after integration test")
        
        pres_data = slides.presentations().get(presentationId=pres_id).execute()
        target_slide = None
        for slide in pres_data.get("slides", []):
            if slide.get("objectId") == slide_id:
                target_slide = slide
                break
                
        if target_slide:
            # Check for visible script boxes on the slide
            visible_script_boxes = []
            for element in target_slide.get("pageElements", []):
                if element.get("objectId", "").startswith("script_box"):
                    visible_script_boxes.append(element)
                elif "script" in element.get("objectId", "").lower():
                    visible_script_boxes.append(element)
            
            print(f"   📦 Visible script boxes found: {len(visible_script_boxes)}")
            if visible_script_boxes:
                print("   ❌ ISSUE: Found visible script boxes - speaker notes fell back to visible text")
                for box in visible_script_boxes:
                    print(f"      - Box ID: {box.get('objectId')}")
            else:
                print("   ✅ Good: No visible script boxes found")
            
            # Check speaker notes structure
            notes_page = target_slide.get("slideProperties", {}).get("notesPage", {})
            notes_props = notes_page.get("notesProperties", {})
            speaker_notes_id = notes_props.get("speakerNotesObjectId")
            
            print(f"   📝 Speaker notes shape ID: {speaker_notes_id}")
            
            if speaker_notes_id:
                # Try to get the actual text content
                for element in notes_page.get("pageElements", []):
                    if element.get("objectId") == speaker_notes_id:
                        shape = element.get("shape", {})
                        text_content = shape.get("text", {})
                        if text_content and text_content.get("textElements"):
                            text_runs = [elem.get("textRun", {}).get("content", "") 
                                        for elem in text_content.get("textElements", []) 
                                        if "textRun" in elem]
                            actual_text = "".join(text_runs).strip()
                            print(f"   📄 Speaker notes text: '{actual_text}'")
                            if actual_text:
                                print("   ✅ SUCCESS: Speaker notes text found in proper location")
                            else:
                                print("   ❌ ISSUE: Speaker notes shape exists but no text content")
                        else:
                            print("   ❌ ISSUE: Speaker notes shape exists but no text structure")
                        break
                else:
                    print("   ❌ ISSUE: Speaker notes shape ID found but no matching element")
            else:
                print("   ❌ ISSUE: No speaker notes shape ID found")
        
        # Test 3: Direct native API test
        print("\n🔧 Test 3: Direct native API test on new slide")
        
        # Create another slide for direct testing
        slide_id_2 = create_main_slide_with_content(
            pres_id,
            title="Direct API Test Slide",
            subtitle="Testing direct native API", 
            bullets=["Direct test point 1", "Direct test point 2"],
            image_url=None,
            script=None  # Don't set script via integration
        )
        
        # Now test direct native API
        direct_test_script = "Direct native API test - this text should be in speaker notes only."
        success = set_speaker_notes_native(slides, pres_id, slide_id_2, direct_test_script)
        
        print(f"   Native API result: {success}")
        
        if success:
            # Verify it was actually set correctly
            pres_data = slides.presentations().get(presentationId=pres_id).execute()
            for slide in pres_data.get("slides", []):
                if slide.get("objectId") == slide_id_2:
                    notes_page = slide.get("slideProperties", {}).get("notesPage", {})
                    speaker_notes_id = notes_page.get("notesProperties", {}).get("speakerNotesObjectId")
                    
                    if speaker_notes_id:
                        for element in notes_page.get("pageElements", []):
                            if element.get("objectId") == speaker_notes_id:
                                shape = element.get("shape", {})
                                text_content = shape.get("text", {})
                                if text_content:
                                    text_runs = [elem.get("textRun", {}).get("content", "") 
                                                for elem in text_content.get("textElements", []) 
                                                if "textRun" in elem]
                                    actual_text = "".join(text_runs).strip()
                                    if direct_test_script in actual_text:
                                        print("   ✅ SUCCESS: Direct native API correctly set speaker notes")
                                    else:
                                        print(f"   ❌ ISSUE: Text mismatch - expected: '{direct_test_script}', got: '{actual_text}'")
                                else:
                                    print("   ❌ ISSUE: Direct API success but no text content found")
                                break
                    break
        
        print(f"\n🔗 Test presentation URL: https://docs.google.com/presentation/d/{pres_id}/edit")
        print("👁️  MANUAL VERIFICATION STEPS:")
        print("   1. Open the presentation URL")
        print("   2. Click on slide 1 or slide 2")
        print("   3. Look at the bottom panel - click on 'Speaker notes' section")
        print("   4. Verify that speaker notes text appears THERE, not as visible text on slides")
        print("   5. If you see 'Presenter Script:' text boxes on slides, that indicates fallback behavior")
        
        return pres_id
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    comprehensive_test()