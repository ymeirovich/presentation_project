#!/usr/bin/env python3
"""
Test script for speaker notes implementation
Tests both Apps Script and native API approaches
"""
import os
import sys
import time
from src.agent.slides_google import _load_credentials, _slides_service, create_presentation

def test_speaker_notes():
    """Test speaker notes with a real presentation"""
    print("=== Speaker Notes Implementation Test ===")
    
    try:
        # Load credentials and create test presentation
        creds = _load_credentials()
        slides = _slides_service(creds)
        
        print("✓ Credentials loaded")
        print("✓ Scopes:", getattr(creds, 'scopes', []))
        
        # Create test presentation
        test_pres = create_presentation("Speaker Notes Test - " + str(int(time.time())))
        pres_id = test_pres['presentationId']
        print(f"✓ Test presentation created: {pres_id}")
        
        # Get the default slide ID 
        pres_data = slides.presentations().get(presentationId=pres_id).execute()
        slide_id = pres_data['slides'][0]['objectId']
        print(f"✓ Using slide ID: {slide_id}")
        
        # Test enhanced native API
        print("\n--- Testing Enhanced Native API ---")
        try:
            from src.agent.notes_native_api import set_speaker_notes_native
            
            test_notes = f"Test speaker notes via Enhanced Native API - {time.time()}"
            success = set_speaker_notes_native(slides, pres_id, slide_id, test_notes)
            
            if success:
                print("✅ Enhanced Native API: SUCCESS")
            else:
                print("❌ Enhanced Native API: FAILED")
                
        except Exception as e:
            print(f"❌ Enhanced Native API: ERROR - {e}")
        
        # Test Apps Script (if configured)
        print("\n--- Testing Apps Script API ---")
        script_id = os.getenv("APPS_SCRIPT_SCRIPT_ID", "").strip()
        
        if not script_id:
            print("⚠️  Apps Script: SKIPPED (APPS_SCRIPT_SCRIPT_ID not set)")
        else:
            try:
                from src.agent.notes_apps_script import set_speaker_notes_via_script
                
                test_notes = f"Test speaker notes via Apps Script - {time.time()}"
                success = set_speaker_notes_via_script(
                    creds, script_id, pres_id, slide_id, test_notes
                )
                
                if success:
                    print("✅ Apps Script API: SUCCESS")
                else:
                    print("❌ Apps Script API: FAILED (likely scope issue)")
                    
            except Exception as e:
                print(f"❌ Apps Script API: ERROR - {e}")
        
        # Test integrated approach
        print("\n--- Testing Integrated Approach ---")
        try:
            from src.agent.slides_google import create_main_slide_with_content
            
            slide_id = create_main_slide_with_content(
                pres_id,
                title="Test Slide",
                subtitle="Integration Test", 
                bullets=["Point 1", "Point 2", "Point 3"],
                image_url=None,
                script=f"Integrated test speaker notes - {time.time()}"
            )
            
            print(f"✅ Integrated approach: SUCCESS (slide: {slide_id})")
            
        except Exception as e:
            print(f"❌ Integrated approach: ERROR - {e}")
        
        # Provide presentation URL for manual verification
        pres_url = f"https://docs.google.com/presentation/d/{pres_id}/edit"
        print(f"\n🔗 Test presentation URL: {pres_url}")
        print("👀 Manually verify speaker notes were added correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_speaker_notes()
    sys.exit(0 if success else 1)