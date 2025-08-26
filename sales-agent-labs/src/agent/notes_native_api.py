# src/agent/notes_native_api.py
"""
Robust native Google Slides API implementation for speaker notes
Provides reliable alternative to Apps Script approach
"""
from __future__ import annotations
import logging
import time
from typing import Optional
from googleapiclient.errors import HttpError

log = logging.getLogger("agent.notes_native")


def set_speaker_notes_native(
    slides_service,
    presentation_id: str,
    slide_object_id: str,
    notes_text: str,
    max_retries: int = 3
) -> bool:
    """
    Set speaker notes using native Slides API with multiple fallback strategies.
    
    Strategy priorities:
    1. Use existing speakerNotesObjectId (fastest)
    2. Scan pageElements for TEXT_BOX (fallback)
    3. Create new notes text box (last resort)
    4. Add visible script box on slide (guaranteed fallback)
    
    Args:
        slides_service: Authorized Slides API service
        presentation_id: Google Slides presentation ID
        slide_object_id: Target slide objectId
        notes_text: Speaker notes content
        max_retries: Maximum retry attempts
        
    Returns:
        bool: True if notes were set successfully, False otherwise
    """
    for attempt in range(max_retries):
        try:
            # Strategy 1: Use official speakerNotesObjectId
            notes_shape_id = _get_official_notes_shape_id(
                slides_service, presentation_id, slide_object_id
            )
            
            if notes_shape_id:
                if _insert_notes_text(slides_service, presentation_id, notes_shape_id, notes_text):
                    log.info("Speaker notes set via official shape ID: %s", notes_shape_id)
                    return True
            
            # Strategy 2: Scan for existing TEXT_BOX in notes page
            notes_shape_id = _find_notes_textbox(
                slides_service, presentation_id, slide_object_id
            )
            
            if notes_shape_id:
                if _insert_notes_text(slides_service, presentation_id, notes_shape_id, notes_text):
                    log.info("Speaker notes set via existing TEXT_BOX: %s", notes_shape_id)
                    return True
            
            # Strategy 3: Create new notes text box
            notes_shape_id = _create_notes_textbox(
                slides_service, presentation_id, slide_object_id
            )
            
            if notes_shape_id:
                if _insert_notes_text(slides_service, presentation_id, notes_shape_id, notes_text):
                    log.info("Speaker notes set via new TEXT_BOX: %s", notes_shape_id)
                    return True
            
            log.warning(f"All notes strategies failed on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                
        except HttpError as e:
            log.warning(f"HTTP error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            
        except Exception as e:
            log.error(f"Unexpected error setting notes: {e}")
            break
    
    # Strategy 4: Fallback to visible script box on slide
    log.warning("All notes strategies failed, using visible script box fallback")
    return _add_visible_script_box(slides_service, presentation_id, slide_object_id, notes_text)


def _get_official_notes_shape_id(
    slides_service, presentation_id: str, slide_object_id: str
) -> Optional[str]:
    """Get the official speakerNotesObjectId from slide metadata."""
    try:
        pres = slides_service.presentations().get(
            presentationId=presentation_id,
            fields="slides(objectId,slideProperties/notesPage/notesProperties/speakerNotesObjectId)"
        ).execute()
        
        for slide in pres.get("slides", []):
            if slide.get("objectId") == slide_object_id:
                slide_props = slide.get("slideProperties", {})
                notes_page = slide_props.get("notesPage", {})
                notes_props = notes_page.get("notesProperties", {})
                speaker_notes_id = notes_props.get("speakerNotesObjectId")
                if speaker_notes_id:
                    log.debug(f"Found speaker notes object ID: {speaker_notes_id}")
                    return speaker_notes_id
                
    except HttpError as e:
        log.debug(f"Could not get official notes shape ID: {e}")
    
    return None


def _find_notes_textbox(
    slides_service, presentation_id: str, slide_object_id: str
) -> Optional[str]:
    """Find existing TEXT_BOX elements in the slide's notes page."""
    try:
        pres = slides_service.presentations().get(
            presentationId=presentation_id,
            fields="slides(objectId,slideProperties/notesPage/pageElements(objectId,shape/shapeType))"
        ).execute()
        
        for slide in pres.get("slides", []):
            if slide.get("objectId") == slide_object_id:
                slide_props = slide.get("slideProperties", {})
                notes_page = slide_props.get("notesPage", {})
                for element in notes_page.get("pageElements", []):
                    shape = element.get("shape", {})
                    if shape.get("shapeType") == "TEXT_BOX":
                        element_id = element.get("objectId")
                        log.debug(f"Found notes TEXT_BOX: {element_id}")
                        return element_id
                        
    except HttpError as e:
        log.debug(f"Could not find existing notes TEXT_BOX: {e}")
    
    return None


def _create_notes_textbox(
    slides_service, presentation_id: str, slide_object_id: str
) -> Optional[str]:
    """Create a new TEXT_BOX on the slide's notes page."""
    try:
        # First get the notes page ID
        pres = slides_service.presentations().get(
            presentationId=presentation_id,
            fields="slides(objectId,slideProperties/notesPage/objectId)"
        ).execute()
        
        notes_page_id = None
        for slide in pres.get("slides", []):
            if slide.get("objectId") == slide_object_id:
                slide_props = slide.get("slideProperties", {})
                notes_page = slide_props.get("notesPage", {})
                notes_page_id = notes_page.get("objectId")
                break
        
        if not notes_page_id:
            log.debug(f"No notes page ID found for slide {slide_object_id}")
            return None
        
        # Generate unique ID for new text box
        import uuid
        textbox_id = f"notes_textbox_{uuid.uuid4().hex[:8]}"
        
        # Create the text box
        requests = [{
            "createShape": {
                "objectId": textbox_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": notes_page_id,
                    "size": {
                        "width": {"magnitude": 8000000, "unit": "EMU"},  # ~8.75 inches
                        "height": {"magnitude": 2000000, "unit": "EMU"}  # ~2.2 inches
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 400000,  # ~0.44 inches from left
                        "translateY": 400000,  # ~0.44 inches from top
                        "unit": "EMU"
                    }
                }
            }
        }]
        
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": requests}
        ).execute()
        
        log.debug(f"Created notes TEXT_BOX: {textbox_id} on page: {notes_page_id}")
        return textbox_id
        
    except HttpError as e:
        log.debug(f"Could not create notes TEXT_BOX: {e}")
        return None


def _insert_notes_text(
    slides_service, presentation_id: str, shape_id: str, notes_text: str
) -> bool:
    """Insert text into the specified shape, replacing any existing content."""
    if not notes_text:
        notes_text = ""
        
    try:
        # Strategy 1: Try replace all text (most reliable for existing content)
        requests = [
            {
                "deleteText": {
                    "objectId": shape_id,
                    "textRange": {"type": "ALL"}
                }
            },
            {
                "insertText": {
                    "objectId": shape_id,
                    "insertionIndex": 0,
                    "text": notes_text
                }
            }
        ]
        
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": requests}
        ).execute()
        
        log.debug(f"Successfully replaced text in shape {shape_id} ({len(notes_text)} chars)")
        return True
        
    except HttpError as e:
        # Strategy 2: Delete might fail if shape is empty, try insert only
        log.debug(f"Replace strategy failed, trying insert: {e}")
        try:
            requests = [{
                "insertText": {
                    "objectId": shape_id,
                    "insertionIndex": 0,
                    "text": notes_text
                }
            }]
            
            slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": requests}
            ).execute()
            
            log.debug(f"Successfully inserted text in shape {shape_id} ({len(notes_text)} chars)")
            return True
            
        except HttpError as e2:
            # Strategy 3: Maybe shape doesn't exist, try to get more info
            log.debug(f"Insert strategy failed: {e2}")
            try:
                # Verify the shape actually exists
                pres = slides_service.presentations().get(
                    presentationId=presentation_id,
                    fields=f"slides/slideProperties/notesPage/pageElements(objectId)"
                ).execute()
                
                shape_exists = False
                for slide in pres.get("slides", []):
                    notes_page = slide.get("slideProperties", {}).get("notesPage", {})
                    for element in notes_page.get("pageElements", []):
                        if element.get("objectId") == shape_id:
                            shape_exists = True
                            break
                
                if shape_exists:
                    log.warning(f"Shape {shape_id} exists but text insertion failed: {e2}")
                else:
                    log.warning(f"Shape {shape_id} does not exist - may need to create notes shape first")
                    
            except Exception as e3:
                log.debug(f"Shape verification failed: {e3}")
                
            return False


def _add_visible_script_box(
    slides_service, presentation_id: str, slide_object_id: str, script_text: str
) -> bool:
    """Fallback: Add visible script box at bottom of slide."""
    try:
        import uuid
        script_box_id = f"script_box_{uuid.uuid4().hex[:8]}"
        
        requests = [
            {
                "createShape": {
                    "objectId": script_box_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_object_id,
                        "size": {
                            "width": {"magnitude": 8000000, "unit": "EMU"},
                            "height": {"magnitude": 1000000, "unit": "EMU"}
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 700000,
                            "translateY": 5200000,  # Bottom of slide
                            "unit": "EMU"
                        }
                    }
                }
            },
            {
                "insertText": {
                    "objectId": script_box_id,
                    "insertionIndex": 0,
                    "text": f"📝 Presenter Script:\n{script_text or ''}"
                }
            },
            {
                "updateTextStyle": {
                    "objectId": script_box_id,
                    "textRange": {"type": "ALL"},
                    "style": {
                        "fontSize": {"magnitude": 10, "unit": "PT"},
                        "foregroundColor": {
                            "opaqueColor": {"rgbColor": {"red": 0.4, "green": 0.4, "blue": 0.4}}
                        }
                    },
                    "fields": "fontSize,foregroundColor"
                }
            }
        ]
        
        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": requests}
        ).execute()
        
        log.info(f"Added visible script box as fallback: {script_box_id}")
        return True
        
    except HttpError as e:
        log.error(f"Even fallback script box failed: {e}")
        return False


def test_notes_implementation(presentation_id: str, slide_id: str) -> dict:
    """Test function to verify notes implementation works."""
    try:
        from .slides_google import _load_credentials, _slides_service
        
        creds = _load_credentials()
        slides = _slides_service(creds)
        
        test_text = f"Test speaker notes - {time.time()}"
        
        success = set_speaker_notes_native(
            slides, presentation_id, slide_id, test_text
        )
        
        return {
            "success": success,
            "message": "Native speaker notes test completed",
            "test_text": test_text,
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Native speaker notes test failed"
        }