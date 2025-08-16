from __future__ import annotations
import logging, time
from typing import Dict, Tuple, Optional
from googleapiclient.errors import HttpError

from ..schemas import SlidesCreateParams, SlidesCreateResult
from src.agent.slides_google import (
    create_presentation,
    upload_image_to_drive,
    create_main_slide_with_content,
    _load_credentials,  # ensures scopes include script.projects
)

log = logging.getLogger("mcp.tools.slides")
_IDEMPOTENCY: Dict[str, Tuple[str, str, str]] = {}  # client_request_id -> (pres_id, slide_id, url)

def _retryable_http(e: Exception) -> bool:
    if isinstance(e, HttpError):
        status = getattr(e, "status_code", None) or getattr(getattr(e, "resp", None), "status", None)
        return status in (429, 500, 502, 503, 504)
    return False

def _backoff(fn, attempts=4, base=0.6):
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i >= attempts - 1 or not _retryable_http(e):
                raise
            delay = base * (2 ** i)
            log.warning("Retry after %.2fs (%s)", delay, type(e).__name__)
            time.sleep(delay)

def _choose_image(p: SlidesCreateParams) -> Tuple[str, Optional[str]]:
    count = sum(1 for v in [p.image_local_path, p.image_url, p.image_drive_file_id] if v)
    if count == 0:
        return ("none", None)
    if count > 1:
        raise ValueError("Provide exactly one of image_local_path, image_url, image_drive_file_id.")
    if p.image_drive_file_id:
        return ("drive_file_id", p.image_drive_file_id)
    if p.image_url:
        return ("url", str(p.image_url))
    return ("local", p.image_local_path)  # type: ignore

def slides_create_tool(params: dict) -> dict:
    p = SlidesCreateParams.model_validate(params)

    if p.client_request_id and p.client_request_id in _IDEMPOTENCY:
        pres, slide, url = _IDEMPOTENCY[p.client_request_id]
        return SlidesCreateResult(presentation_id=pres, slide_id=slide, url=url, reused_existing=True).model_dump()

    _ = _load_credentials()  # ensure OAuth scopes are present

    pres_id, url = _backoff(lambda: create_presentation(
        p.title if not p.subtitle else f"{p.title}: {p.subtitle}"[:120]
    ))

    mode, val = _choose_image(p)
    image_url = None
    if mode == "local":
        file_id, public_url = _backoff(lambda: upload_image_to_drive(val, make_public=p.share_image_public))
        image_url = public_url or f"https://drive.google.com/uc?export=download&id={file_id}"
    elif mode == "url":
        image_url = val
    elif mode == "drive_file_id":
        image_url = f"https://drive.google.com/uc?export=download&id={val}"

    slide_id = _backoff(lambda: create_main_slide_with_content(
        presentation_id=pres_id,
        title=p.title, subtitle=p.subtitle, bullets=p.bullets,
        image_url=image_url, script=p.script or ""
    ))

    if p.client_request_id:
        _IDEMPOTENCY[p.client_request_id] = (pres_id, slide_id, url)

    return SlidesCreateResult(presentation_id=pres_id, slide_id=slide_id, url=url).model_dump()
