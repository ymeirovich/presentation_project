# src/mcp/tools/slides.py
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple, List

from googleapiclient.errors import HttpError

from ..schemas import SlidesCreateParams, SlidesCreateResult
from src.agent.slides_google import (
    create_presentation,
    create_main_slide_with_content,
    delete_default_slide,
    _load_credentials,
    _drive_public_download_url,
)
from src.common.idempotency import load_cache, save_cache
from src.common.jsonlog import jlog

log = logging.getLogger("mcp.tools.slides")

# ---------- Retry helpers -----------------------------------------------------


def _retryable_http(e: Exception) -> bool:
    if isinstance(e, HttpError):
        status = getattr(e, "status_code", None) or getattr(
            getattr(e, "resp", None), "status", None
        )
        return status in (429, 500, 502, 503, 504)
    return False


def _backoff(fn, attempts: int = 4, base: float = 0.6):
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i >= attempts - 1 or not _retryable_http(e):
                raise
            delay = base * (2**i)
            log.warning("Retry after %.2fs (%s)", delay, type(e).__name__)
            time.sleep(delay)


# ---------- Return normalization ---------------------------------------------


def _normalize_create_presentation_ret(ret: Any) -> Tuple[str, str]:
    """
    Accept shapes from create_presentation(...) and return (presentation_id, url).

    Supported:
      - tuple/list: (id, url) or (id, file_id, url) → (first, last)
      - dict: {presentation_id|presentationId|id, url|presentation_url|presentationUrl|link}
      - str: just the presentation ID → synthesize URL
    """
    if isinstance(ret, (tuple, list)):
        if len(ret) == 2:
            pres_id, url = ret[0], ret[1]
            return str(pres_id), str(url)
        if len(ret) >= 3:
            pres_id, url = ret[0], ret[-1]
            return str(pres_id), str(url)
        raise ValueError(
            "create_presentation returned tuple/list with insufficient values"
        )

    if isinstance(ret, dict):
        pres_id = (
            ret.get("presentation_id") or ret.get("presentationId") or ret.get("id")
        )
        url = (
            ret.get("url")
            or ret.get("presentation_url")
            or ret.get("presentationUrl")
            or ret.get("link")
        )
        if pres_id and url:
            return str(pres_id), str(url)
        if pres_id and not url:
            return (
                str(pres_id),
                f"https://docs.google.com/presentation/d/{pres_id}/edit",
            )
        raise ValueError("create_presentation returned dict without usable id/url")

    if isinstance(ret, str):
        pres_id = ret
        return pres_id, f"https://docs.google.com/presentation/d/{pres_id}/edit"

    raise ValueError(f"Unsupported return type from create_presentation: {type(ret)!r}")


# ---------- Image source selection -------------------------------------------


def _choose_image(p: SlidesCreateParams) -> Tuple[str, Optional[str]]:
    """
    Returns (mode, value)
      mode ∈ {"none","local","url","drive_file_id"}
    """
    count = sum(
        1 for v in [p.image_local_path, p.image_url, p.image_drive_file_id] if v
    )
    if count == 0:
        return ("none", None)
    if count > 1:
        raise ValueError(
            "Provide exactly one of image_local_path, image_url, image_drive_file_id."
        )
    if p.image_drive_file_id:
        return ("drive_file_id", p.image_drive_file_id)
    if p.image_url:
        return (
            "url",
            str(p.image_url),
        )  # ensure plain str (avoid HttpUrl serialization issues)
    return ("local", p.image_local_path)  # type: ignore


def _clamp_title(title: str, subtitle: Optional[str]) -> str:
    composed = title if not subtitle else f"{title}: {subtitle}"
    return composed[:120]


# ---------- Main tool ---------------------------------------------------------


def slides_create_tool(params: dict) -> dict:
    """
    Create a single-slide presentation with title/subtitle/bullets/image(+notes).

    Behavior:
      - If 'presentation_id' present → append the new slide to that deck.
      - Else → create a new deck, delete the default blank slide, then add content.

    Idempotent via client_request_id persisted to out/state/idempotency.json.
    Returns strictly JSON-safe dict via SlidesCreateResult.model_dump(mode="json").
    """
    p = SlidesCreateParams.model_validate(params)

    # 1) Idempotency: check file-backed cache
    cache = load_cache()
    if p.client_request_id and p.client_request_id in cache:
        pres_id, slide_id, url = cache[p.client_request_id]
        jlog(
            log,
            logging.INFO,
            tool="slides.create",
            event="cache_hit",
            client_request_id=p.client_request_id,
            presentation_id=pres_id,
            slide_id=slide_id,
            url=url,
        )
        return SlidesCreateResult(
            presentation_id=str(pres_id),
            slide_id=str(slide_id),
            url=str(url),
            reused_existing=True,
        ).model_dump(mode="json")

    # 2) Ensure credentials/scopes (no-op if using ADC for everything)
    _ = _load_credentials()

    # 3) Deck: append or create
    pres_id: str
    url: str

    if getattr(p, "presentation_id", None):
        # Append mode
        pres_id = str(p.presentation_id)
        url = f"https://docs.google.com/presentation/d/{pres_id}/edit"
        jlog(
            log,
            logging.INFO,
            tool="slides.create",
            event="append_mode",
            presentation_id=pres_id,
            url=url,
        )
    else:
        # Create new deck
        ret = _backoff(lambda: create_presentation(_clamp_title(p.title, p.subtitle)))
        pres_id, url = _normalize_create_presentation_ret(ret)
        jlog(
            log,
            logging.INFO,
            tool="slides.create",
            event="presentation_created",
            presentation_id=pres_id,
            url=url,
        )
        # Remove the first blank slide the API auto-creates (non-fatal)
        try:
            _backoff(lambda: delete_default_slide(pres_id))
            jlog(
                log,
                logging.INFO,
                tool="slides.create",
                event="deleted_default_slide",
                presentation_id=pres_id,
            )
        except HttpError as e:
            jlog(
                log,
                logging.WARNING,
                tool="slides.create",
                event="default_slide_delete_failed",
                presentation_id=pres_id,
                err=str(e),
            )

    # 4) Resolve image source to a URL usable by Slides (must resolve to image bytes)
    mode, val = _choose_image(p)
    image_url: Optional[str] = None

    def _normalize_maybe_drive(u: str) -> str:
        # If it's a Drive link or bare id, normalize to uc?export=download&id=<id>
        try:
            return _drive_public_download_url(u)
        except Exception:
            return u  # non-Drive URLs: return as-is

    if mode == "local":
        # For local files, upload to Drive since base64 exceeds Slides API 2KB URL limit for chart files
        jlog(log, logging.INFO, tool="slides.create", event="drive_upload_begin", 
             path=str(val), req_id=p.client_request_id)
        start_time = time.time()
        try:
            # Import here to avoid circular import after removing from top
            from src.agent.slides_google import upload_image_to_drive
            file_id, public_url = _backoff(lambda: upload_image_to_drive(val, make_public=p.share_image_public))  # type: ignore[arg-type]
            upload_duration = time.time() - start_time
            jlog(log, logging.INFO, tool="slides.create", event="drive_upload_complete", 
                 file_id=file_id, duration_secs=upload_duration, req_id=p.client_request_id)
            image_url = (
                public_url or f"https://drive.google.com/uc?export=download&id={file_id}"
            )
        except Exception as e:
            upload_duration = time.time() - start_time
            jlog(log, logging.ERROR, tool="slides.create", event="drive_upload_failed", 
                 error=str(e), duration_secs=upload_duration, req_id=p.client_request_id)
            raise
    elif mode == "url":
        jlog(log, logging.INFO, tool="slides.create", event="using_external_image_url")
        image_url = _normalize_maybe_drive(val)  # handles Drive and non-Drive
    elif mode == "drive_file_id":
        jlog(log, logging.INFO, tool="slides.create", event="using_drive_file_id")
        image_url = _drive_public_download_url(val)  # val is a fileId → normalize
    # else: "none" → leave image_url=None

    # Debug log to confirm image resolution
    jlog(
        log,
        logging.INFO,
        tool="slides.create",
        event="image_resolution_debug",
        mode=mode,
        val=str(val),
        image_url=image_url,
    )
    if mode != "none" and not image_url:
        jlog(
            log,
            logging.WARNING,
            tool="slides.create",
            event="image_resolved_empty",
            mode=mode,
            val=str(val),
        )

    # 5) Build content slide
    bullets: List[str] = list(p.bullets or [])
    script_text: str = p.script or ""
    
    jlog(log, logging.INFO, tool="slides.create", event="slides_api_begin", 
         presentation_id=pres_id, has_image=bool(image_url), req_id=p.client_request_id)
    slide_start_time = time.time()
    
    try:
        slide_id = _backoff(
            lambda: create_main_slide_with_content(
                presentation_id=pres_id,
                title=p.title,
                subtitle=p.subtitle,
                bullets=bullets,
                image_url=image_url,
                script=script_text,
            )
        )
        slide_duration = time.time() - slide_start_time
        jlog(log, logging.INFO, tool="slides.create", event="slides_api_complete", 
             slide_id=slide_id, duration_secs=slide_duration, req_id=p.client_request_id)
    except Exception as e:
        slide_duration = time.time() - slide_start_time
        jlog(log, logging.ERROR, tool="slides.create", event="slides_api_failed", 
             error=str(e), duration_secs=slide_duration, req_id=p.client_request_id)
        raise
    jlog(
        log,
        logging.INFO,
        tool="slides.create",
        event="slide_built",
        presentation_id=pres_id,
        slide_id=slide_id,
    )

    # 6) Persist idempotency mapping
    if p.client_request_id:
        cache[p.client_request_id] = (pres_id, slide_id, url)
        save_cache(cache)
        jlog(
            log,
            logging.INFO,
            tool="slides.create",
            event="cache_write",
            client_request_id=p.client_request_id,
            presentation_id=pres_id,
            slide_id=slide_id,
        )

    # 7) Return strictly JSON-safe types
    return SlidesCreateResult(
        presentation_id=str(pres_id), slide_id=str(slide_id), url=str(url)
    ).model_dump(mode="json")
