from __future__ import annotations

import inspect
import logging
import os
import pathlib
import re
import time
from typing import Dict, Optional, Tuple, Any

from googleapiclient.errors import HttpError
from vertexai import init as vertex_init
from vertexai.preview.vision_models import ImageGenerationModel

from ..schemas import GenerateImageParams, GenerateImageResult  # repo schemas
from src.agent.slides_google import upload_image_to_drive
from src.common.config import cfg
from google.api_core import exceptions as gexc  # we'll use this in Fix 2 as well


log = logging.getLogger("mcp.tools.imagen")

# ------------ Safe defaults / fallbacks ---------------------------------------

_FALLBACK_ASPECT_TO_SIZE: Dict[str, Tuple[int, int]] = {
    "16:9": (1280, 720),
    "4:3": (1024, 768),
    "1:1": (1024, 1024),
}


def _parse_size(s: Optional[str]) -> Optional[Tuple[int, int]]:
    """Accept '1280x720' or '1280×720'. Returns (w, h) or None."""
    if not s:
        return None
    m = re.match(r"^\s*(\d+)\s*[x×]\s*(\d+)\s*$", s)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _get_sizes_map() -> Dict[str, Tuple[int, int]]:
    """
    Pull sizes from config if present; else use fallback.
    Expecting cfg('defaults','imagen_sizes') like {'16:9':[1280,720], ...}.
    """
    try:
        sizes_cfg = cfg("defaults", "imagen_sizes")
        if isinstance(sizes_cfg, dict) and sizes_cfg:
            out: Dict[str, Tuple[int, int]] = {}
            for k, v in sizes_cfg.items():
                if isinstance(v, (list, tuple)) and len(v) == 2:
                    try:
                        out[str(k)] = (int(v[0]), int(v[1]))
                    except Exception:
                        continue
            if out:
                return out
    except Exception:
        pass
    return _FALLBACK_ASPECT_TO_SIZE


# ------------ Retry helpers ---------------------------------------------------


def _retryable_http(e: Exception) -> bool:
    # Vertex / HTTP retryables
    status = getattr(getattr(e, "resp", None), "status", None)
    if status in (429, 500, 502, 503, 504):
        return True
    # gRPC/Vertex typed exceptions that should NOT be retried
    if isinstance(
        e, (gexc.FailedPrecondition, gexc.PermissionDenied, gexc.InvalidArgument)
    ):
        return False
    return False


def _backoff_retry(fn, *, attempts: int = 4, base: float = 0.6):
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i >= attempts - 1 or not _retryable_http(e):
                raise
            delay = base * (2**i)
            log.warning(
                "Retryable HTTP error: %s; sleeping %.2fs", type(e).__name__, delay
            )
            time.sleep(delay)


# ------------ API compatibility helpers --------------------------------------


def _normalize_safety(tier: Optional[str]) -> str:
    """
    Schema values → Imagen allowed values.
    - default, block_only_high  -> block_some  (widely allowed)
    - block_most                -> block_most
    Anything else               -> block_some
    """
    t = (tier or "default").strip().lower()
    if t in ("default", "block_only_high"):
        return "block_some"
    if t == "block_most":
        return "block_most"
    return "block_some"


# src/mcp/tools/imagen.py
import inspect
import logging
import os
import pathlib
import re
import time
from typing import Dict, Optional, Tuple, Any

from googleapiclient.errors import HttpError
from vertexai import init as vertex_init
from vertexai.preview.vision_models import ImageGenerationModel

from ..schemas import GenerateImageParams, GenerateImageResult  # repo schemas
from src.agent.slides_google import upload_image_to_drive
from src.common.config import cfg
from google.api_core import exceptions as gexc  # we'll use this in Fix 2 as well


log = logging.getLogger("mcp.tools.imagen")

# ------------ Safe defaults / fallbacks ---------------------------------------

_FALLBACK_ASPECT_TO_SIZE: Dict[str, Tuple[int, int]] = {
    "16:9": (1280, 720),
    "4:3": (1024, 768),
    "1:1": (1024, 1024),
}


def _parse_size(s: Optional[str]) -> Optional[Tuple[int, int]]:
    """
    Accept '1280x720' or '1280×720'. Returns (w, h) or None.
    """
    if not s:
        return None
    m = re.match(r"^\s*(\d+)\s*[x×]\s*(\d+)\s*$", s)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _get_sizes_map() -> Dict[str, Tuple[int, int]]:
    """
    Pull sizes from config if present; else use fallback.
    Expecting cfg('defaults','imagen_sizes') like {'16:9':[1280,720], ...}.
    """
    try:
        sizes_cfg = cfg("defaults", "imagen_sizes")
        if isinstance(sizes_cfg, dict) and sizes_cfg:
            out: Dict[str, Tuple[int, int]] = {}
            for k, v in sizes_cfg.items():
                if isinstance(v, (list, tuple)) and len(v) == 2:
                    try:
                        out[str(k)] = (int(v[0]), int(v[1]))
                    except Exception:
                        continue
            if out:
                return out
    except Exception:
        pass
    return _FALLBACK_ASPECT_TO_SIZE


# ------------ Retry helpers ---------------------------------------------------


def _retryable_http(e: Exception) -> bool:
    # Vertex / HTTP retryables
    status = getattr(getattr(e, "resp", None), "status", None)
    if status in (429, 500, 502, 503, 504):
        return True
    # gRPC/Vertex typed exceptions that should NOT be retried
    if isinstance(
        e, (gexc.FailedPrecondition, gexc.PermissionDenied, gexc.InvalidArgument)
    ):
        return False
    return False


def _backoff_retry(fn, *, attempts: int = 4, base: float = 0.6):
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i >= attempts - 1 or not _retryable_http(e):
                raise
            delay = base * (2**i)
            log.warning(
                "Retryable HTTP error: %s; sleeping %.2fs", type(e).__name__, delay
            )
            time.sleep(delay)


# ------------ API compatibility helpers --------------------------------------


def _normalize_safety(tier: Optional[str]) -> str:
    """
    Schema values → Imagen allowed values.
    - default, block_only_high  -> block_some  (widely allowed)
    - block_most                -> block_most
    Anything else               -> block_some
    """
    t = (tier or "default").strip().lower()
    if t in ("default", "block_only_high"):
        return "block_some"
    if t == "block_most":
        return "block_most"
    return "block_some"


def _call_generate_images_resilient(model, base_kwargs: Dict[str, Any]):
    """
    Call ImageGenerationModel.generate_images with kwargs filtered to the
    actual signature. Try multiple variants for dimensions, then fall back
    to letting the SDK choose defaults.

    Variants attempted in order:
      1) image_dimensions=(w, h)
      2) size="WxH"
      3) width=w, height=h
      4) aspect_ratio="W:H"
      5) (no dimension kwargs at all)
    """
    fn = model.generate_images
    sig = inspect.signature(fn)

    def _filtered(kwargs: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in kwargs.items() if k in sig.parameters}

    w = base_kwargs.pop("_w", None)
    h = base_kwargs.pop("_h", None)
    ar = f"{w}:{h}" if (w and h) else None
    size_str = f"{w}x{h}" if (w and h) else None

    candidates = [
        dict(base_kwargs, image_dimensions=(w, h) if (w and h) else None),
        dict(base_kwargs, size=size_str if size_str else None),
        dict(base_kwargs, width=w, height=h),
        dict(base_kwargs, aspect_ratio=ar if ar else None),
        dict(base_kwargs),
    ]

    last_err: Optional[Exception] = None
    for cand in candidates:
        kw = {k: v for k, v in cand.items() if v is not None}
        try:
            return fn(**_filtered(kw))
        except TypeError as te:
            last_err = te
            continue
    # If all TypeError due to unexpected args, try truly minimal call
    try:
        return fn(**_filtered(dict(prompt=base_kwargs["prompt"], number_of_images=1)))
    except Exception as e:
        raise last_err or e


# ------------ Main tool -------------------------------------------------------


def image_generate_tool(params: dict) -> dict:
    """
    Generate an image via Vertex Imagen with defensive defaults:
      - Prefer explicit size (e.g., '1280x720'); else resolve via aspect (default '16:9')
      - Retry 429/5xx
      - Save local file under out/images/
      - Optionally upload to Drive and return public URL
    Returns dict(GenerateImageResult).
    """
    # Validate/parse request using repo schemas
    p = GenerateImageParams.model_validate(params)

    # Resolve project/region
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set")

    vertex_init(project=project, location=region)

    # Determine dimensions
    aspect = (p.aspect or "16:9").strip()
    wh = _parse_size(getattr(p, "size", None))
    if not wh:
        sizes_map = _get_sizes_map()
        wh = sizes_map.get(aspect, sizes_map["16:9"])
    width, height = wh

    # Choose model name from config (with safe fallback)
    try:
        model_name = cfg("imagen", "model") or "imagegeneration@006"
    except Exception:
        model_name = "imagegeneration@006"

    model = ImageGenerationModel.from_pretrained(model_name)
    safety_level = _normalize_safety(getattr(p, "safety_tier", None))

    def _gen():
        base = dict(
            prompt=p.prompt,
            number_of_images=1,
            safety_filter_level=safety_level,
            _w=width,
            _h=height,
        )
        log.info(f"Generating image with prompt: {p.prompt}")
        return _call_generate_images_resilient(model, base)

    result = _backoff_retry(_gen)
    log.info(f"Image generation result: {result}")

    # Persist locally
    out_dir = pathlib.Path("out/images")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"imagen_{int(time.time())}.png"
    img = result.images[0]

    img.save(str(path))

    # Build result
    out = GenerateImageResult(local_path=str(path))

    # Optional: upload to Drive (non-fatal if it fails)
    if getattr(p, "return_drive_link", False):
        try:
            file_id, public_url = upload_image_to_drive(str(path), make_public=True)
            out.drive_file_id = file_id
            out.url = public_url
        except HttpError as e:
            log.warning("Drive upload failed: %s", e)

    # Return strictly JSON-safe dict
    return out.model_dump(mode="json")


# ------------ Main tool -------------------------------------------------------


def image_generate_tool(params: dict) -> dict:
    """
    Generate an image via Vertex Imagen with defensive defaults:
      - Prefer explicit size (e.g., '1280x720'); else resolve via aspect (default '16:9')
      - Retry 429/5xx
      - Save local file under out/images/
      - Optionally upload to Drive and return public URL
    Returns dict(GenerateImageResult).
    """
    # Validate/parse request using repo schemas
    p = GenerateImageParams.model_validate(params)

    # Resolve project/region
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set")

    vertex_init(project=project, location=region)

    # Determine dimensions
    aspect = (p.aspect or "16:9").strip()
    wh = _parse_size(getattr(p, "size", None))
    if not wh:
        sizes_map = _get_sizes_map()
        wh = sizes_map.get(aspect, sizes_map["16:9"])
    width, height = wh

    # Choose model name from config (with safe fallback)
    try:
        model_name = cfg("imagen", "model") or "imagegeneration@006"
    except Exception:
        model_name = "imagegeneration@006"

    model = ImageGenerationModel.from_pretrained(model_name)
    safety_level = _normalize_safety(getattr(p, "safety_tier", None))

    def _gen():
        base = dict(
            prompt=p.prompt,
            number_of_images=1,
            safety_filter_level=safety_level,
            _w=width,
            _h=height,
        )
        return _call_generate_images_resilient(model, base)

    result = _backoff_retry(_gen)

    # Persist locally
    out_dir = pathlib.Path("out/images")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"imagen_{int(time.time())}.png"
    img = result.images[0]
    img.save(str(path))

    # Build result
    out = GenerateImageResult(local_path=str(path))

    # Optional: upload to Drive (non-fatal if it fails)
    if getattr(p, "return_drive_link", False):
        try:
            file_id, public_url = upload_image_to_drive(str(path), make_public=True)
            out.drive_file_id = file_id
            out.url = public_url
        except HttpError as e:
            log.warning("Drive upload failed: %s", e)

    # Return strictly JSON-safe dict
    return out.model_dump(mode="json")
