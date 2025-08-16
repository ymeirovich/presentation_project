# src/mcp/tools/slides.py
from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

from googleapiclient.errors import HttpError

from ..schemas import SlidesCreateParams, SlidesCreateResult
from src.agent.slides_google import (
    create_presentation,
    upload_image_to_drive,
    create_main_slide_with_content,
    _load_credentials,  # ensures OAuth scopes include script.projects when used
)

from src.common.idempotency import load_cache, save_cache
from src.common.jsonlog import jlog

log = logging.getLogger("mcp.tools.slides")


# ---------- Retry helpers -----------------------------------------------------
def _retryable_http(e: Exception) -> bool:
    if isinstance(e, HttpError):
        status = getattr(e, "status_code", None) or getattr(getattr(e, "resp", None), "status", None)
        return status in (429, 500, 502, 503, 504)
    return False


def _backoff(fn, attempts: int = 4, base: float = 0.6):
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i >= attempts - 1 or not _retryable_http(e):
                raise
            delay = base * (2 ** i)
            log.warning("Retry after %.2fs (%s)", delay, type(e).__name__)
            time.sleep(delay)


# ---------- Image source selection -------------------------------------------
def _choose_image(p: SlidesCreateParams) -> Tuple[str, Optional[str]]:
    """
    Returns (mode, value)
      mode ∈ {"none","local","url","drive_file_id"}
      value = chosen string or None
    """
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


# ---------- Main tool ---------------------------------------------------------
def slides_create_tool(params: dict) -> dict:
    """
    Create a single-slide presentation with title/subtitle/bullets/image(+notes).
    Idempotent via client_request_id persisted to out/state/idempotency.json.
    """
    p = SlidesCreateParams.model_validate(params)

    # 1) Idempotency: check file-backed cache
    cache = load_cache()
    if p.client_request_id and p.client_request_id in cache:
        pres_id, slide_id, url = cache[p.client_request_id]
        jlog(log, logging.INFO, tool="slides.create", event="cache_hit",
             presentation_id=pres_id, slide_id=slide_id, url=url)
        return SlidesCreateResult(
            presentation_id=pres_id, slide_id=slide_id, url=url, reused_existing=True
        ).model_dump()

    # 2) Ensure credentials/scopes (no-op if using pure ADC for all)
    _ = _load_credentials()

    # 3) Create presentation (title shown in Drive)
    pres_title = p.title if not p.subtitle else f"{p.title}: {p.subtitle}"[:120]
    pres_id, url = _backoff(lambda: create_presentation(pres_title))
    jlog(log, logging.INFO, tool="slides.create", event="presentation_created",
         presentation_id=pres_id, url=url)

    # 4) Resolve image source to a URL usable by Slides
    mode, val = _choose_image(p)
    image_url: Optional[str] = None
    if mode == "local":
        file_id, public_url = _backoff(lambda: upload_image_to_drive(val, make_public=p.share_image_public))
        image_url = public_url or f"https://drive.google.com/uc?export=download&id={file_id}"
    elif mode == "url":
        image_url = val
    elif mode == "drive_file_id":
        image_url = f"https://drive.google.com/uc?export=download&id={val}"
    # elif mode == "none": keep image_url=None

    # 5) Build the single content slide (title/subtitle/bullets + optional image + notes)
    slide_id = _backoff(lambda: create_main_slide_with_content(
        presentation_id=pres_id,
        title=p.title,
        subtitle=p.subtitle,
        bullets=p.bullets,
        image_url=image_url,
        script=p.script or ""
    ))
    jlog(log, logging.INFO, tool="slides.create", event="slide_built",
         presentation_id=pres_id, slide_id=slide_id)

    # 6) Persist idempotency mapping (only if a key was provided)
    if p.client_request_id:
        cache[p.client_request_id] = (pres_id, slide_id, url)
        save_cache(cache)
        jlog(log, logging.INFO, tool="slides.create", event="cache_write",
             client_request_id=p.client_request_id, presentation_id=pres_id, slide_id=slide_id)

    return SlidesCreateResult(presentation_id=pres_id, slide_id=slide_id, url=url).model_dump()
