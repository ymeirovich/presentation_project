#!/usr/bin/env python3
"""
Test script to verify correct field paths for speaker notes
"""
import sys
sys.path.append('src')

from agent.slides_google import _load_credentials, _slides_service, create_presentation

def test_field_paths():
    """Test different field paths for speaker notes"""
    print("=== Testing Field Paths for Speaker Notes ===")
    
    try:
        creds = _load_credentials()
        slides = _slides_service(creds)
        
        # Create test presentation
        test_pres = create_presentation("Field Path Test")
        pres_id = test_pres['presentationId']
        print(f"✓ Test presentation created: {pres_id}")
        
        # Test Path 1: slideProperties/notesPage/... (current incorrect path)
        print("\n--- Testing Path 1: slideProperties/notesPage/... ---")
        try:
            pres = slides.presentations().get(
                presentationId=pres_id,
                fields="slides(objectId,slideProperties/notesPage/notesProperties/speakerNotesObjectId)"
            ).execute()
            
            slide = pres.get("slides", [])[0]
            slide_props = slide.get("slideProperties", {})
            notes_page = slide_props.get("notesPage", {})
            notes_props = notes_page.get("notesProperties", {})
            speaker_notes_id = notes_props.get("speakerNotesObjectId")
            
            print(f"   slideProperties exists: {bool(slide_props)}")
            print(f"   notesPage under slideProperties: {bool(notes_page)}")
            print(f"   speakerNotesObjectId: {speaker_notes_id}")
            
        except Exception as e:
            print(f"   ERROR: {e}")
        
        # Test Path 2: Direct notesPage/... (potentially correct path)
        print("\n--- Testing Path 2: Direct notesPage/... ---")
        try:
            pres = slides.presentations().get(
                presentationId=pres_id,
                fields="slides(objectId,notesPage/notesProperties/speakerNotesObjectId)"
            ).execute()
            
            slide = pres.get("slides", [])[0]
            notes_page = slide.get("notesPage", {})
            notes_props = notes_page.get("notesProperties", {})
            speaker_notes_id = notes_props.get("speakerNotesObjectId")
            
            print(f"   notesPage directly: {bool(notes_page)}")
            print(f"   notesProperties: {bool(notes_props)}")
            print(f"   speakerNotesObjectId: {speaker_notes_id}")
            
        except Exception as e:
            print(f"   ERROR: {e}")
        
        # Test Path 3: Get all data and inspect structure
        print("\n--- Testing Path 3: Full structure inspection ---")
        try:
            pres = slides.presentations().get(presentationId=pres_id).execute()
            slide = pres.get("slides", [])[0]
            
            print(f"   Keys in slide: {list(slide.keys())}")
            if 'slideProperties' in slide:
                print(f"   Keys in slideProperties: {list(slide['slideProperties'].keys())}")
            if 'notesPage' in slide:
                print(f"   Keys in notesPage: {list(slide['notesPage'].keys())}")
                if 'notesProperties' in slide['notesPage']:
                    print(f"   Keys in notesProperties: {list(slide['notesPage']['notesProperties'].keys())}")
            
        except Exception as e:
            print(f"   ERROR: {e}")
            
        print(f"\n🔗 Test presentation URL: https://docs.google.com/presentation/d/{pres_id}/edit")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_field_paths()