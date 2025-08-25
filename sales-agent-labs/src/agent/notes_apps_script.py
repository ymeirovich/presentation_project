# src/agent/notes_apps_script.py
from __future__ import annotations
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

log = logging.getLogger("agent.notes_script")


def set_speaker_notes_via_script(
    creds,  # google.oauth2.credentials.Credentials (must include script.projects scope)
    script_id: str,  # Apps Script *Script ID* (Project settings → Script ID), NOT deployment id
    presentation_id: str,  # Slides deck ID
    slide_object_id: str,  # target slide objectId
    text: str,  # notes text
) -> bool:
    """
    Call Apps Script API to run Code.gs:setSpeakerNotes.
    Returns True on success, False on failure (error already logged).
    """
    try:
        service = build("script", "v1", credentials=creds, cache_discovery=False)
        body = {
            "function": "setSpeakerNotes",
            "parameters": [presentation_id, slide_object_id, text or ""],
            "devMode": False,
        }
        resp = service.scripts().run(scriptId=script_id, body=body).execute()
        if "error" in resp:
            log.error("Apps Script error: %s", resp["error"])
            return False
        log.info("Apps Script setSpeakerNotes OK: %s", resp.get("response", {}))
        return True
    except HttpError:
        log.exception("Apps Script call failed")
        return False
