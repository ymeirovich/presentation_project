#!/usr/bin/env python3
"""
Debug script to understand why speaker notes are failing
"""
import os
import sys
sys.path.append('src')

from agent.slides_google import _load_credentials, _slides_service
from agent.notes_native_api import set_speaker_notes_native
import json
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

def debug_presentation_structure():
    """Create a test presentation and debug its structure"""
    try:
        creds = _load_credentials()
        slides = _slides_service(creds)
        
        # Create test presentation
        pres = slides.presentations().create(body={"title": "Speaker Notes Debug Test"}).execute()
        pres_id = pres.get("presentationId")
        log.info(f"Created test presentation: {pres_id}")
        
        # Get the default slide
        full_pres = slides.presentations().get(presentationId=pres_id).execute()
        first_slide = full_pres.get("slides", [])[0]
        slide_id = first_slide.get("objectId")
        log.info(f"First slide ID: {slide_id}")
        
        # Debug: Show the full slide structure
        log.info("=== FULL SLIDE STRUCTURE ===")
        log.info(json.dumps(first_slide, indent=2))
        
        # Now try to get notes page details
        log.info("=== NOTES PAGE ANALYSIS ===")
        notes_page = first_slide.get("notesPage", {})
        log.info(f"Notes page exists: {bool(notes_page)}")
        log.info(f"Notes page ID: {notes_page.get('objectId')}")
        
        notes_props = notes_page.get("notesProperties", {})
        log.info(f"Notes properties: {json.dumps(notes_props, indent=2)}")
        
        page_elements = notes_page.get("pageElements", [])
        log.info(f"Page elements count: {len(page_elements)}")
        for i, elem in enumerate(page_elements):
            log.info(f"Element {i}: {json.dumps(elem, indent=2)}")
        
        # Test our native implementation
        log.info("=== TESTING NATIVE IMPLEMENTATION ===")
        test_script = "This is a test speaker note from debug script."
        success = set_speaker_notes_native(slides, pres_id, slide_id, test_script)
        log.info(f"Native implementation success: {success}")
        
        # Check the result
        log.info("=== POST-TEST STRUCTURE ===")
        updated_pres = slides.presentations().get(presentationId=pres_id).execute()
        updated_slide = None
        for slide in updated_pres.get("slides", []):
            if slide.get("objectId") == slide_id:
                updated_slide = slide
                break
                
        if updated_slide:
            slide_props = updated_slide.get("slideProperties", {})
            updated_notes = slide_props.get("notesPage", {})
            log.info(f"Updated notes page: {json.dumps(updated_notes, indent=2)}")
            
            # Check if our text was actually inserted
            for element in updated_notes.get("pageElements", []):
                if element.get("objectId") == "i3":  # The speaker notes element
                    shape = element.get("shape", {})
                    text_content = shape.get("text", {})
                    if text_content:
                        log.info("✅ SPEAKER NOTES TEXT FOUND!")
                        log.info(f"Text content: {json.dumps(text_content, indent=2)}")
                    else:
                        log.warning("⚠️  Speaker notes shape found but no text content")
                    break
        
        log.info(f"Presentation URL: https://docs.google.com/presentation/d/{pres_id}/edit")
        return pres_id, slide_id
        
    except Exception as e:
        log.error(f"Debug failed: {e}", exc_info=True)
        return None, None

if __name__ == "__main__":
    debug_presentation_structure()