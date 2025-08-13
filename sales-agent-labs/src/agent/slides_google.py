from __future__ import annotations
import logging
import pathlib
from typing import Dict, Any, List, Optional
import uuid
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

log = logging.getLogger("agent.slides")

SLIDES_SCOPE = "https://www.googleapis.com/auth/presentations"
DRIVE_SCOPE  = "https://www.googleapis.com/auth/drive.file"
SCOPES = [SLIDES_SCOPE, DRIVE_SCOPE]

TOKEN_PATH = pathlib.Path("token_slides.json")
# Put your OAuth client JSON for Slides/Drive here (Web or Installed type).
# This is separate from Imagen's OAuth; using a dedicated file keeps things clean.
OAUTH_CLIENT_JSON = pathlib.Path("oauth_slides_client.json")

def _gen_id(prefix: str) -> str:
    # Slides objectIds must be <= 50 chars, letters/numbers/_
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def _load_credentials() -> Credentials:
    if TOKEN_PATH.exists():
        creds= Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if creds and creds.valid:
            log.debug("Using cached Slides/Drive token from %s", TOKEN_PATH)
            return creds
    if not OAUTH_CLIENT_JSON.exists():
        raise RuntimeError(
            "Missing oauth_slides_client.json and no token cache present. \n"
            "Download OAuth client credentials for Slides/Drive and save as oauth_slides_client.json, "
            "then run again to complete the browser consent."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CLIENT_JSON), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    log.info("Saved Slides/Drive OAuth token to %s", TOKEN_PATH)
    return creds

def _slides_service(creds: Credentials):
    return build("slides", "v1", credentials=creds, cache_discovery=False)

def _drive_service(creds: Credentials):
    return build("drive", "v3", credentials=creds, cache_discovery=False)

#-------- Slides Operations ----------

def create_presentation(title: str) -> Dict[str, Any]:
    creds = _load_credentials()
    slides = _slides_service(creds)
    try:
        pres=slides.presentations().create(body={"title":title}).execute()
        log.info("Created presentation: %s (%s)", pres.get("title"), pres.get("presentationId"))
        return pres
    except HttpError as e:
        _log_http_error("create_presentation",e)
        raise

def add_title_and_subtitle(presentation_id: str, title: str, subtitle: str) -> str:
    """
    Create a BLANK slide, add two text boxes, and fill them with title/subtitle.
    Returns the created slide's objectId.
    """
    creds = _load_credentials()
    slides = _slides_service(creds)

    # Unique IDs so multiple runs don’t collide
    slide_id   = _gen_id("title_slide")
    title_box  = _gen_id("title_box")
    sub_box    = _gen_id("subtitle_box")

    # EMU: English Metric Units. A 16:9 slide is ~10in x 5.625in → 914400 EMU per inch.
    # We'll position/size boxes reasonably near the top.
    requests = [
        {
            "createSlide": {
                "objectId": slide_id,
                "slideLayoutReference": {"predefinedLayout": "BLANK"}
            }
        },
        {
            "createShape": {
                "objectId": title_box,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width":  {"magnitude": 8000000, "unit": "EMU"},  # ~8.75in
                        "height": {"magnitude":  900000, "unit": "EMU"}   # ~1in
                    },
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX":  700000,   # ~0.77in from left
                        "translateY":  600000,   # ~0.66in from top
                        "unit": "EMU"
                    }
                }
            }
        },
        {
            "insertText": {
                "objectId": title_box,
                "insertionIndex": 0,
                "text": title
            }
        },
        # Optional: enlarge title font
        {
            "updateTextStyle": {
                "objectId": title_box,
                "style": {"fontSize": {"magnitude": 28, "unit": "PT"}, "bold": True},
                "textRange": {"type": "ALL"},
                "fields": "bold,fontSize"
            }
        },
        {
            "createShape": {
                "objectId": sub_box,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width":  {"magnitude": 8000000, "unit": "EMU"},
                        "height": {"magnitude":  700000, "unit": "EMU"}
                    },
                    "transform": {
                        "scaleX": 1, "scaleY": 1,
                        "translateX":  700000,
                        "translateY": 1700000,   # below the title
                        "unit": "EMU"
                    }
                }
            }
        },
        {
            "insertText": {
                "objectId": sub_box,
                "insertionIndex": 0,
                "text": subtitle
            }
        },
        # Optional: subtitle styling
        {
            "updateTextStyle": {
                "objectId": sub_box,
                "style": {"fontSize": {"magnitude": 16, "unit": "PT"}},
                "textRange": {"type": "ALL"},
                "fields": "fontSize"
            }
        }
    ]

    try:
        slides.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": requests}
        ).execute()
        log.info("Added title & subtitle on slide %s", slide_id)
        return slide_id
    except HttpError as e:
        _log_http_error("add_title_and_subtitle", e)
        raise

def _get_notes_shape_id(slides, presentation_id: str, page_object_id: str) -> str | None:
    """
    Return the objectId of the TEXT_BOX on the notesPage for the given slide page.
    Strategy:
      1) Prefer notesPage.notesProperties.notesShape.objectId if present.
      2) Else, scan notesPage.pageElements[] for a TEXT_BOX.
    """
    pres = slides.presentations().get(
        presentationId=presentation_id  # <-- no fields filter: fetch full structure
    ).execute()

    for s in pres.get("slides", []):
        if s.get("objectId") != page_object_id:
            continue

        notes_page = s.get("notesPage") or {}

        # --- Path A: notesProperties.notesShape.objectId (often present) ---
        notes_props = notes_page.get("notesProperties") or {}
        notes_shape = notes_props.get("notesShape")
        if isinstance(notes_shape, dict):
            ns_id = notes_shape.get("objectId")
            if ns_id:
                log.debug("Found notesShape via notesProperties: %s", ns_id)
                return ns_id

        # --- Path B: scan pageElements for a TEXT_BOX ---
        for el in notes_page.get("pageElements", []) or []:
            shp = el.get("shape") or {}
            if shp.get("shapeType") == "TEXT_BOX":
                ns_id = el.get("objectId")
                if ns_id:
                    log.debug("Found notesShape via pageElements scan: %s", ns_id)
                    return ns_id

        log.debug("No notesShape found on slide %s", page_object_id)

    return None


def add_bullets_and_script(presentation_id: str, bullets: list[str], script: str) -> str:
    """
    Create a BLANK slide, add a text box with bullet points, then set speaker notes.
    """
    creds = _load_credentials()
    slides = _slides_service(creds)

    body_slide_id = _gen_id("body_slide")
    body_box_id   = _gen_id("body_box")

    bullets = [b for b in bullets if isinstance(b, str) and b.strip()]
    bullet_text = "\n".join(bullets) if bullets else "(placeholder)"

    requests = [
        {"createSlide": {
            "objectId": body_slide_id,
            "slideLayoutReference": {"predefinedLayout": "BLANK"},
        }},
        {"createShape": {
            "objectId": body_box_id,
            "shapeType": "TEXT_BOX",
            "elementProperties": {
                "pageObjectId": body_slide_id,
                "size": {"width": {"magnitude": 6000000, "unit": "EMU"},
                         "height": {"magnitude": 3000000, "unit": "EMU"}},
                "transform": {"scaleX": 1, "scaleY": 1,
                              "translateX": 500000, "translateY": 1000000, "unit": "EMU"},
            }
        }},
        {"insertText": {
            "objectId": body_box_id,
            "insertionIndex": 0,
            "text": bullet_text,
        }},
        {"createParagraphBullets": {
            "objectId": body_box_id,
            "textRange": {"type": "ALL"},
            "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
        }},
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
            log.warning("No notes TEXT_BOX found for slide %s; skipping speaker notes.", body_slide_id)
            return body_slide_id

        slides.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": [{
                "insertText": {
                    "objectId": notes_shape_id,
                    "insertionIndex": 0,
                    "text": script or "",
                }
            }]},
        ).execute()
        log.info("Added speaker notes for slide %s", body_slide_id)
        return body_slide_id

    except HttpError as e:
        _log_http_error("add_bullets_and_script.notes", e)
        raise

def _set_speaker_notes(slides, presentation_id: str, page_object_id: str, script: str) -> None:
    # We fetch the page's notesPage to find the notesShape id, then insert text
    pres = slides.presentations().get(presentationId=presentation_id,
                                      fields="slides(notesPage(notesProperties,notesProperties/notesShape))").execute()
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
            body={"requests": [{"insertText": {"objectId": notes_shape_id, "insertionIndex": 0, "text": script}}]}
        ).execute()
    except HttpError as e:
        _log_http_error("_set_speaker_notes", e)
        raise

# ----------------------- Drive upload & image insert -----------------------

def upload_image_to_drive(image_path: pathlib.Path) -> str:
    """
    Uploads the image to Drive and returns a publicly accessible URL
    suitable for Slides 'createImage' from URL.
    """
    creds = _load_credentials()
    drive = _drive_service(creds)
    try:
        file_meta = {"name": image_path.name, "mimeType": "image/png"}
        media = None
        # Lazy import to keep top clean
        from googleapiclient.http import MediaFileUpload
        media = MediaFileUpload(str(image_path), mimetype="image/png", resumable=False)

        f = drive.files().create(body=file_meta, media_body=media, fields="id,webContentLink,webViewLink").execute()
        file_id = f["id"]

        # Make it link-readable
        drive.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}, fields="id").execute()

        # Use webContentLink as a direct content URL (Slides can fetch it)
        public_url = drive.files().get(fileId=file_id, fields="webContentLink").execute()["webContentLink"]
        log.info("Uploaded image to Drive: fileId=%s", file_id)
        return public_url
    except HttpError as e:
        _log_http_error("upload_image_to_drive", e)
        raise

def insert_image_from_url(presentation_id: str, image_url: str, page_object_id: str = "body_slide") -> None:
    creds = _load_credentials()
    slides = _slides_service(creds)
    requests = [{
        "createImage": {
            "url": image_url,
            "elementProperties": {
                "pageObjectId": page_object_id,
                "size": {"width": {"magnitude": 5000000, "unit": "EMU"},
                         "height": {"magnitude": 2812500, "unit": "EMU"}},  # ~16:9 box
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": 6500000, "translateY": 1000000, "unit": "EMU"}
            }
        }
    }]
    try:
        slides.presentations().batchUpdate(presentationId=presentation_id, body={"requests": requests}).execute()
        log.info("Inserted image on slide %s", page_object_id)
    except HttpError as e:
        _log_http_error("insert_image_from_url", e)
        raise

# ----------------------- Error logging helper -----------------------

def _log_http_error(where: str, e: HttpError) -> None:
    status = getattr(e, "status_code", None) or getattr(e, "resp", {}).status if getattr(e, "resp", None) else "?"
    try:
        content = e.content.decode("utf-8") if isinstance(e.content, (bytes, bytearray)) else str(e.content)
    except Exception:
        content = str(e)
    log.error("Google API error in %s | status=%s | content=%s", where, status, content)

