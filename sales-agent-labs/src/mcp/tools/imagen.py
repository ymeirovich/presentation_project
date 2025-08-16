from __future__ import annotations
import logging, os, time, pathlib
from typing import Optional, Tuple

from vertexai import init as vertex_init
from vertexai.preview.vision_models import ImageGenerationModel
from googleapiclient.errors import HttpError

from ..schemas import GenerateImageParams, GenerateImageResult
from src.agent.slides_google import upload_image_to_drive

log = logging.getLogger("mcp.tools.imagen")

from src.common.config import cfg

_ASPECT_TO_SIZE = {
    "16:9": (1280, 720),
    "1:1":  (1024, 1024),
    "4:3":  (1024, 768),
}

def _retryable_http(e: Exception) -> bool:
    status = getattr(getattr(e, "resp", None), "status", None)
    return status in (429, 500, 502, 503, 504)

def _backoff_retry(fn, *, attempts=4, base=0.6):
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i >= attempts - 1 or not _retryable_http(e):
                raise
            delay = base * (2 ** i)
            log.warning("Retryable HTTP error: %s; sleeping %.2fs", type(e).__name__, delay)
            time.sleep(delay)

def image_generate_tool(params: dict) -> dict:
    p = GenerateImageParams.model_validate(params)
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is not set")
    vertex_init(project=project, location=region)   # <-- inside the function
    model = ImageGenerationModel.from_pretrained("imagegeneration@006") 
    #width, height = _ASPECT_TO_SIZE[p.aspect]
    sizes = cfg("defaults", "imagen_sizes")
    width, height = sizes[p.aspect]


    def _gen():
        return model.generate_images(
            prompt=p.prompt,
            number_of_images=1,
            size=f"{width}x{height}",
            safety_filter_level=(
                "block_most" if p.safety_tier == "block_most"
                else "block_some" if p.safety_tier == "block_only_high"
                else "block_none"
            ),
        )
    result = _backoff_retry(_gen)

    img = result.images[0]
    out_dir = pathlib.Path("out/images"); out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"imagen_{int(time.time())}.png"
    img.save(str(path))

    out = GenerateImageResult(local_path=str(path))
    if p.return_drive_link:
        file_id, public_url = upload_image_to_drive(str(path), make_public=True)
        out.drive_file_id, out.url = file_id, public_url
    return out.model_dump()
