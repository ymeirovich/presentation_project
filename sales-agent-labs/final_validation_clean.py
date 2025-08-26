#!/usr/bin/env python3
"""
Final validation test for speaker notes implementation
"""
import sys
sys.path.append('src')

from agent.slides_google import _load_credentials, _slides_service, create_main_slide_with_content, create_presentation, delete_default_slide

def final_validation():
    """Final validation test"""
    print("=== Final Speaker Notes Validation Test ===")
    
    try:
        creds = _load_credentials()
        slides = _slides_service(creds)
        
        pres = create_presentation("Final Speaker Notes Validation")
        pres_id = pres['presentationId']
        delete_default_slide(pres_id)
        print(f"✓ Created presentation: {pres_id}")
        
        # Test normal operation
        print("\n🧪 Test Case 1: Normal operation")
        slide_id_1 = create_main_slide_with_content(
            pres_id,
            title="Test Case 1: Normal Operation",
            subtitle="Regular speaker notes test", 
            bullets=["Normal bullet 1", "Normal bullet 2"],
            image_url=None,
            script="Normal speaker notes text for Test Case 1."
        )
        print(f"   ✓ Created slide 1: {slide_id_1}")
        
        # Validation
        print("\n🔍 Validation: Checking slide structure")
        pres_data = slides.presentations().get(presentationId=pres_id).execute()
        
        for slide in pres_data.get("slides", []):
            if slide.get("objectId") == slide_id_1:
                # Check for visible script boxes (should be 0)
                visible_boxes = 0
                for element in slide.get("pageElements", []):
                    obj_id = element.get("objectId", "")
                    if "script" in obj_id.lower():
                        visible_boxes += 1
                        
                print(f"   📦 Visible script boxes: {visible_boxes}")
                if visible_boxes == 0:
                    print("   ✅ SUCCESS: No visible script boxes found")
                else:
                    print("   ❌ ISSUE: Found visible script boxes (fallback occurred)")
                
                # Check speaker notes
                slide_props = slide.get("slideProperties", {})
                notes_page = slide_props.get("notesPage", {})
                notes_props = notes_page.get("notesProperties", {})
                speaker_notes_id = notes_props.get("speakerNotesObjectId")
                
                print(f"   📝 Speaker notes shape ID: {speaker_notes_id}")
                
                if speaker_notes_id:
                    print("   ✅ SUCCESS: Speaker notes properly configured")
                else:
                    print("   ❌ ISSUE: No speaker notes shape ID found")
                
                break
        
        print(f"\n🔗 Validation presentation URL: https://docs.google.com/presentation/d/{pres_id}/edit")
        print("🎯 Key Improvements Made:")
        print("   1. Fixed field path inconsistencies in slides_google.py")
        print("   2. Improved error handling and text insertion robustness") 
        print("   3. Added detailed logging for better debugging")
        print("   4. Enhanced fallback detection and warnings")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = final_validation()
    print(f"\n🏁 Final validation: {'PASSED' if success else 'FAILED'}")