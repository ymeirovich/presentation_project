from __future__ import annotations
import logging
import pathlib
from typing import Dict, Any, List, Optional
import uuid, time, os, inspect, sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from .notes_apps_script import set_speaker_notes_via_script

log = logging.getLogger("agent.slides")

EMU = "EMU"  # Slides uses English Metric Units (914,400 EMU per inch)

SLIDES_SCOPE = "https://www.googleapis.com/auth/presentations"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
SCRIPT_SCOPE = "https://www.googleapis.com/auth/script.projects"

SCOPES = [SLIDES_SCOPE, DRIVE_SCOPE, SCRIPT_SCOPE]


TOKEN_PATH = pathlib.Path("token_slides.json")
# Put your OAuth client JSON for Slides/Drive here (Web or Installed type).
# This is separate from Imagen's OAuth; using a dedicated file keeps things clean.
OAUTH_CLIENT_JSON = pathlib.Path("oauth_slides_client.json")


def _gen_id(prefix: str) -> str:
    # Slides objectIds must be <= 50 chars, letters/numbers/_
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _load_credentials() -> Credentials:
    SLIDES_SCOPE = "https://www.googleapis.com/auth/presentations"
    DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
    SCRIPT_SCOPE = (
        "https://www.googleapis.com/auth/script.projects"  # required for scripts.run
    )

    SCOPES = [SLIDES_SCOPE, DRIVE_SCOPE, SCRIPT_SCOPE]

    force_consent = os.getenv("FORCE_OAUTH_CONSENT") == "1"

    creds = None
    if TOKEN_PATH.exists() and not force_consent:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        # If token is valid *and* includes all scopes, reuse it
        if creds and creds.valid and creds.has_scopes(SCOPES):
            log.debug("Using cached OAuth token from %s", TOKEN_PATH)
            log.debug("Active OAuth scopes: %s", getattr(creds, "scopes", None))
            return creds
        else:
            # Either invalid or missing scopes — discard and re-consent
            try:
                TOKEN_PATH.unlink(missing_ok=True)
            except Exception:
                pass
            log.info("Cached token missing required scopes; will re-consent.")

    if not OAUTH_CLIENT_JSON.exists():
        raise RuntimeError(
            "Missing oauth_slides_client.json and no token cache present.\n"
            "Download OAuth client credentials and save as oauth_slides_client.json."
        )

    # Start a fresh consent flow requesting ALL current scopes
    flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CLIENT_JSON), SCOPES)
    # prompt='consent' ensures user sees the consent screen again
    creds = flow.run_local_server(port=0, prompt="consent")
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    log.info("Saved OAuth token to %s", TOKEN_PATH)
    log.debug("Active OAuth scopes: %s", getattr(creds, "scopes", None))
    return creds


def _slides_service(creds: Credentials):
    return build("slides", "v1", credentials=creds, cache_discovery=False)


def _drive_service(creds: Credentials):
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# -------- Slides Operations ----------
def set_speaker_notes_via_script(pres_id, slide_id, text):
    creds = _load_credentials()  # Your existing OAuth load
    service = build("script", "v1", credentials=creds, cache_discovery=False)

    body = {
        "function": "setSpeakerNotes",
        "parameters": [pres_id, slide_id, text],
        "devMode": False,
    }

    try:
        resp = (
            service.scripts()
            .run(scriptId=os.getenv("APPS_SCRIPT_DEPLOYMENT_ID"), body=body)
            .execute()
        )
        log.debug("Apps Script response:", resp)
    except HttpError as e:
        log.debug("Error calling Apps Script:", e)


def create_presentation(title: str) -> Dict[str, Any]:
    creds = _load_credentials()
    slides = _slides_service(creds)
    try:
        pres = slides.presentations().create(body={"title": title}).execute()
        log.info(
            "Created presentation: %s (%s)",
            pres.get("title"),
            pres.get("presentationId"),
        )
        return pres
    except HttpError as e:
        _log_http_error("create_presentation", e)
        raise


def add_title_and_subtitle(presentation_id: str, title: str, subtitle: str) -> str:
    """
    Create a BLANK slide, add two text boxes, and fill them with title/subtitle.
    Returns the created slide's objectId.
    """
    creds = _load_credentials()
    slides = _slides_service(creds)

    # Unique IDs so multiple runs don’t collide
    slide_id = _gen_id("title_slide")
    title_box = _gen_id("title_box")
    sub_box = _gen_id("subtitle_box")

    # EMU: English Metric Units. A 16:9 slide is ~10in x 5.625in → 914400 EMU per inch.
    # We'll position/size boxes reasonably near the top.
    requests = [
        {
            "createSlide": {
                "objectId": slide_id,
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
            }
        },
        {
            "createShape": {
                "objectId": title_box,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": 8000000, "unit": "EMU"},  # ~8.75in
                        "height": {"magnitude": 900000, "unit": "EMU"},  # ~1in
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 700000,  # ~0.77in from left
                        "translateY": 600000,  # ~0.66in from top
                        "unit": "EMU",
                    },
                },
            }
        },
        {"insertText": {"objectId": title_box, "insertionIndex": 0, "text": title}},
        # Optional: enlarge title font
        {
            "updateTextStyle": {
                "objectId": title_box,
                "style": {"fontSize": {"magnitude": 28, "unit": "PT"}, "bold": True},
                "textRange": {"type": "ALL"},
                "fields": "bold,fontSize",
            }
        },
        {
            "createShape": {
                "objectId": sub_box,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": 8000000, "unit": "EMU"},
                        "height": {"magnitude": 700000, "unit": "EMU"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 700000,
                        "translateY": 1700000,  # below the title
                        "unit": "EMU",
                    },
                },
            }
        },
        {"insertText": {"objectId": sub_box, "insertionIndex": 0, "text": subtitle}},
        # Optional: subtitle styling
        {
            "updateTextStyle": {
                "objectId": sub_box,
                "style": {"fontSize": {"magnitude": 16, "unit": "PT"}},
                "textRange": {"type": "ALL"},
                "fields": "fontSize",
            }
        },
    ]

    try:
        slides.presentations().batchUpdate(
            presentationId=presentation_id, body={"requests": requests}
        ).execute()
        log.info("Added title & subtitle on slide %s", slide_id)
        return slide_id
    except HttpError as e:
        _log_http_error("add_title_and_subtitle", e)
        raise


def _fetch_slide_with_notes(
    slides, presentation_id: str, page_object_id: str
) -> dict | None:
    """
    Fetch a single slide with the notesPage objectId, speakerNotesObjectId,
    and any pageElements (so we can fall back to an existing TEXT_BOX).
    """
    try:
        pres = (
            slides.presentations()
            .get(
                presentationId=presentation_id,
                # Ask explicitly for the fields we need; use slashes for nested paths.
                fields=(
                    "slides("
                    "objectId,"
                    "notesPage/objectId,"
                    "notesPage/notesProperties/speakerNotesObjectId,"
                    "notesPage/pageElements(objectId,shape/shapeType)"
                    ")"
                ),
            )
            .execute()
        )
    except HttpError as e:
        _log_http_error("_fetch_slide_with_notes", e)
        return None

    for s in pres.get("slides", []):
        if s.get("objectId") == page_object_id:
            return s

    log.debug("Slide %s not found in presentation.", page_object_id)
    return None


def _fetch_slide_full(slides, presentation_id: str, page_object_id: str) -> dict | None:
    """Fetch the full presentation (no fields mask) and return the specific slide dict."""
    try:
        pres = slides.presentations().get(presentationId=presentation_id).execute()
    except HttpError as e:
        _log_http_error("_fetch_slide_full", e)
        return None

    for s in pres.get("slides", []):
        if s.get("objectId") == page_object_id:
            return s
    return None


def _find_notes_shape_pointer(slide_dict: dict) -> tuple[str | None, dict]:
    """
    Try all known paths to the notes text shape pointer and return (shape_id, notes_page_dict).
      - notesPage.notesProperties.speakerNotesObjectId
      - notesPage.notesProperties.notesShape.objectId
      - notesPage.pageElements[*.shapeType == TEXT_BOX].objectId
    """
    notes_page = (slide_dict or {}).get("notesPage") or {}
    props = notes_page.get("notesProperties") or {}

    # A) Official pointer
    sn_id = props.get("speakerNotesObjectId")
    if sn_id:
        return sn_id, notes_page

    # B) Some payloads expose the actual notes shape object
    notes_shape = props.get("notesShape")
    if isinstance(notes_shape, dict):
        ns_id = notes_shape.get("objectId")
        if ns_id:
            return ns_id, notes_page

    # C) Fallback: scan existing elements
    for el in notes_page.get("pageElements") or []:
        shp = el.get("shape") or {}
        if shp.get("shapeType") == "TEXT_BOX":
            ns_id = el.get("objectId")
            if ns_id:
                return ns_id, notes_page

    return None, notes_page


def _create_notes_textbox_on_page(
    slides, presentation_id: str, notes_page_id: str
) -> str | None:
    """Create a TEXT_BOX on the given notes page and return its objectId."""
    new_id = _gen_id("notes_box")
    reqs = [
        {
            "createShape": {
                "objectId": new_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": notes_page_id,
                    "size": {
                        "width": {"magnitude": 8000000, "unit": "EMU"},
                        "height": {"magnitude": 1500000, "unit": "EMU"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 400000,
                        "translateY": 400000,
                        "unit": "EMU",
                    },
                },
            }
        }
    ]
    try:
        slides.presentations().batchUpdate(
            presentationId=presentation_id, body={"requests": reqs}
        ).execute()
        log.debug("Created notes TEXT_BOX %s on notesPage %s", new_id, notes_page_id)
        return new_id
    except HttpError as e:
        _log_http_error("_create_notes_textbox_on_page", e)
        return None


def _get_notes_shape_id(
    slides, presentation_id: str, page_object_id: str
) -> str | None:
    """
    Return the speaker notes shape objectId for the given slide.
    Preferred path: notesPage.notesProperties.speakerNotesObjectId.
    If absent, fall back to scanning pageElements for a TEXT_BOX.
    """
    pres = slides.presentations().get(presentationId=presentation_id).execute()

    for s in pres.get("slides", []):
        if s.get("objectId") != page_object_id:
            continue

        # Access notes page via the correct path: slideProperties.notesPage
        slide_props = s.get("slideProperties", {})
        notes_page = slide_props.get("notesPage", {})
        props = notes_page.get("notesProperties", {})

        # ✅ Primary path (official pointer). If the actual shape doesn't exist yet,
        # inserting text with this ID will auto-create it.
        sn_id = props.get("speakerNotesObjectId")
        if sn_id:
            log.debug("Found speakerNotesObjectId: %s", sn_id)
            return sn_id

        # Fallback: scan pageElements for a TEXT_BOX (older decks/themes)
        for el in notes_page.get("pageElements") or []:
            shp = el.get("shape") or {}
            if shp.get("shapeType") == "TEXT_BOX":
                ns_id = el.get("objectId")
                if ns_id:
                    log.debug("Found notes TEXT_BOX via pageElements: %s", ns_id)
                    return ns_id

        log.debug("No notes shape pointer for slide %s", page_object_id)

    return None


def _get_notes_page_id(slides, presentation_id: str, page_object_id: str) -> str | None:
    """Return the notesPage.objectId for the given slide page."""
    pres = slides.presentations().get(presentationId=presentation_id).execute()
    for s in pres.get("slides", []):
        if s.get("objectId") == page_object_id:
            # Access notes page via the correct path: slideProperties.notesPage
            slide_props = s.get("slideProperties", {})
            notes_page = slide_props.get("notesPage", {})
            npid = notes_page.get("objectId")
            if npid:
                return npid
    return None


def _get_or_create_notes_shape(
    slides, presentation_id: str, page_object_id: str
) -> str | None:
    """
    Robust path:
      1) Fetch slide; try all pointer paths.
      2) If notesPage.objectId missing, retry a couple of times (race condition).
      3) If still missing, try heuristic notes page id: f"{page_object_id}_notes".
      4) If still impossible, return None (caller will fall back to on-slide script box).
    """
    # --- 1) Fetch + probe once
    slide = _fetch_slide_full(slides, presentation_id, page_object_id)
    if not slide:
        log.warning("Could not fetch slide %s to write notes.", page_object_id)
        return None

    shape_id, notes_page = _find_notes_shape_pointer(slide)
    if shape_id:
        log.debug("Using notes shape id: %s", shape_id)
        return shape_id

    # --- 2) If missing notesPage.objectId, sleep+retry a couple of times
    notes_page_id = notes_page.get("objectId")
    if not notes_page_id:
        log.debug("notesPage has no objectId; raw notesPage: %r", notes_page)
        for i in range(2):  # small retry window
            time.sleep(5.0)  # give backend time to populate notes metadata
            slide = _fetch_slide_full(slides, presentation_id, page_object_id)
            if not slide:
                break
            shape_id, notes_page = _find_notes_shape_pointer(slide)
            if shape_id:
                log.debug("Using notes shape id after retry %d: %s", i + 1, shape_id)
                return shape_id
            notes_page_id = (notes_page or {}).get("objectId")
            if notes_page_id:
                break

    # --- 3) If still no objectId, try heuristic page id
    if not notes_page_id:
        heuristic_id = f"{page_object_id}_notes"
        log.debug("Trying heuristic notes page id: %s", heuristic_id)
        created = _create_notes_textbox_on_page(slides, presentation_id, heuristic_id)
        if created:
            return created
        # If that failed, we’re done here
        return None

    # We *do* have a notes page id; create a text box on it and return the id
    return _create_notes_textbox_on_page(slides, presentation_id, notes_page_id)


def add_bullets_and_script(
    presentation_id: str, bullets: list[str], script: str
) -> str:
    """
    Create a BLANK slide, add a text box with bullet points, then set speaker notes.
    """
    creds = _load_credentials()
    slides = _slides_service(creds)

    body_slide_id = _gen_id("body_slide")
    body_box_id = _gen_id("body_box")

    bullets = [b for b in bullets if isinstance(b, str) and b.strip()]
    bullet_text = "\n".join(bullets) if bullets else "(placeholder)"

    requests = [
        {
            "createSlide": {
                "objectId": body_slide_id,
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
            }
        },
        {
            "createShape": {
                "objectId": body_box_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": body_slide_id,
                    "size": {
                        "width": {"magnitude": 6000000, "unit": "EMU"},
                        "height": {"magnitude": 3000000, "unit": "EMU"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 500000,
                        "translateY": 1000000,
                        "unit": "EMU",
                    },
                },
            }
        },
        {
            "insertText": {
                "objectId": body_box_id,
                "insertionIndex": 0,
                "text": bullet_text,
            }
        },
        {
            "createParagraphBullets": {
                "objectId": body_box_id,
                "textRange": {"type": "ALL"},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }
        },
    ]

    # Create slide + bullets
    try:
        slides.presentations().batchUpdate(
            presentationId=presentation_id, body={"requests": requests}
        ).execute()
        log.info("Added bullets on slide %s", body_slide_id)
    except HttpError as e:
        _log_http_error("add_bullets_and_script.create+bullets", e)
        raise

    # Speaker notes
    try:
        notes_shape_id = _get_notes_shape_id(slides, presentation_id, body_slide_id)
        if not notes_shape_id:
            log.warning(
                "No notes TEXT_BOX found for slide %s; skipping speaker notes.",
                body_slide_id,
            )
            return body_slide_id

        slides.presentations().batchUpdate(
            presentationId=presentation_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "objectId": notes_shape_id,
                            "insertionIndex": 0,
                            "text": script or "",
                        }
                    }
                ]
            },
        ).execute()
        log.info("Added speaker notes for slide %s", body_slide_id)
        return body_slide_id

    except HttpError as e:
        _log_http_error("add_bullets_and_script.notes", e)
        raise


def _set_speaker_notes(
    slides, presentation_id: str, page_object_id: str, script: str
) -> None:
    # We fetch the page's notesPage to find the notesShape id, then insert text
    pres = (
        slides.presentations()
        .get(
            presentationId=presentation_id,
            fields="slides(notesPage(notesProperties,notesProperties/notesShape))",
        )
        .execute()
    )
    # For simplicity, locate the first notesShape available for the last page
    # (A more robust approach would map page_object_id -> its notesPage.)
    # In many templates, there is a single notesShape per slide.
    try:
        notes_shape_id = None
        for s in pres.get("slides", []):
            notes = s.get("notesPage", {})
            shape = notes.get("notesProperties", {}).get("notesShape")
            if shape and shape.get("objectId"):
                notes_shape_id = shape["objectId"]
        if not notes_shape_id:
            log.warning("No notesShape found; skipping speaker notes.")
            return
        slides.presentations().batchUpdate(
            presentationId=presentation_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "objectId": notes_shape_id,
                            "insertionIndex": 0,
                            "text": script,
                        }
                    }
                ]
            },
        ).execute()
    except HttpError as e:
        _log_http_error("_set_speaker_notes", e)
        raise


def delete_default_slide(presentation_id: str) -> str:
    """
    Delete the first (default) slide the API creates and return its objectId.
    """
    creds = _load_credentials()
    slides = _slides_service(creds)

    pres = slides.presentations().get(presentationId=presentation_id).execute()
    first = pres.get("slides", [])[0]
    default_id = first["objectId"]

    slides.presentations().batchUpdate(
        presentationId=presentation_id,
        body={"requests": [{"deleteObject": {"objectId": default_id}}]},
    ).execute()
    log.info("Deleted default slide: %s", default_id)
    return default_id


def _add_on_slide_script_box(
    slides, presentation_id: str, slide_id: str, script: str
) -> None:
    """Fallback: put the script on the slide bottom; guarantees presenter has the text."""
    script_box_id = _gen_id("script_box")
    reqs = [
        {
            "createShape": {
                "objectId": script_box_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": 8000000, "unit": "EMU"},
                        "height": {"magnitude": 1000000, "unit": "EMU"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 700000,
                        "translateY": 5200000,
                        "unit": "EMU",
                    },
                },
            }
        },
        {
            "insertText": {
                "objectId": script_box_id,
                "insertionIndex": 0,
                "text": "Presenter Script:\n" + (script or ""),
            }
        },
        {
            "updateTextStyle": {
                "objectId": script_box_id,
                "textRange": {"type": "FIXED_RANGE", "startIndex": 0, "endIndex": 17},
                "style": {"bold": True},
                "fields": "bold",
            }
        },
        {
            "updateTextStyle": {
                "objectId": script_box_id,
                "textRange": {"type": "ALL"},
                "style": {"fontSize": {"magnitude": 11, "unit": "PT"}},
                "fields": "fontSize",
            }
        },
    ]
    try:
        slides.presentations().batchUpdate(
            presentationId=presentation_id, body={"requests": reqs}
        ).execute()
        log.info("Placed 'Presenter Script' box on the slide.")
    except HttpError as e:
        _log_http_error("_add_on_slide_script_box", e)


def create_main_slide_with_content(
    presentation_id: str,
    *,
    title: str,
    subtitle: str,
    bullets: List[str],
    image_url: Optional[str],
    script: Optional[str],
) -> str:
    """
    Create a single BLANK slide containing:
      - Title (text box)
      - Subtitle (text box)
      - Bulleted list (text box, valid bullet preset)
      - Optional image (right column)
    Then set speaker notes using Apps Script (most reliable).
    If speaker notes cannot be set, place a small 'Presenter Script' box on the slide.

    Returns:
        slide_id (str): the objectId of the created slide.
    """
    # Acquire creds + Slides service (uses your existing helpers in this module)
    creds = _load_credentials()
    slides = _slides_service(creds)

    # Generate stable IDs for this slide and its elements
    slide_id = _gen_id("main_slide")
    title_box = _gen_id("title_box")
    sub_box = _gen_id("subtitle_box")
    body_box = _gen_id("body_box")

    # Normalize inputs
    title = title or "Untitled"
    subtitle = subtitle or ""  # Keep empty string for now
    bullets = [b for b in (bullets or []) if isinstance(b, str) and b.strip()]
    bullet_text = "\n".join(bullets) if bullets else "(placeholder)"
    
    # Determine if we should create subtitle elements
    has_subtitle = bool(subtitle and subtitle.strip())

    # 🔧 Smart image handling: base64 for small files, Drive URLs for large
    final_image_url = None
    if image_url:
        log.debug("Original image URL: %s", image_url)
        
        # Check if it's a local file path (charts from data pipeline)
        if image_url.startswith(('/Users', './out', 'out/')):
            image_path = pathlib.Path(image_url)
            if image_path.exists():
                # Try base64 for small files (charts)
                data_url = _create_base64_data_url(image_path)
                if data_url:
                    final_image_url = data_url
                    log.info("Using base64 embed for chart: %s", image_path.name)
                else:
                    # File too large, upload to Drive
                    log.info("File >100KB, uploading to Drive: %s", image_path.name)
                    try:
                        _, drive_url = upload_image_to_drive(image_path, make_public=True)
                        final_image_url = drive_url
                    except Exception as e:
                        log.error("Drive upload failed: %s", e)
                        final_image_url = None
            else:
                log.warning("Local image path does not exist: %s", image_url)
        else:
            # Already a URL, normalize for Drive compatibility
            final_image_url = _drive_public_download_url(image_url)
            
        if final_image_url:
            log.debug("Using final image URL for Slides: %s", final_image_url[:100] + "..." if len(final_image_url) > 100 else final_image_url)

    # Layout (16:9). Reasonable positions/sizes in EMU.
    # Top area: title and optional subtitle
    # Lower left: bullets
    # Lower right: optional image
    requests = [
        # 1) Slide
        {
            "createSlide": {
                "objectId": slide_id,
                "slideLayoutReference": {"predefinedLayout": "BLANK"},
            }
        },
        # 2) Title box
        {
            "createShape": {
                "objectId": title_box,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": 8000000, "unit": EMU},  # ~8.75 in
                        "height": {"magnitude": 900000, "unit": EMU},  # ~1 in
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 700000,  # ~0.77 in from left
                        "translateY": 600000,  # ~0.66 in from top
                        "unit": EMU,
                    },
                },
            }
        },
        {"insertText": {"objectId": title_box, "insertionIndex": 0, "text": title}},
        {
            "updateTextStyle": {
                "objectId": title_box,
                "textRange": {"type": "ALL"},
                "style": {"fontSize": {"magnitude": 28, "unit": "PT"}, "bold": True},
                "fields": "bold,fontSize",
            }
        },
    ]
    
    # 3) Subtitle box (only if subtitle exists)
    if has_subtitle:
        subtitle_requests = [
            {
                "createShape": {
                    "objectId": sub_box,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": 8000000, "unit": EMU},
                            "height": {"magnitude": 700000, "unit": EMU},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 700000,
                            "translateY": 1700000,
                            "unit": EMU,
                        },
                    },
                }
            },
            {"insertText": {"objectId": sub_box, "insertionIndex": 0, "text": subtitle}},
            {
                "updateTextStyle": {
                    "objectId": sub_box,
                    "textRange": {"type": "ALL"},
                    "style": {"fontSize": {"magnitude": 16, "unit": "PT"}},
                    "fields": "fontSize",
                }
            },
        ]
        requests.extend(subtitle_requests)
    
    # 4) Bullets section
    bullets_requests = [
        {
            "createShape": {
                "objectId": body_box,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": 5000000, "unit": EMU},
                        "height": {"magnitude": 3000000, "unit": EMU},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 700000,
                        "translateY": 2600000,
                        "unit": EMU,
                    },
                },
            }
        },
        {
            "insertText": {
                "objectId": body_box,
                "insertionIndex": 0,
                "text": bullet_text,
            }
        },
        {
            "createParagraphBullets": {
                "objectId": body_box,
                "textRange": {"type": "ALL"},
                # Valid preset (BULLET_DISC is invalid)
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }
        },
    ]
    
    # Add bullets requests to main requests
    requests.extend(bullets_requests)

    # 5) Optional image (right column)
    log.debug("Final image URL for insertion:", final_image_url)
    if final_image_url:
        requests.append(
            {
                "createImage": {
                    "url": final_image_url,
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": 5000000, "unit": EMU},
                            "height": {"magnitude": 2812500, "unit": EMU},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 6000000,
                            "translateY": 2600000,
                            "unit": EMU,
                        },
                    },
                }
            }
        )
    # Execute: create slide + content
    try:
        log.debug("createImage? %s", bool(final_image_url))
        slides.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": requests},
        ).execute()
        log.info(
            "Built main slide with title/subtitle/bullets%s",
            " + image" if final_image_url else "",
        )
    except HttpError as e:
        _log_http_error("create_main_slide_with_content.layout", e)
        raise

    # --- Speaker notes with multiple fallback strategies ---
    if script:
        log.debug("Setting speaker notes for slide: %s", slide_id)
        
        # Strategy 1: Try enhanced native API (most reliable)
        try:
            from .notes_native_api import set_speaker_notes_native
            
            log.debug("Attempting speaker notes via enhanced native API")
            if set_speaker_notes_native(slides, presentation_id, slide_id, script):
                log.info("✅ Speaker notes set via enhanced native API")
                return slide_id
            else:
                log.warning("Enhanced native API returned False")
                
        except Exception as e:
            log.warning("Enhanced native API failed with exception: %s", e)
        
        # Strategy 2: Try Apps Script (if configured)
        script_id = os.getenv("APPS_SCRIPT_SCRIPT_ID", "").strip()
        if script_id:
            try:
                from .notes_apps_script import set_speaker_notes_via_script as _notes_func
                
                log.debug("Attempting Apps Script notes with ID: %s", script_id)
                if _notes_func(creds, script_id, presentation_id, slide_id, script):
                    log.info("Speaker notes set via Apps Script")
                    return slide_id
                else:
                    log.warning("Apps Script method failed (insufficient scopes)")
                    
            except Exception as e:
                log.warning("Apps Script method failed: %s", e)
        
        # Strategy 3: Legacy native approach
        try:
            notes_shape_id = _get_notes_shape_id(slides, presentation_id, slide_id)
            if notes_shape_id:
                slides.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={
                        "requests": [{
                            "insertText": {
                                "objectId": notes_shape_id,
                                "insertionIndex": 0,
                                "text": script,
                            }
                        }]
                    },
                ).execute()
                log.info("Speaker notes set via legacy native API")
                return slide_id
                
        except Exception as e:
            log.warning("Legacy native method failed: %s", e)
        
        # Strategy 4: Guaranteed fallback - visible script box
        log.warning("🚨 All speaker notes methods failed, falling back to visible script box on slide")
        log.warning("This means speaker notes will appear as visible text, not in Speaker Notes panel")
        _add_on_slide_script_box(slides, presentation_id, slide_id, script)

    return slide_id


# ----------------------- Drive upload & image insert -----------------------


def _create_base64_data_url(image_path: pathlib.Path) -> str | None:
    """
    Convert small PNG files to base64 data URLs for instant embedding.
    Returns None if file too large (>100KB for charts).
    """
    file_size = image_path.stat().st_size
    MAX_BASE64_SIZE = 1_500  # 1.5KB - Google Slides API has 2KB URL limit, base64 only for very small images
    
    if file_size > MAX_BASE64_SIZE:
        return None
        
    try:
        import base64
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        log.info("Created base64 data URL: size=%d bytes (%.1fKB)", file_size, file_size/1024)
        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        log.warning("Failed to create base64 data URL: %s", e)
        return None


def upload_image_to_drive(
    image_path: str | pathlib.Path, make_public: bool = True
) -> tuple[str, str]:
    """
    Uploads a PNG to Drive, optionally makes it public, and returns:
      (file_id, public_download_url)
    """
    import time
    start_time = time.time()
    
    image_path = pathlib.Path(image_path)
    creds = _load_credentials()
    drive = _drive_service(creds)

    from googleapiclient.http import MediaFileUpload

    file_size = image_path.stat().st_size
    
    # Enhanced logging with size thresholds
    log.info("Drive upload begin: path=%s size=%d bytes (%.1fMB)", 
             image_path.name, file_size, file_size / (1024*1024))
    
    if file_size > 5_000_000:  # 5MB
        log.warning("Large file upload detected - this may take several minutes")
        
    if file_size > 10_000_000:  # 10MB  
        log.error("File exceeds 10MB - consider compression or alternative approach")

    meta = {"name": image_path.name, "mimeType": "image/png"}
    # Use resumable upload for better reliability with larger files
    file_size = image_path.stat().st_size
    resumable = file_size > 1_000_000  # 1MB threshold
    media = MediaFileUpload(str(image_path), mimetype="image/png", resumable=resumable)

    try:
        f = drive.files().create(body=meta, media_body=media, fields="id").execute()
        file_id = f["id"]
        upload_duration = time.time() - start_time
        log.info("Drive upload complete: fileId=%s duration=%.2fs", file_id, upload_duration)

        if make_public:
            perm_start = time.time()
            drive.permissions().create(
                fileId=file_id, body={"type": "anyone", "role": "reader"}, fields="id"
            ).execute()
            perm_duration = time.time() - perm_start
            log.info("Drive permissions set: duration=%.2fs", perm_duration)

        public_url = _drive_public_download_url(file_id)
        total_duration = time.time() - start_time
        log.info(
            "Drive upload OK: fileId=%s total_duration=%.2fs public=%s", 
            file_id, total_duration, bool(make_public)
        )
        return file_id, public_url
        
    except Exception as e:
        duration = time.time() - start_time
        log.error("Drive upload failed: path=%s duration=%.2fs error=%s", 
                  image_path.name, duration, str(e))
        raise


def insert_image_from_url(
    presentation_id: str, image_url: str, page_object_id: str = "body_slide"
) -> None:
    creds = _load_credentials()
    slides = _slides_service(creds)
    requests = [
        {
            "createImage": {
                "url": image_url,
                "elementProperties": {
                    "pageObjectId": page_object_id,
                    "size": {
                        "width": {"magnitude": 5000000, "unit": "EMU"},
                        "height": {"magnitude": 2812500, "unit": "EMU"},
                    },  # ~16:9 box
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": 6500000,
                        "translateY": 1000000,
                        "unit": "EMU",
                    },
                },
            }
        }
    ]
    try:
        slides.presentations().batchUpdate(
            presentationId=presentation_id, body={"requests": requests}
        ).execute()
        log.info("Inserted image on slide %s", page_object_id)
    except HttpError as e:
        _log_http_error("insert_image_from_url", e)
        raise


# ----------------------- Error logging helper -----------------------


def _log_http_error(where: str, e: HttpError) -> None:
    status = (
        getattr(e, "status_code", None) or getattr(e, "resp", {}).status
        if getattr(e, "resp", None)
        else "?"
    )
    try:
        content = (
            e.content.decode("utf-8")
            if isinstance(e.content, (bytes, bytearray))
            else str(e.content)
        )
    except Exception:
        content = str(e)
    log.error("Google API error in %s | status=%s | content=%s", where, status, content)


def _drive_public_download_url(file_id_or_url: str) -> str:
    """
    Accepts either a Drive fileId or any Drive URL and returns a stable
    direct-download URL Slides can fetch: https://drive.google.com/uc?export=download&id=<fileId>
    """
    log.debug("inside drive public download url")
    import re

    s = str(file_id_or_url)
    # If we already have a bare id
    if re.fullmatch(r"[A-Za-z0-9_\-]{10,}", s):
        fid = s
    else:
        # Try to extract fileId from common Drive URL shapes
        m = re.search(r"/d/([A-Za-z0-9_\-]{10,})", s) or re.search(
            r"[?&]id=([A-Za-z0-9_\-]{10,})", s
        )
        fid = m.group(1) if m else s  # fall back to raw
    return f"https://drive.google.com/uc?export=download&id={fid}"
